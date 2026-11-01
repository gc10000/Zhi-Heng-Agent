"""剩余清单准入仅使用合成来源，不读取产品答案。"""
import copy
import json
from types import SimpleNamespace
import pytest


def test_remaining_contract_is_explicit_and_default_off():
    from app.infrastructure.providers.output_contract import RemainingManifestContract, parse_contract, is_product_risk
    p = RemainingManifestContract.model_validate(dict(endpoint_sha256='a'*64, model='synthetic',
        client_versions={'openai':'synthetic'}, ledger_id='batch', max_total_output_tokens=8192,
        admission=dict(authorization=dict(commit='a'*40,path='docs/synthetic.json',sha256='b'*64),
                       manifest_sha256='c'*64,member_slot='member')))
    assert not p.enabled and not is_product_risk(p)
    assert parse_contract(p.model_dump(mode='json')) == p


def make_remaining_case(tmp_path, monkeypatch, *, configs=None, questions=None, expected=None, controls=None,targets=None):
    from app.infrastructure.providers import remaining_risk as r
    from app.infrastructure.providers import product_risk as single
    from app.infrastructure.providers.output_contract import parse_contract
    from app.knowledge.repository import fingerprint as fp
    import hashlib
    monkeypatch.setattr(r,'ROOT',tmp_path)
    def save(name,value):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True)
        p.write_text(json.dumps(value),encoding='utf-8');return hashlib.sha256(p.read_bytes()).hexdigest()
    controls=controls or ['m1_test_m4_c1','m1_test_m4_c2']
    questions=questions or [dict(id='q'+str(i),question='合成问题'+str(i),product_names=['AX'],history=[]) for i in (1,2)]
    expected=expected or [dict(prompt='合成输入'+str(i),context=[],groups=[],prompt_reference_map=[],budget=dict(input_tokens=12,input_limit=28416)) for i in (1,2)]
    configs=[copy.deepcopy(c) for c in configs] if configs else [dict(strategy='m4-configured',target=dict(database='m1_test_m4_t'+str(i),collection='m1_test_m4_t'+str(i),owner_id='owner',kb_id='kb',bucket='existing',object_prefix='m4-test/'),parameters=dict(answer_budget=dict(context_window=32768,output_tokens=4096,reserve_tokens=256,max_chars=12000)),dataset_sha256='a'*64,split_manifest_sha256='b'*64,versions=dict(code='c'*64,model='d'*64,prompt='e'*64),phase='development',split='dev',execution_mode='real_query_runner',metric_schema_version=1) for i in (1,2)]
    members=[];parents=[]
    for i,(cfg,q,value,control) in enumerate(zip(configs,questions,expected,controls),1):
        if targets:cfg['target']['database']=targets[i-1]
        cfg['question_ids']=[q['id']]
        path='output/anchor'+str(i)+'.json'
        generated=value.get('route')!='clarify'
        members.append(dict(version=i,ordinal=1,question_id=q['id'],expected_generation=generated,fixed_slot='member'+str(i),source_input_path=path,source_input_file_sha256=save(path,dict(new_config=cfg,result=value)),dataset_sha256=cfg['dataset_sha256'],split_manifest_sha256=cfg['split_manifest_sha256'],**(dict(prompt_utf8_sha256=hashlib.sha256(value['prompt'].encode()).hexdigest()) if generated else dict(clarification_result_sha256=fp(value)))))
        parents.append(dict(version=i,control_database=control,owner_id=cfg['target']['owner_id'],kb_id=cfg['target']['kb_id'],source_config=cfg))
    master_path='output/master.json';execution_path='output/original.json'
    master_sha=save(master_path,dict(version_sources=parents));execution_sha=save(execution_path,dict(entries=[]))
    prior=dict(input_tokens=10,output_tokens=8,sources=dict(synthetic='a'*64));prior['sha256']=fp(prior)
    monkeypatch.setattr(r,'prior_receipt',lambda:prior)
    monkeypatch.setattr(r,'authorized_inputs',lambda auth,member:{k:questions[member['version']-1][k] for k in ('id','question','product_names','history')},raising=False)
    monkeypatch.setattr(r,'code_version',lambda:configs[0]['versions']['code'])
    ref=dict(commit='a'*40,path='docs/synthetic-remaining.json',sha256='f'*64)
    versions={k:__import__('importlib.metadata',fromlist=['version']).version(k) for k in ('openai','langchain-openai')}
    auth=dict(kind='coordinator_scoped_remaining_diagnostic_risk_authorization',admission_version=r.VERSION,fixed_batch_slot=r.BATCH,
        original_master_path=master_path,original_master_file_sha256=master_sha,original_execution_manifest_path=execution_path,original_execution_manifest_sha256=execution_sha,
        members=members,dispatch_order=[m['fixed_slot'] for m in members],
        risk=dict(gateway_capability_status='unknown',coordinator_accepts_unknown_paid_upper_bound_only_for_fixed_remaining_manifest=True),
        runtime=dict(n=1,model='synthetic',endpoint_sha256=fp('https://synthetic.invalid/v1'),client_versions=versions,limit_field='max_completion_tokens',requested_total_output_tokens=4096,temperature=.1,timeout_seconds=120),
        budget=dict(prior_diagnostic_input_tokens=10,prior_diagnostic_output_tokens=8,max_total_diagnostic_input_tokens=1477632,max_total_diagnostic_output_tokens=212992,max_new_product_streams=2,single_input_limit=28416,context_window=32768,output_tokens_requested=4096,reserve_tokens=256,max_chars=12000))
    monkeypatch.setattr(r,'AUTHORIZED_GIT',ref);monkeypatch.setattr(r,'evidence_bytes',lambda v:json.dumps(auth).encode())
    for cfg,m in zip(configs,members):
        cfg.update(experiment_id=m['fixed_slot'])
        cfg['parameters']['answer_budget'].update(output_token_field='max_completion_tokens',output_contract=dict(enabled=True,function_version=r.VERSION,n=1,status='unknown',semantics='unknown',model='synthetic',endpoint_sha256=auth['runtime']['endpoint_sha256'],client_versions=versions,limit_field='max_completion_tokens',ledger_id=r.BATCH,prior_input_tokens=10,prior_output_tokens=8,prior_source_sha256=prior['sha256'],max_total_input_tokens=1477632,max_total_output_tokens=212992,admission=dict(authorization=ref,manifest_sha256='0'*64,member_slot=m['fixed_slot'])))
    manifest=r.build_manifest([(cfg,q,control) for cfg,q,control in zip(configs,questions,controls)])
    for cfg in configs:cfg['parameters']['answer_budget']['output_contract']['admission']['manifest_sha256']=fp(manifest)
    r.prepare_manifest(manifest)
    policies=[parse_contract(c['parameters']['answer_budget']['output_contract']) for c in configs]
    return SimpleNamespace(module=r,configs=configs,questions=questions,expected=expected,controls=controls,policies=policies,manifest=manifest,auth=auth,fp=fp,save=save)


@pytest.fixture
def remaining_case(tmp_path,monkeypatch):return make_remaining_case(tmp_path,monkeypatch)


@pytest.mark.parametrize('drift',['member','control','target','input','ledger','prior','code','version','dataset','manifest'])
def test_member_identity_drift_refuses(remaining_case,drift):
    c=remaining_case;cfg=copy.deepcopy(c.configs[0]);q=copy.deepcopy(c.questions[0]);control=c.controls[0]
    p=cfg['parameters']['answer_budget']['output_contract']
    if drift=='member':p['admission']['member_slot']='unauthorized'
    if drift=='control':control=c.controls[1]
    if drift=='target':cfg['target']=c.configs[1]['target']
    if drift=='input':q['question']='改输入'
    if drift=='ledger':p['ledger_id']='new-ledger'
    if drift=='prior':p['prior_output_tokens']=0
    if drift=='code':cfg['versions']['code']='0'*64
    if drift=='version':p['admission']['member_slot']='member2'
    if drift=='dataset':cfg['dataset_sha256']='0'*64
    if drift=='manifest':p['admission']['manifest_sha256']='0'*64
    with pytest.raises((ValueError,FileNotFoundError)):c.module.validate_config(cfg,control,question=q)


def test_prompt_groups_refs_budget_remain_exact(remaining_case):
    c=remaining_case;v=c.expected[0];state=dict(prompt_used_docs=v['context'],prompt_reference_map=v['prompt_reference_map'],prompt_budget=v['budget'],evidence_groups=v['groups'])
    c.module.validate_prompt(c.policies[0],v['prompt'],state)
    for key in state:
        bad=copy.deepcopy(state);bad[key]=dict(tampered=True)
        with pytest.raises(ValueError):c.module.validate_prompt(c.policies[0],v['prompt'],bad)


def test_forged_initial_question_cannot_obtain_a_new_frozen_plan(remaining_case):
    c=remaining_case;q=copy.deepcopy(c.questions[0]);q['question']='初次冻结时偷偷改输入'
    with pytest.raises(ValueError):c.module.build_member(c.configs[0],q,c.controls[0])


@pytest.mark.parametrize('conflict',['n','typed_limit','kwargs','thinking','reasoning_effort','both_fields'])
def test_remaining_uses_the_installed_sdk_strict_wire_gate(remaining_case,conflict):
    import httpx
    from app.infrastructure.providers.diagnostic_usage import preserving_chat_class
    from app.infrastructure.providers.output_contract import strict_options
    c=remaining_case
    with httpx.Client(transport=httpx.MockTransport(lambda q:pytest.fail('仅构造，不联网')),follow_redirects=False) as http:
        client=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',n=1,stream_usage=True,max_retries=0,timeout=120,temperature=.1,http_client=http)
        assert strict_options(client,4096,'max_completion_tokens',c.policies[0])==dict(n=1,extra_body={'max_completion_tokens':4096})
        if conflict=='n':client.n=2
        if conflict=='typed_limit':client.max_tokens=4096
        if conflict=='kwargs':client.model_kwargs={'n':1}
        if conflict=='thinking':client.extra_body={'enable_thinking':False}
        if conflict=='reasoning_effort':client.reasoning_effort='low'
        if conflict=='both_fields':client.extra_body={'max_tokens':4096,'max_completion_tokens':4096}
        with pytest.raises(ValueError):strict_options(client,4096,'max_completion_tokens',c.policies[0])
