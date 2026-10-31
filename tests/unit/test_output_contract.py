"""诊断输出合同仅测确定协议；合成供应商能力不证明真实网关语义。"""
from types import SimpleNamespace
import pytest
from app.answering.service import AnswerBudget
from app.infrastructure.providers.clients import output_limit_options
from app.knowledge.repository import fingerprint
from importlib.metadata import version


def verified_case(monkeypatch, *, field='max_tokens', thinking=None, reasoning_budget=None):
    import json
    import app.infrastructure.providers.output_contract as module
    client=SimpleNamespace(openai_api_base='https://synthetic.invalid/v1',model_name='synthetic',max_retries=0,
        extra_body={},model_kwargs={})
    if thinking is not None:client.extra_body['enable_thinking']=thinking
    if reasoning_budget is not None:client.extra_body['thinking_budget']=reasoning_budget
    p=dict(enabled=True,status='verified',n=1,endpoint_sha256=fingerprint(str(client.openai_api_base)),model='synthetic',
        client_versions={'openai':version('openai'),'langchain-openai':version('langchain-openai')},
        semantics='total_including_reasoning',limit_field=field,thinking=thinking,reasoning_budget=reasoning_budget,
        evidence=dict(commit='a'*40,path='docs/synthetic-output-evidence.json',sha256='b'*64),
        ledger_id='synthetic-budget',max_total_output_tokens=9000)
    proof=dict(kind='gateway_output_capability_evidence_v1',status='verified',server_hard_limit=True,
        evidence_type='authorized_gateway_probe',max_verified_total_tokens=4096,
        identity={k:p[k] for k in ('endpoint_sha256','model','client_versions','limit_field','semantics','thinking','reasoning_budget','n')})
    monkeypatch.setattr(module,'evidence_bytes',lambda _:json.dumps(proof).encode())
    return p,client,proof


def test_old_budget_identity_remains_byte_equivalent():
    assert AnswerBudget().model_dump() == dict(context_window=32768,output_tokens=4096,
        reserve_tokens=256,max_chars=12000,output_token_field='max_tokens')


def test_unknown_output_semantics_rejected_before_any_client_call():
    from app.infrastructure.providers.output_contract import OutputContract, require_capability
    policy=OutputContract(enabled=True,endpoint_sha256='a'*64,model='synthetic',client_versions={'synthetic':'1'},
        ledger_id='synthetic',max_total_output_tokens=8192)
    with pytest.raises(Exception,match='unknown|未知'):
        require_capability(policy)


def test_new_contract_does_not_silently_replace_conflicting_limit_fields():
    client=SimpleNamespace(extra_body={'max_completion_tokens':4096})
    with pytest.raises(ValueError):
        output_limit_options(client,4096,'max_tokens',contract={'enabled':True})


def test_usage_total_is_never_increased_by_reasoning():
    from app.infrastructure.providers.output_contract import usage_receipt
    result=usage_receipt({'input':7,'output':6150},reasoning=5556)
    assert result['output_tokens']==6150
    assert result['output_minus_reasoning']==594 and result['visible_tokens'] is None
    assert result['http_requests'] is None and result['cost'] is None


@pytest.mark.parametrize('bad',[None,-1,True,'4096'])
def test_missing_or_invalid_usage_stays_unknown(bad):
    from app.infrastructure.providers.output_contract import usage_receipt
    assert usage_receipt({'input':3,'output':bad})['output_tokens'] is None


@pytest.mark.parametrize('field',['max_tokens','max_completion_tokens'])
def test_approved_total_limit_preserves_thinking_and_independent_budget(monkeypatch,field):
    p,client,_=verified_case(monkeypatch,field=field,thinking=True,reasoning_budget=100)
    before=dict(client.extra_body)
    assert output_limit_options(client,4096,field,contract=p)==dict(n=1,extra_body=before|{field:4096})
    assert client.extra_body==before


@pytest.mark.parametrize('drift',['endpoint','model','sdk','field','cap','extra','both','kwargs','thinking','reasoning','retries','default','float_limit','other_thinking'])
def test_wire_identity_and_conflicts_fail_closed(monkeypatch,drift):
    p,client,_=verified_case(monkeypatch)
    field='max_tokens';limit=4096
    if drift=='endpoint':client.openai_api_base='https://other.invalid/v1'
    if drift=='model':client.model_name='other'
    if drift=='sdk':p['client_versions']['openai']='wrong'
    if drift=='field':field='max_completion_tokens'
    if drift=='cap':limit=8192
    if drift=='extra':client.extra_body={'max_tokens':8192}
    if drift=='both':client.extra_body={'max_tokens':4096,'max_completion_tokens':4096}
    if drift=='kwargs':client.model_kwargs={'max_tokens':4096}
    if drift=='thinking':client.extra_body={'enable_thinking':True}
    if drift=='reasoning':client.extra_body={'thinking_budget':1}
    if drift=='retries':client.max_retries=1
    if drift=='default':client.max_tokens=4096
    if drift=='float_limit':client.extra_body={'max_tokens':4096.0}
    if drift=='other_thinking':client.extra_body={'thinking':{'type':'enabled'}}
    with pytest.raises(Exception):output_limit_options(client,limit,field,contract=p)


@pytest.mark.parametrize('drift',['status','semantics','hard','model','range','evidence_type','missing'])
def test_unsupported_or_inapplicable_gateway_proof_is_not_a_wire_success(monkeypatch,drift):
    from app.infrastructure.providers.output_contract import require_capability
    p,_,proof=verified_case(monkeypatch)
    if drift=='status':p['status']='unknown'
    if drift=='semantics':p['semantics']='visible'
    if drift=='hard':proof['server_hard_limit']=False
    if drift=='model':proof['identity']['model']='other'
    if drift=='range':proof['max_verified_total_tokens']=100
    if drift=='evidence_type':proof['evidence_type']='mock_transport'
    if drift=='missing':p['evidence']=None
    with pytest.raises(Exception):require_capability(p)


def test_run_contract_is_internal_and_drift_rejects_old_success():
    from app.runs.models import RunInput,InternalRunInput
    from app.infrastructure.providers.output_contract import validate_run,identity
    p=dict(enabled=True,endpoint_sha256='a'*64,model='synthetic',client_versions={'openai':'1'},ledger_id='x',max_total_output_tokens=8192)
    data=dict(question='合成题',kb_id='k',client_request_id='new')
    with pytest.raises(ValueError):RunInput(**data,output_contract=p)
    assert InternalRunInput(**data,output_contract=p).output_contract.enabled
    saved=identity(p);validate_run(saved,p)
    with pytest.raises(Exception):validate_run({},p)
    with pytest.raises(Exception):validate_run(saved,p|{'max_total_output_tokens':9000})


def test_budget_contract_cannot_change_total_4096_to_visible_or_larger_cap():
    p=dict(enabled=True,endpoint_sha256='a'*64,model='synthetic',client_versions={'openai':'1'},ledger_id='x',max_total_output_tokens=8192)
    with pytest.raises(ValueError):AnswerBudget(output_tokens=4097,output_contract=p)
    assert AnswerBudget(output_contract=p).output_contract.status=='unknown'


@pytest.mark.parametrize('field',['max_tokens','max_completion_tokens'])
def test_installed_sdk_mock_wire_preserves_exact_requested_field(monkeypatch,field):
    # 实际安装SDK＋MockTransport，只证明wire，不证明供应商总输出限制。
    import json,httpx
    from langchain_openai.chat_models.base import ChatOpenAI
    from app.infrastructure.providers.output_contract import strict_options
    p,_,_=verified_case(monkeypatch,field=field,thinking=True)
    sent=[]
    def handle(req):
        sent.append(json.loads(req.content))
        return httpx.Response(200,json=dict(id='synthetic',object='chat.completion',created=1,model='synthetic',
            choices=[dict(index=0,message=dict(role='assistant',content='synthetic'),finish_reason='stop')],
            usage=dict(prompt_tokens=4,completion_tokens=9,total_tokens=13)))
    with httpx.Client(transport=httpx.MockTransport(handle)) as transport:
        client=ChatOpenAI(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',
            max_retries=0,http_client=transport,extra_body={'enable_thinking':True})
        response=client.invoke('synthetic',**strict_options(client,4096,field,p))
    assert sent[0][field]==4096 and sent[0]['enable_thinking'] is True
    assert ('max_completion_tokens' if field=='max_tokens' else 'max_tokens') not in sent[0]
    assert response.usage_metadata['output_tokens']==9
