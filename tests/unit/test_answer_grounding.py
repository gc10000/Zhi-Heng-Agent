"""完整提示词预算必须包含模板和问题，字符兜底不能替代模型窗口。"""
import pytest
from app.api.errors import APIError


def test_unavoidable_question_overflow_is_rejected_before_generation(answer_node):
    state=dict(original_query='中English🙂'*200,answer_budget=dict(context_window=512,
        output_tokens=64,reserve_tokens=16,max_chars=12000),reranked_docs=[dict(chunk_id='c',text='24V')])
    with pytest.raises(APIError) as error:
        answer_node.module.step_2_construct_prompt(state)
    assert error.value.code=='prompt_budget_exceeded'


def test_final_render_including_template_and_history_fits_recorded_budget(answer_node,monkeypatch):
    node=answer_node.module
    monkeypatch.setattr(node,'load_prompt',lambda name,**kw:'SYS:'+kw['context']+'H:'+kw['history']+'Q:'+kw['question'])
    state=dict(original_query='question'*25,history=[dict(role='user',text='history'*50)],
        reranked_docs=[dict(chunk_id='a',text='证据🙂'*100),dict(chunk_id='b',text='24V')],
        answer_budget=dict(context_window=512,output_tokens=64,reserve_tokens=16,max_chars=12000))
    prompt=node.step_2_construct_prompt(state)
    assert len(prompt.encode('utf-8'))+64+16<=512,'必须对完整渲染后的prompt计费'
    assert state['prompt_budget']['counter']=='utf8_bytes_upper_bound'
    assert [d['chunk_id'] for d in state['prompt_used_docs']]==['b']


@pytest.mark.parametrize('parts,expected', [(['值[','1',']'],'值[1]'),
    (['值[1, 2]'],'值[1, 2]'),(['值[1-2]'],'值[1-2]'),
    (['`寄存器[999]`'],'`寄存器[999]`'),(['``寄存器[999]``'],'``寄存器[999]``'),
    (['```\n数组[999]\n```'],'```\n数组[999]\n```'),
    (['![999](asset://a)'],'![999](asset://a)')])
def test_citation_guard_handles_split_refs_and_code_or_image_alt(parts,expected):
    from app.answering.citations import CitationGuard
    output=[];guard=CitationGuard({1,2},output.append)
    for part in parts:guard.write(part)
    guard.write('',final=True)
    assert ''.join(output)==expected


@pytest.mark.parametrize('parts',[['[0]'],['[3]'],['[1,3]'],['[2-1]'],['[1,,2]'],['[999'],['[', '9'*129]])
def test_invalid_citation_never_emits_reference(parts):
    from app.answering.citations import CitationGuard
    output=[];guard=CitationGuard({1,2},output.append)
    with pytest.raises(APIError):
        for part in parts:guard.write(part)
        guard.write('',final=True)
    assert not any('999' in x for x in output)


def test_atomic_group_is_never_split_to_retain_a_child_under_token_budget():
    from app.answering.service import build_budgeted_prompt,AnswerBudget
    docs=[dict(chunk_id='parent',text='长前提'*100),dict(chunk_id='child',text='后半块'),dict(chunk_id='short',text='短独立证据')]
    packed=build_budgeted_prompt(docs,[],question='参数',items='AX',groups=[['parent','child']],
        render=lambda **kw:kw['context']+kw['history']+kw['question'],
        budget=AnswerBudget(context_window=256,output_tokens=32,reserve_tokens=16))
    assert packed['used_doc_indices']==[2]
    assert '后半块' not in packed['prompt']


def test_injected_tokenizer_is_measured_on_full_render_and_output_limit_reaches_client(answer_node):
    state=dict(original_query='参数',reranked_docs=[dict(chunk_id='c',text='24V')],
        answer_budget=dict(context_window=2048,output_tokens=256),token_counter=lambda s:len(s))
    prompt=answer_node.module.step_2_construct_prompt(state)
    assert state['prompt_budget']['input_tokens']==len(prompt)
    assert state['prompt_budget']['counter']=='provided_tokenizer'
    from types import SimpleNamespace
    calls=[]
    client=SimpleNamespace(invoke=lambda p,**kw:calls.append(kw) or SimpleNamespace(content='24V [1]'))
    answer_node.module.step_3_generate_response(state,prompt,client=client)
    assert calls==[dict(extra_body=dict(max_tokens=256))]


def test_output_length_finish_reason_is_preserved_as_partial(answer_node):
    from types import SimpleNamespace
    state=dict(is_stream=False,answer_max_tokens=256)
    client=SimpleNamespace(invoke=lambda *a,**kw:SimpleNamespace(content='部分内容',response_metadata=dict(finish_reason='length')))
    answer_node.module.step_3_generate_response(state,'合成提示',client=client)
    assert state.get('output_truncated') is True


@pytest.mark.parametrize('field',['max_tokens','max_completion_tokens'])
@pytest.mark.parametrize('stream',[False,True])
def test_installed_langchain_sends_limit_without_rewriting_or_losing_vendor_flags(answer_node,monkeypatch,field,stream):
    import httpx,json
    from langchain_openai.chat_models.base import ChatOpenAI
    bodies=[]
    def reply(request):
        bodies.append(json.loads(request.content))
        if stream:
            events=[dict(id='synthetic',object='chat.completion.chunk',created=0,model='synthetic',
                choices=[dict(index=0,delta=dict(role='assistant',content='24V [1]'),finish_reason=None)]),
                dict(id='synthetic',object='chat.completion.chunk',created=0,model='synthetic',
                choices=[dict(index=0,delta={},finish_reason='stop')])]
            return httpx.Response(200,text=''.join('data: '+json.dumps(e)+'\n\n' for e in events)+'data: [DONE]\n\n',
                headers={'content-type':'text/event-stream'})
        return httpx.Response(200,json=dict(id='synthetic',object='chat.completion',created=0,model='synthetic',
            choices=[dict(index=0,message=dict(role='assistant',content='24V [1]'),finish_reason='stop')]))
    with httpx.Client(transport=httpx.MockTransport(reply)) as transport:
        client=ChatOpenAI(model='synthetic',api_key='synthetic-not-secret',base_url='https://synthetic.invalid/v1',
            http_client=transport,max_retries=0,extra_body=dict(enable_thinking=False,max_tokens=999))
        state=dict(answer_max_tokens=256,answer_token_field=field,is_stream=stream,session_id='synthetic-sdk')
        monkeypatch.setattr(answer_node.module,'push_to_session',lambda *a,**kw:None)
        answer_node.module.step_3_generate_response(state,'合成提示',client=client)
        assert client.extra_body['max_tokens']==999
    assert bodies[0].get(field)==256
    assert ('max_completion_tokens' if field=='max_tokens' else 'max_tokens') not in bodies[0]
    assert bodies[0]['enable_thinking'] is False


@pytest.mark.parametrize('overrides',[dict(context_window=128),dict(output_tokens=0),
    dict(reserve_tokens=True),dict(context_window=512,output_tokens=500),dict(max_chars=12001),
    dict(output_token_field='unknown'),dict(unknown=1)])
def test_invalid_answer_budget_rejected(overrides):
    from app.answering.service import AnswerBudget
    with pytest.raises(ValueError):AnswerBudget(**overrides)


def test_exact_token_boundary_and_policy_wrapper_preserve_limit_without_mutating_client():
    from app.answering.service import AnswerBudget,build_budgeted_prompt
    from app.infrastructure.providers.clients import PolicyChatClient,output_limit_options
    from types import SimpleNamespace
    body=dict(enable_thinking=False,max_tokens=999)
    client=SimpleNamespace(extra_body=body)
    wrapper=PolicyChatClient(client,None)
    assert output_limit_options(wrapper,256,'max_completion_tokens')==dict(extra_body=dict(enable_thinking=False,max_completion_tokens=256))
    assert client.extra_body==body and body['max_tokens']==999
    result=build_budgeted_prompt([],[],question='x'*224,items='',render=lambda **kw:kw['question'],
        budget=AnswerBudget(context_window=256,output_tokens=16,reserve_tokens=16))
    assert result['budget']['input_tokens']==224
    with pytest.raises(APIError):
        build_budgeted_prompt([],[],question='x'*225,items='',render=lambda **kw:kw['question'],
            budget=AnswerBudget(context_window=256,output_tokens=16,reserve_tokens=16))
