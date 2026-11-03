"""完整标量池到精确prompt的纯离线冻结；不创建客户端、Run或授权。"""
from copy import deepcopy
import hashlib
import json

from app.knowledge.repository import fingerprint

VERSION='connection_048_production_input_v1'
SCALAR_FIELDS=('chunk_uid','owner_id','kb_id','document_id','revision_id','ordinal','text','metadata','content_sha256')


def read_scalar_pool(client,config):
    """只读指定四修订标量；实际成员与hash由装配入口再次全等校验。"""
    target=config['target'];docs=config['corpus']['snapshot']['documents'];rows=[]
    for doc in docs:
        if len(rows)>=1000:
            raise ValueError('冻结标量超过读取上限')
        selectors={k:target[k] for k in ('owner_id','kb_id')}
        selectors.update({k:doc[k] for k in ('document_id','revision_id')})
        rows.extend(dict(r) for r in client.query(collection_name=target['collection'],
            filter=' and '.join(k+' == '+json.dumps(v) for k,v in selectors.items()),
            output_fields=list(SCALAR_FIELDS),limit=1000-len(rows),timeout=15,consistency_level='Strong'))
    return rows


def assemble_input(config,inputs):
    from app.answering.comparison_context import _checked_row
    from app.answering.evidence_attribution import EvidenceAttributionPolicy
    from app.answering.service import AnswerBudget
    from app.retrieval.models import QueryPlan
    from app.runs.query_runner import QueryRunner
    from app.runs.comparison_inputs import validate_input_guard
    config,inputs=deepcopy(config),deepcopy(inputs)
    policy=EvidenceAttributionPolicy.model_validate(config['parameters']['evidence_attribution'])
    if not policy.comparison_answer or not policy.comparison_answer.enabled or policy.comparison_answer.function_version!='connection_comparison_v1':
        raise ValueError('输入冻结只支持显式连接比较模式')
    scope=policy.scope.model_dump(mode='json');frozen=policy.source_relations.frozen_payloads
    pool=inputs['frozen_scalar_payloads']
    checked=[_checked_row(row,scope,frozen) for row in pool]
    if len(checked)!=len(frozen) or {r['chunk_uid'] for r in checked}!=set(frozen):
        raise ValueError('生产输入必须包含全部且仅含冻结标量，不能缩scope或重复成员')
    # pool保存顺序规范化，使本次实时读取顺序不影响精确输入身份。
    inputs['frozen_scalar_payloads']=sorted(checked,key=lambda r:r['chunk_uid'])
    for seed in inputs['seeds']:
        _checked_row(seed,scope,frozen)
    plan=QueryPlan.model_validate(inputs['query_plan']);question=inputs['question']
    ids=inputs['product_ids']
    if (plan.original_query!=question['question'] or plan.route!='compare' or plan.comparison_target!='device_uplink' or
            len(ids)!=2 or list(plan.product_ids)!=ids or not set(ids)<=set(scope['product_ids'])):
        raise ValueError('生产输入问题、目标或产品身份不一致')
    runner=object.__new__(QueryRunner)
    runner.answer_budget=AnswerBudget.model_validate(config['parameters']['answer_budget'])
    runner.evidence_attribution=policy.model_dump(mode='json')
    runner.retrieval_policy=deepcopy(config['parameters']['retrieval'])
    docs,groups,manifest=runner.assemble_connection_context(inputs['seeds'],inputs['frozen_scalar_payloads'],ids,inputs['groups'])
    # 正式adapter按原题product_names创建input_product_snapshot；QueryRunner先按该顺序
    # 呈现已选产品，再补检索后新增产品。selected顺序只用于比较身份，不能替代展示顺序。
    prompt_ids=[]
    for name in question['product_names']:
        for pid in ids:
            if policy.products[pid]==name and pid not in prompt_ids:
                prompt_ids.append(pid)
    prompt_ids.extend(pid for pid in ids if pid not in prompt_ids)
    state,prompt=runner.evidence_prompt(question['question'],docs,groups,plan,
        item_names=[policy.products[p] for p in prompt_ids],history=question['history'],
        session_id='connection-048-input-freeze',product_ids=ids,comparison_context=manifest)
    if not prompt or state.get('comparison_answer_short_circuit') or state['prompt_used_docs']!=docs:
        raise ValueError('生产输入未形成完整生成prompt')
    if [r['reference_number'] for r in state['prompt_reference_map']]!=list(range(1,len(docs)+1)):
        raise ValueError('生产输入引用必须连续')
    validate_input_guard(state)
    result=dict(prompt=prompt,context=state['prompt_used_docs'],prompt_reference_map=state['prompt_reference_map'],
        groups=state['evidence_groups'],budget=state['prompt_budget'],comparison_context_assembly=manifest)
    return dict(schema_version=VERSION,new_config=config,production_inputs=inputs,result=result,
        full_scope_scalar_payloads_replayed=True,exact_production_prompt_frozen=True,
        prompt_utf8_sha256=hashlib.sha256(prompt.encode('utf-8')).hexdigest(),result_sha256=fingerprint(result))


def validate_input_anchor(anchor):
    if (not isinstance(anchor,dict) or anchor.get('schema_version')!=VERSION or
            any(k not in anchor for k in ('new_config','production_inputs'))):
        raise ValueError('连接048缺少完整生产输入冻结版本')
    actual=assemble_input(anchor['new_config'],anchor['production_inputs'])
    if anchor!=actual:
        raise ValueError('连接048冻结输入、prompt、引用或预算无法从完整标量重算')
    return anchor
