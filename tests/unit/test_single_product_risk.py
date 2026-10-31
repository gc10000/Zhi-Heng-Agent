"""单题风险准入的合成来源与跨进程槽；不读取私有产品答案。"""
import copy,json,hashlib
from pathlib import Path
from types import SimpleNamespace
import pytest


def make_risk_case(tmp_path,monkeypatch,*,source_config=None,question=None,expected=None,control_database='m1_test_m4_control'):
    from app.infrastructure.providers import product_risk as r
    from app.infrastructure.providers.output_contract import SingleProductRiskContract,payload
    from app.knowledge.repository import fingerprint as fp
    monkeypatch.setattr(r,'ROOT',tmp_path)
    def save(name,value):
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value),encoding='utf-8');return hashlib.sha256(p.read_bytes()).hexdigest()
    target=copy.deepcopy(source_config['target']) if source_config else dict(database='m1_test_m4_risk',collection='m1_test_m4_risk',owner_id='m4-test-owner',kb_id='m4-test-kb',bucket='existing',object_prefix='m4-test/risk/')
    question=question or dict(id='synthetic-q',question='合成问题',product_names=['AX'],history=[])
    prior_config=dict(strategy='m4-configured',target=target,dataset_sha256='a'*64,split_manifest_sha256='b'*64,
        parameters=dict(answer_budget=dict(context_window=32768,output_tokens=4096,reserve_tokens=256,max_chars=12000)),
        question_ids=['synthetic-q'],versions=dict(code='c'*64,model='d'*64,prompt='e'*64),phase='development',split='dev',
        execution_mode='real_query_runner',metric_schema_version=1)
    if source_config:prior_config=copy.deepcopy(source_config)
    prior_config['question_ids']=[question['id']]
    expected=expected or dict(prompt='合成输入',context=[],groups=[],excluded=[],prompt_reference_map=[],budget=dict(input_tokens=12,input_limit=28416))
    anchor=dict(new_config=prior_config,result=expected)
    source_sha=save('output/synthetic-anchor.json',anchor);binding_sha=save(r.BINDING_PATH,dict(synthetic=True))
    master=dict(version_sources=[dict(version=1,control_database=control_database,owner_id=target['owner_id'],
        kb_id=target['kb_id'],source_config=prior_config)])
    master_sha=save(r.MASTER_PATH,master);monkeypatch.setattr(r,'MASTER_SHA256',master_sha)
    save(r.SIX_USAGE_PATH,dict(jobs=[dict(input=5,output=6)]))
    save(r.PROBE_PATH,dict(slot='m6-output-cap-4096-probe-r1',classification='observed_limit_4096_at_fixed_profile',
        usage_receipt=dict(input_tokens=5,output_tokens=2)))
    ref=dict(commit='a'*40,path='docs/synthetic-risk.json',sha256='f'*64)
    auth=dict(kind='coordinator_scoped_product_diagnostic_risk_authorization',admission_version='diagnostic_single_product_risk_v1',
        status='authorized_conditionally_for_next_execution_package_not_yet_executed',fixed_authorization_slot=r.SLOT,
        question_id=question['id'],source_version='v1_only',source_dataset_sha256=prior_config['dataset_sha256'],source_split_manifest_sha256=prior_config['split_manifest_sha256'],
        source_input=dict(path='output/synthetic-anchor.json',file_sha256=source_sha,prompt_canonical_fingerprint=fp(expected['prompt']),
            prompt_utf8_sha256=hashlib.sha256(expected['prompt'].encode()).hexdigest(),subject_binding_file_sha256=binding_sha),
        risk=dict(gateway_capability_status='unknown',unknown_paid_upper_bound_accepted_only_for_this_one_product_stream=True),
        runtime=dict(endpoint_sha256=fp('https://synthetic.invalid/v1'),model='synthetic',client_versions={},n=1,temperature=0.1,
            limit_field='max_completion_tokens',requested_total_output_tokens=4096,sdk_max_retries=0,timeout_seconds=120),
        budget=dict(max_new_product_streams=1,saved_conservative_input_reservation=expected['budget']['input_tokens'],single_input_limit=28416,
            prior_diagnostic_input_tokens=10,prior_diagnostic_output_tokens=8,max_total_diagnostic_input_tokens=1477632,
            max_total_diagnostic_output_tokens=212992,context_window=32768,output_tokens_requested=4096,reserve_tokens=256,max_chars=12000))
    monkeypatch.setattr(r,'AUTHORIZED_GIT',ref)
    monkeypatch.setattr(r,'evidence_bytes',lambda v:json.dumps(auth).encode())
    monkeypatch.setattr(r,'code_version',lambda:prior_config['versions']['code'])
    policy=dict(enabled=True,function_version='diagnostic_single_product_risk_v1',status='unknown',semantics='unknown',n=1,
        endpoint_sha256=auth['runtime']['endpoint_sha256'],model='synthetic',client_versions={k:__import__('importlib.metadata',fromlist=['version']).version(k) for k in ('openai','langchain-openai')},
        limit_field='max_completion_tokens',ledger_id='synthetic-ledger',prior_input_tokens=10,prior_output_tokens=8,
        prior_source_sha256=r.prior_receipt()['sha256'],max_total_output_tokens=212992,max_total_input_tokens=1477632,
        admission=dict(authorization=ref,manifest_sha256='0'*64))
    auth['runtime']['client_versions']=policy['client_versions']
    cfg=copy.deepcopy(prior_config);cfg['parameters']['answer_budget'].update(output_token_field='max_completion_tokens',output_contract=policy)
    manifest=r.build_manifest(cfg,question,control_database=control_database)
    policy['admission']['manifest_sha256']=fp(manifest)
    r.prepare_manifest(manifest)
    return SimpleNamespace(module=r,policy=policy,config=cfg,question=question,expected=expected,manifest=manifest,auth=auth,
        contract=SingleProductRiskContract.model_validate(policy),target=target,save=save,fp=fp)


@pytest.fixture
def risk_case(tmp_path,monkeypatch):return make_risk_case(tmp_path,monkeypatch)


def test_regular_unknown_contract_keeps_refusing():
    from app.infrastructure.providers.output_contract import require_capability
    from app.api.errors import APIError
    with pytest.raises(APIError):require_capability(dict(enabled=True,endpoint_sha256='a'*64,model='synthetic',
        client_versions={'openai':'synthetic'},ledger_id='plain',max_total_output_tokens=8192))


def test_explicit_risk_contract_is_registered_in_existing_boundary():
    from app.infrastructure.providers import output_contract
    assert hasattr(output_contract,'SingleProductRiskContract'),'正式输出边界尚无显式单题准入身份'


def test_risk_identity_is_explicit_and_does_not_claim_capability(risk_case):
    from app.infrastructure.providers.output_contract import require_capability,identity
    p=require_capability(risk_case.policy)
    assert p.status=='unknown' and p.function_version=='diagnostic_single_product_risk_v1'
    assert identity(p)['output_contract']['admission']['authorization']==risk_case.policy['admission']['authorization']


def test_explicitly_disabled_risk_uses_the_ordinary_off_path(risk_case):
    from app.infrastructure.providers.output_contract import is_product_risk,payload
    off=risk_case.policy|dict(enabled=False)
    assert payload(off) is None
    assert not is_product_risk(off)


@pytest.mark.parametrize('field',['question','question_ids','target','control','code','prompt','grant','prior',
    'ledger','dataset','manifest','version','endpoint','field','model','budget'])
def test_risk_drift_refuses_before_claim(risk_case,field):
    c=risk_case;cfg=copy.deepcopy(c.config);q=copy.deepcopy(c.question);db='m1_test_m4_control'
    if field=='question':q['question']='变化'
    if field=='question_ids':cfg['question_ids']=['another']
    if field=='target':cfg['target']['database']='m1_test_m4_other'
    if field=='control':db='m1_test_m4_other'
    if field=='code':cfg['versions']['code']='0'*64
    if field=='prompt':c.expected['prompt']='变化';c.save('output/synthetic-anchor.json',dict(new_config=c.config,result=c.expected))
    if field=='grant':cfg['parameters']['answer_budget']['output_contract']['admission']['authorization']['sha256']='0'*64
    if field=='prior':cfg['parameters']['answer_budget']['output_contract']['prior_output_tokens']=0
    if field=='ledger':cfg['parameters']['answer_budget']['output_contract']['ledger_id']='another-ledger'
    if field=='dataset':cfg['dataset_sha256']='0'*64
    if field=='manifest':cfg['split_manifest_sha256']='0'*64
    if field=='version':cfg['parameters']['answer_budget']['output_contract']['function_version']='unknown'
    if field=='endpoint':cfg['parameters']['answer_budget']['output_contract']['endpoint_sha256']='0'*64
    if field=='field':cfg['parameters']['answer_budget']['output_contract']['limit_field']='max_tokens'
    if field=='model':cfg['parameters']['answer_budget']['output_contract']['model']='another-model'
    if field=='budget':cfg['parameters']['answer_budget']['output_contract']['max_total_output_tokens']+=1
    with pytest.raises(ValueError):
        c.module.validate_config(cfg,db,question=q)
    assert not (c.module.slot_dir()/'started.json').exists()


def test_fixed_slot_stops_nonce_and_directory_regrant(risk_case):
    c=risk_case;context=dict(config=c.config,control_database='m1_test_m4_control',question=c.question,
        execution=dict(experiment_id='one',attempt=1,config_sha256=c.fp(c.config)))
    c.module.start(c.contract,db_name=c.target['database'],run_id='r',run_identity='i',context=context)
    assert (c.module.slot_dir()/'started.json').is_file()
    for changed in ('same','run','ledger','control','target'):
        other=copy.deepcopy(context)
        if changed=='control':other['control_database']='m1_test_m4_other'
        if changed=='target':other['config']['target']['database']='m1_test_m4_other'
        with pytest.raises(Exception):c.module.start(c.contract,db_name=c.target['database'],run_id='other' if changed=='run' else 'r',run_identity='i',context=other)


def test_precise_prompt_and_source_map_are_checked(risk_case):
    c=risk_case;state=dict(prompt_used_docs=[],prompt_reference_map=[],prompt_budget=c.expected['budget'])
    c.module.validate_prompt(c.contract,c.expected['prompt'],state)
    for key in ('prompt_used_docs','prompt_reference_map','prompt_budget'):
        bad=copy.deepcopy(state);bad[key]={'changed':True}
        with pytest.raises(Exception):c.module.validate_prompt(c.contract,c.expected['prompt'],bad)


def test_failed_or_settled_slot_never_dispatches_again(risk_case):
    c=risk_case;context=dict(config=c.config,control_database='m1_test_m4_control',question=c.question,
        execution=dict(experiment_id='one',attempt=1,config_sha256=c.fp(c.config)))
    c.module.start(c.contract,db_name=c.target['database'],run_id='r',run_identity='i',context=context)
    receipt=dict(run_id='r',run_identity='i',completed=True,input_tokens=1,output_tokens=2)
    c.module.settle(c.contract,receipt);c.module.settle(c.contract,receipt)
    with pytest.raises(Exception):c.module.settle(c.contract,receipt|dict(output_tokens=3))
    with pytest.raises(Exception):c.module.start(c.contract,db_name=c.target['database'],run_id='r',run_identity='i',context=context)


def test_concurrent_claims_have_one_os_exclusive_winner(risk_case):
    from concurrent.futures import ThreadPoolExecutor
    c=risk_case;context=dict(config=c.config,control_database='m1_test_m4_control',question=c.question,
        execution=dict(experiment_id='one',attempt=1,config_sha256=c.fp(c.config)))
    def claim(i):
        try:c.module.start(c.contract,db_name=c.target['database'],run_id='r'+str(i),run_identity='i',context=context);return True
        except FileExistsError:return False
    with ThreadPoolExecutor(max_workers=4) as pool:assert sum(pool.map(claim,range(4)))==1


def test_real_sdk_profile_rejects_unbound_runtime(risk_case):
    import httpx
    from app.infrastructure.providers.diagnostic_usage import preserving_chat_class
    from app.infrastructure.providers.output_contract import strict_options
    c=risk_case;sent=[]
    with httpx.Client(transport=httpx.MockTransport(lambda q:sent.append(q)),follow_redirects=False) as transport:
        client=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',
            n=1,stream_usage=True,max_retries=0,timeout=120,temperature=0.1,http_client=transport)
        assert strict_options(client,4096,'max_completion_tokens',c.policy)==dict(n=1,extra_body={'max_completion_tokens':4096})
        client.temperature=0.5
        with pytest.raises(ValueError):strict_options(client,4096,'max_completion_tokens',c.policy)
        assert not sent


def test_generation_options_consume_the_explicit_contract(risk_case):
    from app.infrastructure.providers.clients import output_limit_options
    from app.infrastructure.providers.diagnostic_usage import preserving_chat_class
    import httpx
    with httpx.Client(transport=httpx.MockTransport(lambda q:pytest.fail('不得联网')),follow_redirects=False) as transport:
        client=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',
            n=1,stream_usage=True,max_retries=0,timeout=120,temperature=0.1,http_client=transport)
        assert output_limit_options(client,4096,'max_completion_tokens',contract=risk_case.policy)==dict(
            n=1,extra_body={'max_completion_tokens':4096})


def test_no_authorization_and_missing_or_changed_plan_never_claim(risk_case):
    from app.infrastructure.providers.output_contract import require_capability
    c=risk_case
    bad=copy.deepcopy(c.policy);bad.pop('admission')
    with pytest.raises(ValueError):require_capability(bad)
    path=c.module.slot_dir()/'planned.json'
    path.unlink()  # 仅随机pytest合成槽，模拟尚未形成计划。
    with pytest.raises(FileNotFoundError):require_capability(c.policy)
    c.save(path,dict(tampered=True))
    with pytest.raises(ValueError):require_capability(c.policy)
    assert not (c.module.slot_dir()/'started.json').exists()


def test_pre_call_code_refreeze_is_append_only_and_keeps_one_slot(risk_case,monkeypatch):
    c=risk_case;path=c.module.slot_dir()/'planned.json';original=path.read_bytes()
    cfg=copy.deepcopy(c.config);cfg['versions']['code']='f'*64
    monkeypatch.setattr(c.module,'code_version',lambda:'f'*64)
    manifest=c.module.build_manifest(cfg,c.question,control_database='m1_test_m4_control')
    cfg['parameters']['answer_budget']['output_contract']['admission']['manifest_sha256']=c.fp(manifest)
    c.module.prepare_manifest(manifest)
    assert path.read_bytes()==original
    c.module.validate_config(cfg,'m1_test_m4_control',question=c.question)
    bad=copy.deepcopy(manifest);bad['config_subject']['parameters']['answer_budget']['output_contract']['ledger_id']='another'
    with pytest.raises(ValueError):c.module.prepare_manifest(bad)
    context=dict(config=cfg,control_database='m1_test_m4_control',question=c.question,
        execution=dict(experiment_id='one',attempt=1,config_sha256=c.fp(cfg)))
    from app.infrastructure.providers.output_contract import parse_contract
    p=parse_contract(cfg['parameters']['answer_budget']['output_contract'])
    c.module.start(p,db_name=c.target['database'],run_id='r',run_identity='i',context=context)
    manifest['config_subject']['versions']['code']='d'*64
    with pytest.raises(ValueError):c.module.prepare_manifest(manifest)
    with pytest.raises(Exception):c.module.start(p,db_name=c.target['database'],run_id='new',run_identity='i',context=context)


def test_os_exclusive_is_cross_process_and_partial_file_is_closed(tmp_path):
    import subprocess,sys
    path=tmp_path/'claim.json'
    code="from pathlib import Path; from app.infrastructure.providers.product_risk import exclusive; import sys; exclusive(Path(sys.argv[1]),{'synthetic':True})"
    processes=[subprocess.Popen([sys.executable,'-c',code,str(path)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(3)]
    assert sorted(p.communicate() and p.returncode for p in processes)==[0,1,1]
    assert json.loads(path.read_text('utf-8'))=={'synthetic':True}
    from app.infrastructure.providers.product_risk import exclusive
    partial=tmp_path/'partial.json';partial.write_text('{',encoding='utf-8')
    with pytest.raises(FileExistsError):exclusive(partial,{'overwrite':True})
    assert partial.read_text('utf-8')=='{'
