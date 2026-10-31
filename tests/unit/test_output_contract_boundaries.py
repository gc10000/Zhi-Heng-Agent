"""单份wire与原始usage边界；只使用合成SDK传输，不证明真实网关能力。"""
import json
from types import SimpleNamespace
import httpx
import pytest
from tests.unit.test_output_contract import verified_case


@pytest.mark.parametrize('mode',['normal','typed_two','typed_bool','kwargs_two','kwargs_one','extra_two','extra_one','best_of','max_new_tokens'])
def test_single_completion_is_bound_at_all_parameter_entrances(monkeypatch,mode):
    from langchain_openai.chat_models.base import ChatOpenAI
    from app.infrastructure.providers.output_contract import strict_options,identity
    p,_,_=verified_case(monkeypatch);sent=[]
    def handle(req):
        sent.append(json.loads(req.content))
        return httpx.Response(200,json=dict(id='synthetic',object='chat.completion',created=1,model='synthetic',
            choices=[dict(index=0,message=dict(role='assistant',content='synthetic'),finish_reason='stop')],
            usage=dict(prompt_tokens=3,completion_tokens=8,total_tokens=11)))
    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        c=ChatOpenAI(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',
            max_retries=0,n=1,http_client=transport)
        if mode=='typed_two':c.n=2
        if mode=='typed_bool':c.n=True
        if mode.startswith('kwargs_'):c.model_kwargs['n']=2 if mode.endswith('two') else 1
        if mode.startswith('extra_'):c.extra_body={'n':2 if mode.endswith('two') else 1}
        if mode in ('best_of','max_new_tokens'):c.model_kwargs[mode]=2
        if mode!='normal':
            with pytest.raises(ValueError):strict_options(c,4096,'max_tokens',p)
            assert not sent
        else:
            c.invoke('synthetic',**strict_options(c,4096,'max_tokens',p))
            assert sent[0]['n']==1 and sent[0]['max_tokens']==4096
            assert identity(p)['output_contract']['n']==1


def test_old_diagnostic_identity_cannot_be_silently_upgraded(monkeypatch):
    from app.infrastructure.providers.output_contract import identity,validate_run
    p,_,_=verified_case(monkeypatch)
    current=identity(p)
    assert current['output_contract']['function_version']=='diagnostic_total_output_v2'
    old=dict(current);old['output_contract']=dict(current['output_contract'],function_version='diagnostic_total_output_v1')
    old['output_contract'].pop('n',None)
    with pytest.raises(Exception):validate_run(old,p)
    with pytest.raises(ValueError):identity(p|{'n':2})


@pytest.mark.parametrize('reasoning',[None,0,8,9,-1,True,9.5,'9'])
def test_raw_detail_validation_does_not_erase_bad_values(monkeypatch,reasoning):
    from app.infrastructure.providers.output_contract import usage_receipt
    r=usage_receipt({'input':3,'output':8},reasoning=reasoning)
    valid=reasoning is None or type(reasoning) is int and 0<=reasoning<=8
    assert r['usage_validation']['valid']==valid
    if not valid:
        assert r['output_tokens'] is None and r['reported_output_tokens']==8
        assert r['usage_validation']['observations'][0]['fields']['reasoning'][0]['raw_type']==type(reasoning).__name__


@pytest.mark.parametrize('reasoning',[None,0,8,9,-1,True,9.5,'9'])
def test_installed_sdk_stream_keeps_pre_normalization_usage(monkeypatch,reasoning):
    from app.infrastructure.providers.diagnostic_usage import preserving_chat_class
    from app.query_process.agent.nodes.node_answer_output import step_3_generate_response
    from app.answering.errors import AnswerGenerationError
    from app.infrastructure.providers.output_contract import usage_receipt
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',lambda *a:None)
    p,_,_=verified_case(monkeypatch)
    usage=dict(prompt_tokens=3,completion_tokens=8,total_tokens=11)
    if reasoning is not None:usage['completion_tokens_details']={'reasoning_tokens':reasoning}
    def handle(req):
        chunk=dict(id='synthetic',object='chat.completion.chunk',created=1,model='synthetic',
            choices=[dict(index=0,delta=dict(role='assistant',content='synthetic'),finish_reason='stop')],usage=usage)
        return httpx.Response(200,headers={'content-type':'text/event-stream'},content='data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n')
    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        c=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',
            max_retries=0,n=1,http_client=transport,stream_usage=True)
        state=dict(session_id='synthetic',is_stream=True,answer_max_tokens=4096,output_contract=p)
        try:step_3_generate_response(state,'synthetic',client=c)
        except AnswerGenerationError:pass
    r=usage_receipt({'input':3,'output':8},observations=state['answer_usage_observations'])
    valid=reasoning is None or type(reasoning) is int and 0<=reasoning<=8
    assert r['usage_validation']['valid']==valid
    assert r['usage_validation']['observations'][0]['source']=='sdk_raw'
    if reasoning is not None:
        observed=r['usage_validation']['observations'][0]['fields']['reasoning'][0]
        assert observed['raw_type']==type(reasoning).__name__ and observed['value']==reasoning


def test_raw_missing_totals_cannot_become_normalized_zero(monkeypatch):
    from app.infrastructure.providers.diagnostic_usage import observe_usage
    from app.infrastructure.providers.output_contract import usage_receipt
    r=usage_receipt({'input':0,'output':0},observations=[observe_usage({},source='sdk_raw')])
    assert r['output_tokens'] is None and not r['usage_validation']['complete']


def test_invalid_earlier_fragment_is_not_erased_by_later_good_usage():
    from app.infrastructure.providers.diagnostic_usage import observe_usage
    from app.infrastructure.providers.output_contract import usage_receipt
    a=observe_usage({'input_tokens':3,'output_tokens':8,'output_token_details':{'reasoning':True}},source='sdk_raw')
    b=observe_usage({'input_tokens':3,'output_tokens':8,'output_token_details':{'reasoning':2}},source='sdk_raw')
    assert not usage_receipt({'input':3,'output':8},observations=[a,b])['usage_validation']['valid']


@pytest.mark.parametrize('detail',[None,{},[],True,{'reasoning':None},{'reasoning':8},{'reasoning':False}])
def test_empty_and_malformed_details_are_distinct(detail):
    from app.infrastructure.providers.diagnostic_usage import observe_usage
    from app.infrastructure.providers.output_contract import usage_receipt
    o=observe_usage(dict(input_tokens=3,output_tokens=8,output_token_details=detail),source='sdk_raw')
    valid=detail is None or detail=={} or detail=={'reasoning':None} or type(detail) is dict and type(detail.get('reasoning')) is int and detail['reasoning']==8
    assert usage_receipt({'input':3,'output':8},observations=[o])['usage_validation']['valid']==valid
    assert o['containers'][0]['raw_type']==type(detail).__name__


@pytest.mark.parametrize('reasoning',[True,'9'])
def test_installed_sdk_nonstream_also_preserves_wire_detail(monkeypatch,reasoning):
    from app.infrastructure.providers.diagnostic_usage import preserving_chat_class
    from app.query_process.agent.nodes.node_answer_output import step_3_generate_response
    from app.infrastructure.providers.output_contract import usage_receipt
    p,_,_=verified_case(monkeypatch)
    def handle(req):
        return httpx.Response(200,json=dict(id='synthetic',object='chat.completion',created=1,model='synthetic',
            choices=[dict(index=0,message=dict(role='assistant',content='synthetic'),finish_reason='stop')],
            usage=dict(prompt_tokens=3,completion_tokens=8,total_tokens=11,completion_tokens_details={'reasoning_tokens':reasoning})))
    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        c=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',max_retries=0,http_client=transport)
        state=dict(is_stream=False,answer_max_tokens=4096,output_contract=p)
        step_3_generate_response(state,'synthetic',client=c)
    receipt=usage_receipt({'input':3,'output':8},observations=state['answer_usage_observations'])
    assert not receipt['usage_validation']['valid']
    assert receipt['usage_validation']['observations'][0]['fields']['reasoning'][0]['raw_type']==type(reasoning).__name__
