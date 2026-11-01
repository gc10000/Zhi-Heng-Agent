import sys
from app.utils.task_utils import add_running_task, add_done_task
from app.utils.sse_utils import push_to_session, SSEEvent
from app.query_process.agent.state import QueryGraphState
from app.core.logger import logger
from app.core.load_prompt import load_prompt
from app.lm.lm_utils import get_llm_client
from app.clients.mongo_history_utils import save_chat_message
import re
from app.answering.context_budget import pack_prompt_inputs
from app.answering.errors import AnswerGenerationError

_IMAGE_BLOCK_MARKER = "【图片】"
MAX_CONTEXT_CHARS = 12000

def step_1_check_answer(state) -> bool:
  """
  阶段一：检查 state 中是否已有 answer。
  - 若已存在：按需推送流式 delta（用于 SSE），并返回 True
  - 若不存在：返回 False
  """
  answer = state.get("answer", None)
  is_stream = state.get("is_stream" )
  if answer:
    if ((state.get('evidence_attribution') or {}).get('assertion_binding') or {}).get('enabled'):
      from app.answering.assertion_binding import validate_saved_binding
      validate_saved_binding(dict(state,citations=state.get('prompt_used_docs') or []))
    if is_stream:
      logger.info("---Step 1: 发现已有答案，执行流式推送---")
      push_to_session(state["session_id"], SSEEvent.DELTA, {"delta": answer})
    return True
  else:
    return False

# 目标结构
# HAK 180 烫金机的操作面板位于机器正前方。开启电源后，您需要先设置温度，默认建议设置在 110℃ 左右。
# 具体的按键位置请参考下图：
# 【图片】
# http://local-server/images/panel_view.jpg
# http://local-server/images/button_detail.jpg
def step_2_construct_prompt(state: QueryGraphState) -> str:
  """
  第一阶段：构建 Prompt
  根据state中的问题、重新问题、历史对话、提问商品（item_names）、 重排内容 组织prompt
  """
  # 1. 获取相关信息
  original_query = state.get("original_query", "")
  rewritten_query = state.get("rewritten_query", "")
  # 优先使用重写后的问题
  question = rewritten_query if rewritten_query else original_query
  if state.get('evidence_scope_note'):
    question += '\n\n证据限制：' + state['evidence_scope_note']
  history = state.get("history", [])
  item_names = state.get("item_names", [])
  reranked_docs = state.get("reranked_docs") or []

  # 只计算实际插入的完整证据与历史；空串不追加未计费占位文本。
  from app.answering.service import AnswerBudget,build_budgeted_prompt
  budget = AnswerBudget.model_validate(state['answer_budget']) if state.get('answer_budget') is not None else AnswerBudget.load()
  item_names_str = ", ".join(item_names) if item_names else "无指定商品"
  from app.answering.evidence_attribution import EvidenceAttributionPolicy,evidence_labels
  attribution=EvidenceAttributionPolicy.model_validate(state.get('evidence_attribution') or {})
  labels=evidence_labels(reranked_docs,attribution)
  template='answer_attributed_v1' if attribution.enabled else 'answer_out'
  relations=attribution.source_relations is not None and attribution.source_relations.enabled
  binding=attribution.assertion_binding is not None and attribution.assertion_binding.enabled
  baseline=None
  if relations:
    if binding:
      # 新策略以已接线的关系提示为基线，额外矩阵不能挤出任何原证据或历史。
      baseline=build_budgeted_prompt(reranked_docs,history,question=question,items=item_names_str,
        render=lambda **kw:load_prompt('answer_source_relations_v1',**kw),budget=budget,
        groups=state.get('evidence_groups',()),counter=state.get('token_counter'),attributions=labels)
      oldlabels=[{k:v for k,v in label.items() if k!='source_relations'} for label in labels]
      original=build_budgeted_prompt(reranked_docs,history,question=question,items=item_names_str,
        render=lambda **kw:load_prompt('answer_attributed_v1',**kw),budget=budget,
        groups=state.get('evidence_groups',()),counter=state.get('token_counter'),attributions=oldlabels)
      if baseline['used_doc_indices']!=original['used_doc_indices'] or baseline['history']!=original['history']:
        from app.api.errors import APIError
        raise APIError(422,'source_relation_budget_exceeded','关系呈现不能挤出原证据或历史。')
    else:
      oldlabels=[{k:v for k,v in label.items() if k!='source_relations'} for label in labels]
      baseline=build_budgeted_prompt(reranked_docs,history,question=question,items=item_names_str,
        render=lambda **kw:load_prompt('answer_attributed_v1',**kw),budget=budget,
        groups=state.get('evidence_groups',()),counter=state.get('token_counter'),attributions=oldlabels)
    template='answer_source_relations_v1'
  if binding:
    from app.answering.assertion_binding import render_assertion_matrix
    matrix_labels=[dict(labels[i],reference_number=n+1) for n,i in enumerate(baseline['used_doc_indices'])]
    assertion_matrix=render_assertion_matrix(matrix_labels)
    chosen=baseline['used_doc_indices']
    bound_docs=[reranked_docs[i] for i in chosen]
    bound_ids={str(d.get('chunk_uid',d.get('chunk_id'))) for d in bound_docs}
    bound_groups=[g for g in state.get('evidence_groups',()) if all(uid in bound_ids for uid in g)]
    packed = build_budgeted_prompt(bound_docs,history,question=question,items=item_names_str,
      render=lambda **kw:load_prompt('answer_assertion_binding_v1',assertion_matrix=assertion_matrix,**kw),budget=budget,
      groups=bound_groups,counter=state.get('token_counter'),attributions=[labels[i] for i in chosen])
    packed['used_doc_indices']=[chosen[i] for i in packed['used_doc_indices']]
    packed['budget']['omitted_documents']=len(reranked_docs)-len(packed['used_doc_indices'])
  else:
    packed = build_budgeted_prompt(reranked_docs,history,question=question,items=item_names_str,
      render=lambda **kw:load_prompt(template,**kw),budget=budget,
      groups=state.get('evidence_groups',()),counter=state.get('token_counter'),attributions=labels)
  if relations and (packed['used_doc_indices']!=baseline['used_doc_indices'] or packed['history']!=baseline['history']):
    from app.api.errors import APIError
    raise APIError(422,'source_relation_budget_exceeded','关系呈现不能挤出原证据或历史，请停止并核对冻结输入。')
  if labels is not None:
    state['prompt_reference_map']=[dict(labels[i],reference_number=n+1) for n,i in enumerate(packed['used_doc_indices'])]
  context_str, history_str = packed['context'], packed['history']
  state['used_chunk_ids'] = packed['used_chunk_ids']
  state['prompt_used_docs'] = [reranked_docs[i] for i in packed['used_doc_indices']]
  state['prompt_input_chars'] = packed['used_chars']
  state['prompt_budget'] = packed['budget']
  state['answer_max_tokens'] = budget.output_tokens
  state['answer_token_field'] = budget.output_token_field
  if budget.output_contract is not None and budget.output_contract.enabled:
    state['output_contract']=budget.output_contract.model_dump(mode='json')

  # 4. 格式化 Item Names (提问商品)
  item_names_str = ", ".join(item_names) if item_names else "无指定商品"

  # 5. 组装 Prompt
  prompt = packed['prompt']

  logger.info("答案提示词已组装，session={}，字符数={}，证据/历史字符数={}", state.get("session_id"), len(prompt), packed["used_chars"])

  return prompt


def step_3_generate_response(state: QueryGraphState, prompt: str, *, client=None) -> QueryGraphState:
  """生成失败统一抛出携带部分文本的异常，由外层处理任务终态。"""
  session_id = state.get('session_id')
  final_text = ''
  from contextlib import nullcontext
  from app.infrastructure.providers.diagnostic_usage import capture_usage,record_response,summarize,record_reasoning
  observations=[] if (state.get('output_contract') or {}).get('enabled') else None
  mode=[] if observations is not None and state['output_contract'].get('function_version') in ('diagnostic_nonthinking_manifest_r1','diagnostic_source_relation_048_v1') else None
  from app.answering.evidence_attribution import EvidenceAttributionPolicy
  attribution=EvidenceAttributionPolicy.model_validate(state.get('evidence_attribution') or {})
  binding=attribution.assertion_binding is not None and attribution.assertion_binding.enabled
  if binding:
    from app.answering.evidence_attribution import evidence_labels
    from app.answering.assertion_binding import checked_sources
    docs=state.get('prompt_used_docs') or []
    expected=[dict(label,reference_number=n+1) for n,label in enumerate(evidence_labels(docs,attribution))]
    if expected!=state.get('prompt_reference_map'):
      raise ValueError('原句选择输入与冻结来源映射不一致')
    checked_sources(expected,docs,attribution)
  if mode is not None:state['answer_mode_observations']=mode
  if observations is not None:state['answer_usage_observations']=observations
  if binding:
    from app.answering.assertion_binding import failure_record
  try:
    llm = client if client is not None else get_llm_client()
    from app.infrastructure.providers.clients import output_limit_options
    options = output_limit_options(llm,state['answer_max_tokens'],state.get('answer_token_field','max_tokens'),
        contract=state.get('output_contract')) if state.get('answer_max_tokens') else {}
    seen_observations=0
    def reasoning(response):
      nonlocal seen_observations
      if mode is not None:
        record_reasoning((getattr(response,'additional_kwargs',None) or {}).get('reasoning_content'),source='normalized.additional_kwargs')
      if observations is not None:
        record_response(response,observations,seen_observations)
        seen_observations=len(observations)
        return
      usage=getattr(response,'usage_metadata',None) or (getattr(response,'response_metadata',None) or {}).get('token_usage') or {}
      details=usage.get('output_token_details') or usage.get('completion_tokens_details') or {}
      value=details.get('reasoning',details.get('reasoning_tokens'))
      if type(value) is int and value>=0:state['answer_reasoning_tokens']=value
    with capture_usage(observations,mode_observations=mode) if observations is not None else nullcontext():
      if state.get('is_stream'):
        for chunk in llm.stream(prompt,**options):
          reasoning(chunk)
          if (getattr(chunk,'response_metadata',None) or {}).get('finish_reason'):
            state['answer_finish_reason']=chunk.response_metadata['finish_reason']
          if (getattr(chunk,'response_metadata',None) or {}).get('finish_reason') in ('length','max_tokens'):
            state['output_truncated'] = True
          delta = getattr(chunk, 'content', '') or ''
          if delta:
            final_text += delta
            if not binding:
              push_to_session(session_id, SSEEvent.DELTA, {'delta': delta})
      else:
        response = llm.invoke(prompt,**options)
        reasoning(response)
        state['answer_finish_reason']=(getattr(response,'response_metadata',None) or {}).get('finish_reason')
        final_text = response.content
        if (getattr(response,'response_metadata',None) or {}).get('finish_reason') in ('length','max_tokens'):
          state['output_truncated'] = True
  except Exception as exc:
    logger.error('回答生成失败，session={}，异常类型={}，部分字符数={}', session_id, type(exc).__name__, len(final_text))
    if binding:
      state['answer_binding_failure']=failure_record(final_text,prompt,state.get('prompt_reference_map'),attribution,
        'answer_generation_interrupted' if final_text else 'answer_generation_failed')
    raise AnswerGenerationError(partial_answer=final_text) from exc
  finally:
    if observations is not None:state['answer_usage_validation']=summarize(observations)
  if binding:
    from app.answering.assertion_binding import bind_response
    from app.api.errors import APIError
    try:
      if state.get('output_truncated'):
        raise ValueError('原句选择输出被截断')
      bound,proof=bind_response(final_text,state.get('prompt_reference_map') or [],state.get('prompt_used_docs') or [],attribution)
    except (ValueError,TypeError,KeyError) as exc:
      state['answer_binding_failure']=failure_record(final_text,prompt,state.get('prompt_reference_map'),attribution,
        'answer_selection_rejected')
      raise AnswerGenerationError('原句选择与证据不一致，已拒绝写入。',partial_answer=final_text) from APIError(
        422,'answer_binding_invalid','原句选择与冻结证据不一致。')
    state['answer_binding']=proof | dict(raw_selection=final_text)
    final_text=bound
    if state.get('is_stream'):
      push_to_session(session_id, SSEEvent.DELTA, {'delta': final_text})
  state['answer'] = final_text
  return state


def _extract_images_from_docs(docs):
    """
    辅助方法：从文档列表中提取图片URL
    
    核心逻辑：
    1. 遍历所有相关文档（包括本地知识库切片和联网搜索结果）。
    2. 策略一：直接检查文档的 'url' 字段（常见于联网搜索结果）。
       - 验证后缀名是否为图片格式 (.jpg, .png 等)。
    3. 策略二：使用正则表达式扫描文档 'text' 正文内容（常见于本地 Markdown 文档）。
       - 匹配 Markdown 图片语法: ![alt text](image_url)。
    4. 对提取到的 URL 进行去重处理，返回唯一图片列表。
    
    :param docs: 文档列表，每个文档为字典格式
    :return: 图片 URL 字符串列表
    """
    images = []
    seen = set() # 用于去重，避免同一张图片重复出现
    if not docs:
        return []
    # ---------------------------------------------------------
    # 正则表达式解释：r'!\[.*?\]\((.*?)\)'
    # 1. !\[   -> 匹配 Markdown 图片语法的开头 "![" (注意 [ 需要转义)
    # 2. .*?   -> 非贪婪匹配图片描述文本 (Alt Text)，即 [] 中间的内容
    # 3. \]    -> 匹配描述文本的结束符 "]"
    # 4. \(    -> 匹配 URL 部分的开始符 "("
    # 5. (.*?) -> 捕获组 (Group 1)：非贪婪匹配括号内的实际 URL 内容
    # 6. \)    -> 匹配 URL 部分的结束符 ")"
    # ( ... ) （不带反斜杠）：这就是 捕获组 。
    # 它的作用是告诉程序：“虽然我匹配了整个 ![...](...) 结构，但我 只要 这括号里的内容”。
    # ---------------------------------------------------------
    md_img_pattern = re.compile(r'!\[.*?\]\((.*?)\)')

    logger.info(f"开始提取图片，待处理文档数: {len(docs)}")

    for i, doc in enumerate(docs):
        # 1. 优先检查 url 字段 (主要针对 Web Search 结果)
        url = (doc.get("url") or "").strip()
        if url:
            # 简单后缀判断：确保是静态图片资源
            if url.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.svg')):
                if url not in seen:
                    logger.debug("图片字段已识别，文档序号={}", i)
                    seen.add(url)
                    images.append(url)

        # 2. 检查 text 字段中的 Markdown 图片 (主要针对 Local Chunk)
        text = (doc.get("text") or "").strip()
        if text:
            # findall 机制解释：
            # 正则表达式 r'!\[.*?\]\((.*?)\)' 中包含一个捕获组 (.*?)
            # 当存在捕获组时，findall 只返回括号内匹配到的内容（即 URL），而不是整个 ![...](...) 字符串
            # 示例：
            # 输入 text: "参考图片 ![面板图](http://img.com/1.jpg) 如下"
            # 返回 matches: ['http://img.com/1.jpg']
            matches = md_img_pattern.findall(text)
            for img_url in matches:
                img_url = img_url.strip()
                if img_url and img_url not in seen:
                    logger.debug("正文图片已识别，文档序号={}", i)
                    seen.add(img_url)
                    images.append(img_url)

    logger.info("图片提取完成，数量={}", len(images))
    return images


def step_4_write_history(state: QueryGraphState, image_urls = None) -> QueryGraphState:
  """
  阶段四：把本轮答案写入 MongoDB history。
  利用 utils/mongo_history_utils.py 中的 save_chat_messages 方法。
  """
  session_id = state.get("session_id", "default")
  answer = (state.get("answer") or "").strip()
  item_names = state.get("item_names") or []

  try:
    if answer:
       save_chat_message(
        session_id=session_id,
        role="assistant",
        text=answer,
        rewritten_query="",
        item_names=item_names,
        image_urls=image_urls,
        message_id=None
      )
  except Exception as e:
    # 写历史失败不应影响主链路
    logger.error(f"写入Mongo历史记录失败: {e}")

  return state


def node_answer_output(state: QueryGraphState) -> QueryGraphState:
  """
  1 判断state 中的answer是否已经存在，如果存在直接输出answer中的答案，注意判断是否需要流式输出需要则流式输出
  2 根据state中的问题、重新问题、历史对话、提问商品（item_names）、 重排内容 组织prompt 并调用llm 生成答案
  3 阶段三：调用大模型输出答案 注意判断是否需要流式输出需要则流式输出
  4 把答案写入到mongodb的history中 利用utils/mongo_history_utils.py中的save_chat_message方法
  5 返回图文结果，由外层在整图成功后发送 final（主要用于图片渲染）
     {
        "answer": "HAK 180 烫金机的操作面板位于...（大模型生成的纯文本）...",
        "status": "completed",
        "image_urls": [
            "http://local-server/images/panel_view.jpg",
            "http://local-server/images/button_detail.jpg"
        ]
      }
  """
  logger.info("---node_answer_output (答案生成) 节点开始处理---")
  add_running_task(state['session_id'], sys._getframe().f_code.co_name, state.get("is_stream"))
  
  # 阶段一：检查answer是否存在,如果存在直接输出answer中的答案
  answer_exists = step_1_check_answer(state)
  
  # 阶段二  如果没有answer则 构建 Prompt
  if not answer_exists:
    prompt = step_2_construct_prompt(state)
    state["prompt"] = prompt

    # 阶段三：  如果没有answer则 调用大模型输出答案
    step_3_generate_response(state, prompt)

  # 提取图片URL（用于历史记录和前端展示）
  image_urls = _extract_images_from_docs(state.get("prompt_used_docs") or [])

  # 阶段四：把答案写入到mongodb的history中
  if state.get("answer"):
    logger.info("---写入MongoDB历史记录---")
    step_4_write_history(state, image_urls=image_urls)

  add_done_task(state['session_id'], sys._getframe().f_code.co_name, state.get("is_stream"))
  
  # 完成事件由外层在整图成功后统一发送，节点只返回结果。
  state['image_urls'] = image_urls

  logger.info("---node_answer_output 节点处理结束---")
  return state


if __name__ == "__main__":
    print("\n" + "="*50)
    print(">>> 启动 node_answer_output 本地测试")
    print("="*50)
    
    # 1. 构造模拟数据
    # 模拟重排序后的文档列表 (reranked_docs)
    # 包含：本地文档（带Markdown图片）、联网结果（带URL字段）、纯文本文档
    mock_reranked_docs = [
        {
            "chunk_id": "local_101",
            "source": "local",
            "title": "HAK 180 烫金机操作手册_v2.pdf",
            "score": 0.95,
            "text": """
            HAK 180 烫金机的操作面板位于机器正前方。
            开启电源后，您需要先设置温度，默认建议设置在 110℃ 左右。
            具体的操作面板布局请参考下图：
            ![操作面板布局图](http://local-server/images/panel_view.jpg)
            
            如果是进行局部烫金，请调节侧面的旋钮。
            ![侧面旋钮细节](http://local-server/images/knob_detail.png)
            """
        },
        {
            "chunk_id": None,
            "source": "web",
            "title": "HAK 180 常见故障排除 - 官网",
            "score": 0.88,
            "url": "http://example.com/hak180_troubleshooting.jpeg", # 这是一个直接指向图片的URL（虽然少见，但用于测试提取）
            "text": "如果机器无法加热，请检查保险丝是否熔断..."
        },
        {
            "chunk_id": "local_102",
            "source": "local",
            "title": "安全注意事项",
            "score": 0.82,
            "text": "操作时请务必佩戴隔热手套，避免高温烫伤。"
        }
    ]

    # 模拟历史记录
    mock_history = [
        {"role": "user", "text": "你好，这款机器怎么用？"},
        {"role": "assistant", "text": "您好！请问您具体指的是哪一款机器？"},
        {"role": "user", "text": "HAK 180 烫金机"}
    ]

    # 模拟输入状态
    mock_state = {
        "session_id": "test_answer_session_001",
        "original_query": "HAK 180 烫金机怎么操作？",
        "rewritten_query": "HAK 180 烫金机的具体操作步骤和面板设置方法",
        "item_names": ["HAK 180 烫金机"],
        "history": mock_history,
        "reranked_docs": mock_reranked_docs,
        "is_stream": False, # 测试非流式
        # "is_stream": True, # 若要测试流式，需确保 SSE 环境或 mock 相关函数
        "answer": None # 初始无答案
    }

    try:
        # 运行节点
        result = node_answer_output(mock_state)
        
        print("\n" + "="*50)
        print(">>> 测试结果摘要:")
        
        # 1. 验证 Prompt 构建
        if "prompt" in result:
            print(f"[PASS] Prompt 构建成功 (长度: {len(result['prompt'])})")
            # print(f"Prompt 预览:\n{result['prompt'][:200]}...")
        else:
            print("[FAIL] Prompt 未构建")

        # 2. 验证答案生成
        answer = result.get("answer")
        if answer and len(answer) > 10:
            print(f"[PASS] 答案生成成功 (长度: {len(answer)})")
            print(f"答案预览: {answer[:50]}...")
        else:
            print(f"[WARN] 答案生成可能异常 (Content: {answer})")

        # 3. 验证图片提取
        # 我们期望提取到 3 张图片：
        # 1. http://local-server/images/panel_view.jpg (来自 local_101)
        # 2. http://local-server/images/knob_detail.png (来自 local_101)
        # 3. http://example.com/hak180_troubleshooting.jpeg (来自 web 结果的 url 字段)
        
        # 注意：这里我们没办法直接从 result state 里拿到 image_urls，因为它是作为 SSE 推送出去的，或者存库了
        # 但我们可以通过日志观察 _extract_images_from_docs 的输出
        # 如果需要验证，可以临时修改 node_answer_output 返回 image_urls
        print("\n[INFO] 请检查上方日志中是否包含 '图片提取完成' 及以下 URL:")
        print(" - http://local-server/images/panel_view.jpg")
        print(" - http://local-server/images/knob_detail.png")
        print(" - http://example.com/hak180_troubleshooting.jpeg")

        print("="*50)

    except Exception as e:
        logger.exception(f"测试运行期间发生未捕获异常: {e}")
