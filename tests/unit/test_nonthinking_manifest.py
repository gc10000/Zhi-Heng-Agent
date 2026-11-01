"""显式非思考清单的默认关闭、唯一wire和归一化前模式观测。"""
import json
import pytest
from tests.unit.test_remaining_manifest import make_remaining_case


def make_nonthinking_case(tmp_path,monkeypatch,**kw):
    from app.infrastructure.providers import nonthinking_risk as r
    return make_remaining_case(tmp_path,monkeypatch,profile=r,**kw)


@pytest.fixture
def nonthinking_case(tmp_path,monkeypatch):return make_nonthinking_case(tmp_path,monkeypatch)


@pytest.mark.parametrize('drift',['member','control','target','input','ledger','prior','code','version','dataset','manifest'])
def test_nonthinking_member_identity(nonthinking_case,drift):
    from tests.unit.test_remaining_manifest import test_member_identity_drift_refuses
    test_member_identity_drift_refuses(nonthinking_case,drift)


def test_nonthinking_initial_input_and_prompt_exact(nonthinking_case):
    from tests.unit.test_remaining_manifest import test_forged_initial_question_cannot_obtain_a_new_frozen_plan,test_prompt_groups_refs_budget_remain_exact
    test_forged_initial_question_cannot_obtain_a_new_frozen_plan(nonthinking_case)
    test_prompt_groups_refs_budget_remain_exact(nonthinking_case)


@pytest.mark.parametrize('value',[None,True,0,'false'])
def test_nonthinking_wire_requires_strict_false(nonthinking_case,value):
    import httpx
    from app.infrastructure.providers.diagnostic_usage import preserving_chat_class
    from app.infrastructure.providers.output_contract import strict_options
    with httpx.Client(transport=httpx.MockTransport(lambda q:pytest.fail('不可联网')),follow_redirects=False) as http:
        client=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',
            http_client=http,n=1,stream_usage=True,max_retries=0,timeout=120,temperature=.1,extra_body={'enable_thinking':False})
        assert strict_options(client,4096,'max_completion_tokens',nonthinking_case.policies[0])==dict(n=1,extra_body=dict(enable_thinking=False,max_completion_tokens=4096))
        client.extra_body={} if value is None else {'enable_thinking':value}
        with pytest.raises(ValueError):strict_options(client,4096,'max_completion_tokens',nonthinking_case.policies[0])


def test_nonthinking_missing_git_authorization_refuses(nonthinking_case,monkeypatch):
    def absent(_):raise ValueError('合成Git来源缺失')
    monkeypatch.setattr(nonthinking_case.module,'evidence_bytes',absent)
    with pytest.raises(ValueError):nonthinking_case.module.require(nonthinking_case.policies[0])


def test_optional_reasoning_not_proof_of_hard_disable():
    from app.infrastructure.providers.diagnostic_usage import observe_usage,summarize
    v=summarize([observe_usage(dict(prompt_tokens=3,completion_tokens=2,total_tokens=5),source='sdk_raw')])
    assert v['valid'] and v['complete'] and v['reported']['reasoning'] is None


@pytest.mark.parametrize('drift',[False,True])
def test_old_blocked_account_must_match_readonly_snapshot(nonthinking_case,drift):
    import copy
    from types import SimpleNamespace
    c=nonthinking_case
    c.auth.update(previous_batch='old-blocked',previous_account_snapshot_path='output/old-account.json')
    c.save('output/m6-authorized-products/old-blocked/planned.json',dict(shared_control_database='old-control'))
    saved=dict(_id='old',state='blocked',pending=None,unknown_windows=[])
    c.save('output/old-account.json',saved)
    actual=copy.deepcopy(saved)
    if drift:actual['state']='open'
    reads=[]
    def find(query):reads.append(query);return actual
    client={'old-control':{'diagnostic_remaining_accounts':SimpleNamespace(find_one=find)}}
    if drift:
        with pytest.raises(ValueError):c.module.validate_previous_account(c.policies[0],client)
    else:c.module.validate_previous_account(c.policies[0],client)
    assert reads==[{'_id':'old'}]


def test_nonthinking_contract_default_off_and_explicit_false():
    from app.infrastructure.providers.output_contract import NonthinkingManifestContract,parse_contract,is_product_risk
    v=dict(endpoint_sha256='a'*64,model='synthetic',client_versions={'openai':'synthetic'},ledger_id='batch',
        max_total_output_tokens=8192,thinking=False,admission=dict(authorization=dict(commit='a'*40,path='docs/synthetic.json',sha256='b'*64),manifest_sha256='c'*64,member_slot='member'))
    p=NonthinkingManifestContract.model_validate(v)
    assert not p.enabled and not is_product_risk(p) and parse_contract(v|dict(function_version='diagnostic_nonthinking_manifest_r1'))==p
    for value in [True,0,'false',None]:
        with pytest.raises(ValueError):NonthinkingManifestContract.model_validate(v|dict(thinking=value))
    v.pop('thinking')
    with pytest.raises(ValueError):NonthinkingManifestContract.model_validate(v)


@pytest.mark.parametrize('text',['推理内容',''])
def test_raw_sdk_reasoning_observation_survives_normalization(text):
    import httpx
    from app.infrastructure.providers.diagnostic_usage import preserving_chat_class,capture_usage
    chunk=dict(id='synthetic',object='chat.completion.chunk',created=1,model='synthetic',choices=[dict(index=0,delta=dict(content='合成正文',reasoning_content=text),finish_reason='stop')],usage=dict(prompt_tokens=3,completion_tokens=2,total_tokens=5))
    observed=[];mode=[];wires=[]
    def handle(req):
        wires.append(json.loads(req.content))
        return httpx.Response(200,headers={'content-type':'text/event-stream'},content='data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n')
    with httpx.Client(transport=httpx.MockTransport(handle)) as http:
        llm=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',http_client=http,max_retries=0,stream_usage=True)
        with capture_usage(observed,mode_observations=mode):
            list(llm.stream('合成输入',n=1,extra_body={'enable_thinking':False,'max_completion_tokens':4096}))
    assert bool(mode)==bool(text)
    assert observed[-1]['counts']['reasoning'] is None
    assert wires[0]['enable_thinking'] is False and wires[0]['max_completion_tokens']==4096 and wires[0]['n']==1
