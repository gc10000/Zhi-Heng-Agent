"""固定单成员准入只用合成配置、题目与Git来源，不读私有产品答案。"""
import copy
import json
import hashlib
from types import SimpleNamespace
import pytest


def contract_value():
    return dict(function_version='diagnostic_source_relation_048_v1',thinking=False,
        endpoint_sha256='a'*64,model='synthetic',client_versions={'openai':'synthetic'},ledger_id='synthetic',
        max_total_output_tokens=33649,admission=dict(authorization=dict(commit='a'*40,path='docs/synthetic.json',sha256='b'*64),
            manifest_sha256='c'*64,member_slot='synthetic'))


def test_single_profile_default_off_and_strict_false():
    from app.infrastructure.providers.output_contract import parse_contract,is_product_risk,payload
    value=contract_value(); p=parse_contract(value)
    assert not p.enabled and not is_product_risk(p) and payload(p) is None
    for v in (None,True,0,'false'):
        with pytest.raises(ValueError):parse_contract(value|dict(thinking=v))


def make_sr048_case(tmp_path,monkeypatch,*,configs=None,questions=None,expected=None,controls=None,target_database=None):
    from app.infrastructure.providers import source_relation_048_risk as r
    from app.infrastructure.providers.output_contract import parse_contract
    from app.knowledge.repository import fingerprint as fp
    from importlib.metadata import version
    monkeypatch.setattr(r,'ROOT',tmp_path)
    def save(name,v):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(v),encoding='utf8');return hashlib.sha256(p.read_bytes()).hexdigest()
    cfg=copy.deepcopy(configs[0]) if configs else dict(strategy='m4-configured',
        target=dict(database='m1_test_m4_sr',collection='synthetic',owner_id='owner',kb_id='kb',bucket='existing',object_prefix='synthetic/'),
        parameters=dict(answer_budget=dict(context_window=32768,output_tokens=4096,reserve_tokens=256,max_chars=12000)),
        dataset_sha256='a'*64,split_manifest_sha256='b'*64,versions=dict(code='c'*64,prompt='d'*64,model='e'*64),
        phase='development',split='dev',execution_mode='real_query_runner',metric_schema_version=1)
    if target_database:cfg['target']['database']=target_database
    q=copy.deepcopy(questions[0]) if questions else dict(id=r.QUESTION_ID,question='合成比较问题',product_names=['AX','BX'],history=[])
    monkeypatch.setattr(r,'QUESTION_ID',q['id'])
    cfg['question_ids']=[q['id']]
    value=copy.deepcopy(expected[0]) if expected else dict(prompt='合成输入',context=[],groups=[],prompt_reference_map=[],budget=dict(input_tokens=12,input_limit=28416))
    source_cfg=copy.deepcopy(cfg); source_cfg['experiment_id']='synthetic-parent'
    path='output/anchor.json'; anchor=dict(new_config=source_cfg,result=value)
    member=dict(version=1,ordinal=27,question_id=q['id'],expected_generation=True,fixed_slot=r.SLOT,source_input_path=path,
        source_input_file_sha256=save(path,anchor),source_config_sha256=fp(source_cfg),source_result_sha256=fp(value),
        dataset_sha256=cfg['dataset_sha256'],split_manifest_sha256=cfg['split_manifest_sha256'],prompt_utf8_sha256=hashlib.sha256(value['prompt'].encode()).hexdigest())
    control=(controls or ['m1_test_m4_control'])[0]
    master=dict(version_sources=[dict(version=1,control_database=control,owner_id=cfg['target']['owner_id'],kb_id=cfg['target']['kb_id'])])
    mastersha=save('output/master.json',master); executionsha=save('output/original.json',dict(entries=[]))
    extractor=tmp_path/'app/answering/source_relations.py';extractor.parent.mkdir(parents=True);extractor.write_text('synthetic',encoding='utf8')
    prior=dict(input_tokens=46973,output_tokens=29553,sources=dict(synthetic=True));prior['sha256']=fp(prior)
    monkeypatch.setattr(r,'prior_receipt',lambda:prior)
    monkeypatch.setattr(r,'code_version',lambda:cfg['versions']['code'])
    monkeypatch.setattr(r,'authorized_inputs',lambda a,m:{k:q[k] for k in ('id','question','product_names','history')})
    ref=dict(commit='a'*40,path='docs/synthetic-sr048.json',sha256='f'*64)
    auth=dict(kind='coordinator_scoped_source_relation_048_single_authorization',admission_version=r.VERSION,
        fixed_batch_slot=r.BATCH,members=[member],dispatch_order=[r.SLOT],prompt_version=cfg['versions']['prompt'],
        original_master_path='output/master.json',original_master_file_sha256=mastersha,
        original_execution_manifest_path='output/original.json',original_execution_manifest_sha256=executionsha,
        reviewed_extractor_file_sha256=hashlib.sha256(extractor.read_bytes()).hexdigest(),
        risk=dict(gateway_capability_status='unknown',coordinator_accepts_unknown_paid_upper_bound_only_for_this_fixed_single_stream=True),
        runtime=dict(n=1,model='synthetic',endpoint_sha256=fp('https://synthetic.invalid/v1'),client_versions={k:version(k) for k in ('openai','langchain-openai')},
            limit_field='max_completion_tokens',requested_total_output_tokens=4096,thinking=False,temperature=.1,timeout_seconds=120),
        budget=dict(context_window=32768,output_tokens_requested=4096,reserve_tokens=256,max_chars=12000,single_input_limit=28416,
            prior_diagnostic_input_tokens=46973,prior_diagnostic_output_tokens=29553,max_total_diagnostic_input_tokens=75389,max_total_diagnostic_output_tokens=33649,
            max_new_product_jobs=1,max_new_product_streams=1,max_attempts_per_member=1))
    monkeypatch.setattr(r,'AUTHORIZED_GIT',ref);monkeypatch.setattr(r,'evidence_bytes',lambda _:json.dumps(auth).encode())
    policy=dict(enabled=True,function_version=r.VERSION,thinking=False,n=1,status='unknown',semantics='unknown',model='synthetic',
        endpoint_sha256=auth['runtime']['endpoint_sha256'],client_versions=auth['runtime']['client_versions'],limit_field='max_completion_tokens',ledger_id=r.BATCH,
        prior_input_tokens=46973,prior_output_tokens=29553,prior_source_sha256=prior['sha256'],max_total_input_tokens=75389,max_total_output_tokens=33649,
        admission=dict(authorization=ref,manifest_sha256='0'*64,member_slot=r.SLOT))
    cfg['experiment_id']=r.SLOT;cfg['parameters']['answer_budget'].update(output_token_field='max_completion_tokens',output_contract=parse_contract(policy).model_dump(mode='json'))
    manifest=r.build_manifest([(cfg,q,control)]);cfg['parameters']['answer_budget']['output_contract']['admission']['manifest_sha256']=fp(manifest)
    r.prepare_manifest(manifest)
    return SimpleNamespace(module=r,configs=[cfg],questions=[q],expected=[value],controls=[control],policies=[parse_contract(cfg['parameters']['answer_budget']['output_contract'])],manifest=manifest,auth=auth,fp=fp,save=save)


@pytest.fixture
def sr_case(tmp_path,monkeypatch):return make_sr048_case(tmp_path,monkeypatch)


@pytest.mark.parametrize('drift',['authorization','member','version','question','history','prompt','context','config','code','dataset','prior','ledger'])
def test_single_admission_rejects_identity_drift(sr_case,drift):
    c=sr_case;cfg=copy.deepcopy(c.configs[0]);q=copy.deepcopy(c.questions[0]);p=cfg['parameters']['answer_budget']['output_contract']
    if drift=='authorization':p['admission']['authorization']['sha256']='0'*64
    if drift=='member':p['admission']['member_slot']='another'
    if drift=='version':c.auth['members'][0]['version']=2
    if drift=='question':q['question']='变更题目'
    if drift=='history':q['history']=[dict(role='user',content='变更历史')]
    if drift in ('prompt','context'):
        anchor=json.loads(c.module.local(c.auth['members'][0]['source_input_path']).read_text('utf8'));anchor['result'][drift]='变更来源'
        c.save(c.auth['members'][0]['source_input_path'],anchor)
    if drift=='config':cfg['parameters']['extra']='未授权'
    if drift=='code':cfg['versions']['code']='0'*64
    if drift=='dataset':cfg['dataset_sha256']='0'*64
    if drift=='prior':p['prior_output_tokens']=0
    if drift=='ledger':p['ledger_id']='new'
    with pytest.raises((ValueError,FileNotFoundError)):c.module.validate_config(cfg,c.controls[0],question=q)


def test_single_member_and_missing_git_are_rejected(sr_case,monkeypatch):
    c=sr_case
    with pytest.raises(ValueError):c.module.build_manifest([(c.configs[0],c.questions[0],c.controls[0])]*2)
    def absent(_):raise ValueError('合成封存授权缺失')
    monkeypatch.setattr(c.module,'evidence_bytes',absent)
    with pytest.raises(ValueError):c.module.require(c.policies[0])


def test_full_prompt_groups_and_budget_still_exact(sr_case):
    from tests.unit.test_remaining_manifest import test_prompt_groups_refs_budget_remain_exact
    test_prompt_groups_refs_budget_remain_exact(sr_case)


@pytest.mark.parametrize('conflict',['n','typed_limit','kwargs','thinking','reasoning_effort','both_fields'])
def test_single_wire_preserves_strict_false(sr_case,conflict):
    import httpx
    from app.infrastructure.providers.diagnostic_usage import preserving_chat_class
    from app.infrastructure.providers.output_contract import strict_options
    with httpx.Client(transport=httpx.MockTransport(lambda q:pytest.fail('不可联网')),follow_redirects=False) as http:
        sdk=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',n=1,
            stream_usage=True,max_retries=0,timeout=120,temperature=.1,http_client=http,extra_body={'enable_thinking':False})
        assert strict_options(sdk,4096,'max_completion_tokens',sr_case.policies[0])==dict(n=1,extra_body=dict(enable_thinking=False,max_completion_tokens=4096))
        if conflict=='n':sdk.n=2
        if conflict=='typed_limit':sdk.max_tokens=4096
        if conflict=='kwargs':sdk.model_kwargs={'n':1}
        if conflict=='thinking':sdk.extra_body={'enable_thinking':True}
        if conflict=='reasoning_effort':sdk.reasoning_effort='low'
        if conflict=='both_fields':sdk.extra_body.update(max_tokens=4096)
        with pytest.raises(ValueError):strict_options(sdk,4096,'max_completion_tokens',sr_case.policies[0])


@pytest.mark.parametrize('drift',[False,True])
def test_previous_nonthinking_account_kept_blocked(sr_case,drift):
    c=sr_case;c.auth.update(previous_batch='old',previous_account_snapshot_path='output/old-account.json')
    c.save('output/m6-authorized-products/old/planned.json',dict(shared_control_database='old-control'))
    saved=dict(_id='old',state='blocked',pending=None,unknown_windows=[]);c.save('output/old-account.json',saved)
    actual=copy.deepcopy(saved)
    if drift:actual['state']='open'
    client={'old-control':{'diagnostic_nonthinking_accounts':SimpleNamespace(find_one=lambda q:actual)}}
    if drift:
        with pytest.raises(ValueError):c.module.validate_previous_account(c.policies[0],client)
    else:c.module.validate_previous_account(c.policies[0],client)
