"""新连接比较单题合同不得借用旧槽或把预检当授权。"""
from copy import deepcopy
import pytest

from app.infrastructure.providers.output_contract import parse_contract, is_product_risk, risk_handler, require_capability
from app.api.errors import APIError
from app.evaluation.service import EvaluationService
from tests.unit.test_comparison_experiment_admission import Repository, Catalog

VERSION='diagnostic_connection_comparison_048_v1'
SLOT='m6-connection-comparison-048-r1-support-v1-048'


def contract(enabled=False):
    value=dict(enabled=enabled,function_version=VERSION,thinking=False,status='unknown',semantics='unknown',
        n=1,endpoint_sha256='a'*64,model='qwen3.8-flash',
        client_versions={'openai':'2.28.0','langchain-openai':'1.1.11'},limit_field='max_completion_tokens',
        per_request_total_output_tokens=4096,ledger_id='m6-connection-comparison-048-r1',
        prior_input_tokens=56239,prior_output_tokens=30516,prior_source_sha256='b'*64,
        max_total_input_tokens=84655,max_total_output_tokens=34612,admission=None)
    if enabled:
        value['admission']=dict(authorization=dict(commit='c'*40,
            path='docs/development/reviews/M6-connection-comparison-048-authorization-r1.json',sha256='d'*64),
            member_slot=SLOT,manifest_sha256='e'*64)
    return value


def test_disabled_contract_is_explicit_without_fabricated_authorization():
    from app.answering.service import AnswerBudget
    from app.runs.models import InternalRunInput
    policy=parse_contract(contract())
    assert policy.admission is None and not is_product_risk(policy)
    budget=AnswerBudget(output_contract=contract())
    request=InternalRunInput(kb_id='kb',question='比较设备',client_request_id='new',output_contract=contract())
    assert request.output_contract==budget.output_contract==policy
    assert InternalRunInput.model_validate_json(request.model_dump_json()).output_contract==policy


@pytest.mark.parametrize('change',[
    {'n':2},{'thinking':True},{'model':'other'},{'limit_field':'max_tokens'},
    {'prior_input_tokens':0},{'prior_output_tokens':0},{'max_total_input_tokens':84656},
    {'max_total_output_tokens':34613},{'ledger_id':'old'},{'status':'verified'},
    {'per_request_total_output_tokens':4097}, {'enabled':True,'admission':None},
])
def test_mutated_or_unbounded_profile_is_rejected(change):
    with pytest.raises(ValueError): parse_contract(contract()|change)


def test_enabled_unregistered_profile_refuses_capability_client_and_manifest_before_io(tmp_path,monkeypatch):
    from app.infrastructure.providers import connection_comparison_048_risk as risk
    policy=parse_contract(contract(True))
    assert is_product_risk(policy) and risk_handler(policy) is risk
    monkeypatch.setattr(risk,'ROOT',tmp_path)
    for action in (lambda:require_capability(policy),lambda:risk.open_client(policy),
                   lambda:risk.prepare_manifest({'authorization':None})):
        with pytest.raises(ValueError,match='授权'):action()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize('mode',['connection_comparison_v1','comparison_answer_v2'])
@pytest.mark.parametrize('enabled',[False,True])
def test_service_never_reserves_for_unapproved_new_contract(mode,enabled):
    catalog=Catalog(contract(enabled));resolve=catalog.resolve
    def current(*args,**kwargs):
        r=resolve(*args,**kwargs)
        r['config']['parameters']['evidence_attribution']['comparison_answer']['function_version']=mode
        return r
    catalog.resolve=current;repo=Repository()
    with pytest.raises(APIError) as exc:
        EvaluationService(repo,catalog).create_experiment(object(),dict(kb_id='kb',eval_set_id='set',
            eval_set_version='v1',config_id='new',config_version='r1',client_request_id='one'))
    assert exc.value.code=='comparison_admission_required' and not repo.created


def test_service_new_mode_reaches_own_validator_before_repository(monkeypatch):
    from app.infrastructure.providers import connection_comparison_048_risk as risk
    repo=Repository();catalog=Catalog(contract(True));resolve=catalog.resolve
    def current(*args,**kwargs):
        r=resolve(*args,**kwargs)
        r['config']['parameters']['evidence_attribution']['comparison_answer']['function_version']='connection_comparison_v1'
        return r
    catalog.resolve=current
    def validate(config,database):
        raise APIError(409,'synthetic_validator_reached','隔离检查到达专属验证器。')
    monkeypatch.setattr(risk,'validate_config',validate)
    with pytest.raises(APIError) as exc:
        EvaluationService(repo,catalog).create_experiment(object(),dict(kb_id='kb',eval_set_id='set',
            eval_set_version='v1',config_id='new',config_version='r1',client_request_id='one'))
    assert exc.value.code=='synthetic_validator_reached' and not repo.created


def authorized_case(tmp_path,monkeypatch):
    """只替换Git证据读取，实际来源/配置/prompt/清单消费者全部运行。"""
    import json,hashlib
    from app.infrastructure.providers import connection_comparison_048_risk as risk
    from app.knowledge.repository import fingerprint
    from tests.unit.test_connection_comparison_wiring import setup_connection
    runner,pool,plan=setup_connection()
    from app.answering.service import AnswerBudget
    runner.answer_budget=AnswerBudget(context_window=32768,output_tokens=4096,reserve_tokens=256,max_chars=12000)
    runner.retrieval_policy={'context_limit':10}
    docs,groups,manifest=runner.assemble_connection_context([pool[0],pool[2]],pool,['p','q'])
    state,prompt=runner.evidence_prompt(plan.original_query,docs,groups,plan,item_names=['Atlas A17','Beacon B24'],
        history=[],session_id='synthetic-auth',comparison_context=manifest)
    monkeypatch.setattr(risk,'ROOT',tmp_path)
    monkeypatch.setattr(risk,'code_version',lambda:'new-code')
    prior=dict(input_tokens=56239,output_tokens=30516,sources={},sha256='b'*64)
    monkeypatch.setattr(risk,'prior_receipt',lambda:prior)
    monkeypatch.setattr(risk,'technical_review',lambda:{'synthetic':True})
    question=dict(id=risk.QUESTION_ID,question=plan.original_query,product_names=['Atlas A17','Beacon B24'],history=[],split='dev')
    rows=[question]+[dict(question,id='q'+str(i),split='dev' if i<85 else 'heldout') for i in range(1,150)]
    dataset=tmp_path/'dataset.jsonl';dataset.write_text('\n'.join(json.dumps(q) for q in rows),encoding='utf-8')
    split=tmp_path/'split.json';split.write_text('{}',encoding='utf-8')
    original=dict(target=dict(database='m1_test_m4_target',owner_id='owner',kb_id='kb'),
        versions=dict(code='old-code',prompt='old-prompt',model='saved-model'),
        parameters=dict(retrieval=dict(context_limit=10),answer_budget=dict(context_window=32768,output_tokens=4096,reserve_tokens=256,max_chars=12000,
            output_token_field='max_completion_tokens',output_contract=contract()),evidence_attribution=runner.evidence_attribution),
        dataset_sha256=risk.sha(dataset),split_manifest_sha256=risk.sha(split),phase='development',split='dev')
    monkeypatch.setattr(risk,'source_config',lambda:deepcopy(original))
    cfg=risk.candidate_config()
    result=dict(prompt=prompt,context=docs,prompt_reference_map=state['prompt_reference_map'],groups=state['evidence_groups'],
        budget=state['prompt_budget'],comparison_context_assembly=manifest)
    from app.evaluation.connection_048_inputs import assemble_input
    anchor=assemble_input(cfg,dict(question={k:question[k] for k in ('id','question','product_names','history')},
        query_plan=plan.model_dump(mode='json')|dict(comparison_target=plan.comparison_target,
            comparison_target_reason=plan.comparison_target_reason),
        product_ids=list(plan.product_ids),seeds=[pool[0],pool[2]],groups=[],frozen_scalar_payloads=pool))
    result=anchor['result']
    anchor_path=tmp_path/'anchor.json'
    def save_anchor():anchor_path.write_text(json.dumps(anchor),encoding='utf-8')
    save_anchor()
    member=dict(fixed_slot=SLOT,question_id=risk.QUESTION_ID,expected_generation=True,
        dataset_sha256=risk.sha(dataset),split_manifest_sha256=risk.sha(split),
        prompt_utf8_sha256=hashlib.sha256(prompt.encode()).hexdigest(),source_result_sha256=fingerprint(result))
    policy=parse_contract(contract(True));ref=policy.admission.authorization.model_dump(mode='json')
    monkeypatch.setattr(risk,'AUTHORIZED_GIT',ref)
    auth=dict(kind='coordinator_scoped_connection_comparison_048_authorization',status='authorized_for_one_stream_only',
        admission_version=risk.VERSION,fixed_batch_slot=risk.BATCH,dispatch_order=[SLOT],technical_review=deepcopy(risk.TECHNICAL_REVIEW),
        prior_usage=prior,source_config=deepcopy(risk.SOURCE_CONFIG),previous_batch=risk.consumed.BATCH,
        user_authorization=dict(question_id=risk.QUESTION_ID,max_provider_streams=1,accept_unknown_cost_upper_bound=True,
            stop_on_first_failure=True,retry_or_reuse_old_slots=False),members=[member],
        candidate_anchor=dict(path='anchor.json',sha256=risk.sha(anchor_path)),evaluation_control_database='synthetic-control',
        dataset=dict(path='dataset.jsonl',sha256=risk.sha(dataset)),split_manifest=dict(path='split.json',sha256=risk.sha(split)),
        runtime=dict(n=1,model=policy.model,endpoint_sha256=policy.endpoint_sha256,client_versions=policy.client_versions,
            limit_field='max_completion_tokens',requested_total_output_tokens=4096,thinking=False,temperature=0.1,
            timeout_seconds=120,sdk_max_retries=0,stream=True),budget=dict(context_window=32768,output_tokens_requested=4096,
            reserve_tokens=256,max_chars=12000,single_input_limit=28416,max_new_product_streams=1,max_attempts_per_member=1))
    monkeypatch.setattr(risk,'evidence_bytes',lambda _:json.dumps(auth).encode())
    cfg['parameters']['answer_budget']['output_contract']=policy.model_dump(mode='json')
    return risk,auth,anchor,cfg,question,state,prompt,save_anchor


def test_synthetic_authorization_freezes_config_question_and_actual_prompt(tmp_path,monkeypatch):
    from app.knowledge.repository import fingerprint
    risk,auth,anchor,cfg,question,state,prompt,_=authorized_case(tmp_path,monkeypatch)
    manifest=risk.build_manifest([(cfg,question,'synthetic-control')])
    cfg['parameters']['answer_budget']['output_contract']['admission']['manifest_sha256']=fingerprint(manifest)
    risk.prepare_manifest(manifest)
    risk.validate_config(cfg,'synthetic-control',question=question)
    risk.validate_prompt(parse_contract(cfg['parameters']['answer_budget']['output_contract']),prompt,
        state|dict(prompt_budget=anchor['result']['budget']))
    changed=deepcopy(question);changed['history']=[{'role':'user','content':'改写历史'}]
    with pytest.raises(ValueError):risk.validate_config(cfg,'synthetic-control',question=changed)
    with pytest.raises(ValueError):risk.validate_config(cfg,'different-control',question=question)


@pytest.mark.parametrize('fault',['cost','slot','source_config','prompt','anchor_file','scope','mode'])
def test_synthetic_signed_drift_cannot_become_valid_admission(tmp_path,monkeypatch,fault):
    from app.knowledge.repository import fingerprint
    import hashlib
    risk,auth,anchor,cfg,question,state,prompt,save=authorized_case(tmp_path,monkeypatch)
    if fault=='cost':auth['user_authorization']['accept_unknown_cost_upper_bound']=False
    if fault=='slot':auth['members'][0]['fixed_slot']='old-slot'
    if fault=='source_config':auth['source_config']['sha256']='0'*64
    if fault=='prompt':anchor['result']['prompt']+='改写'
    if fault=='scope':anchor['result']['comparison_context_assembly']['frozen_pool_sha256']='0'*64
    if fault=='mode':anchor['new_config']['parameters']['evidence_attribution']['comparison_answer']['function_version']='comparison_answer_v2'
    if fault in {'anchor_file','prompt','scope','mode'}:
        if fault=='anchor_file':anchor['tampered']=True
        save()
        if fault!='anchor_file':
            auth['candidate_anchor']['sha256']=risk.sha(tmp_path/'anchor.json')
            auth['members'][0]['source_result_sha256']=fingerprint(anchor['result'])
    # prompt重新签result但未变独立的prompt字节hash；其余分别在自己的来源边界拒绝。
    with pytest.raises(ValueError):risk.sources(parse_contract(cfg['parameters']['answer_budget']['output_contract']))


@pytest.mark.parametrize('fault',[None,'state','pending','settled','halt','review_missing','review_accepted','review_evidence'])
def test_previous_consumed_account_is_checked_read_only(tmp_path,monkeypatch,fault):
    import json
    from app.infrastructure.providers import connection_comparison_048_risk as risk
    from app.knowledge.repository import fingerprint
    root=tmp_path/'output/m6-authorized-products'/risk.consumed.BATCH
    member_dir=root/'members'/risk.consumed.SLOT;member_dir.mkdir(parents=True)
    receipt=dict(run_id='old-run',completed=True)
    halt=dict(no_more_provider_calls=True,source_review=dict(accepted=False))
    values=dict(planned=dict(version=risk.consumed.VERSION,dispatch_order=[risk.consumed.SLOT],
        shared_control_database='old-control'),halt=halt,settled=dict(receipt=receipt))
    refs={}
    for key,value in values.items():
        path=(member_dir if key=='settled' else root)/(key+'.json')
        path.write_text(json.dumps(value),encoding='utf-8')
        refs[key]=dict(path=path.relative_to(tmp_path).as_posix(),sha256=risk.sha(path))
    account=dict(state='blocked',pending=None,unknown_windows=[],settled={risk.consumed.SLOT:receipt},halt=halt,
        reviews={risk.consumed.SLOT:dict(accepted=False,evidence=deepcopy(halt['source_review']))})
    if fault=='state':account['state']='open'
    if fault=='pending':account['pending']={'run_id':'unknown'}
    if fault=='settled':account['settled']={}
    if fault=='halt':account['halt']={}
    if fault=='review_missing':account['reviews']={}
    if fault=='review_accepted':account['reviews'][risk.consumed.SLOT]['accepted']=True
    if fault=='review_evidence':account['reviews'][risk.consumed.SLOT]['evidence']={}
    reads=[]
    class ReadOnlyCollection:
        def find_one(self,query):
            reads.append(query);return account
    class ReadOnlyDatabase:
        def __getitem__(self,name):
            assert name==risk.consumed.ACCOUNT_COLLECTION
            return ReadOnlyCollection()
    class ReadOnlyClient:
        def __getitem__(self,name):
            assert name=='old-control'
            return ReadOnlyDatabase()
    monkeypatch.setattr(risk,'ROOT',tmp_path)
    monkeypatch.setattr(risk,'sources',lambda _:(dict(previous_receipts=refs),None,None,None))
    if fault:
        with pytest.raises(ValueError):risk.validate_previous_account(parse_contract(contract(True)),ReadOnlyClient())
    else:
        risk.validate_previous_account(parse_contract(contract(True)),ReadOnlyClient())
    assert reads==[{'_id':fingerprint([risk.consumed.VERSION,risk.consumed.BATCH])}]


@pytest.mark.parametrize('fault',['missing','partial','unfrozen','prompt'])
def test_authorization_must_consume_recomputable_complete_input(tmp_path,monkeypatch,fault):
    from app.knowledge.repository import fingerprint
    import hashlib
    risk,auth,anchor,cfg,question,state,prompt,save=authorized_case(tmp_path,monkeypatch)
    if fault=='missing':anchor.pop('production_inputs')
    if fault=='partial':anchor['full_scope_scalar_payloads_replayed']=False
    if fault=='unfrozen':anchor['exact_production_prompt_frozen']=False
    if fault=='prompt':anchor['result']['prompt']+='coordinated-change'
    anchor['prompt_utf8_sha256']=hashlib.sha256(anchor['result']['prompt'].encode()).hexdigest()
    anchor['result_sha256']=fingerprint(anchor['result'])
    save();auth['candidate_anchor']['sha256']=risk.sha(tmp_path/'anchor.json')
    auth['members'][0].update(prompt_utf8_sha256=anchor['prompt_utf8_sha256'],source_result_sha256=anchor['result_sha256'])
    with pytest.raises(ValueError):risk.sources(parse_contract(cfg['parameters']['answer_budget']['output_contract']))


@pytest.mark.parametrize('fault',['database','version','batch','order','prior','duplicate'])
@pytest.mark.parametrize('restore',[False,True])
def test_manifest_top_level_cannot_redirect_or_regrant_account(tmp_path,monkeypatch,fault,restore):
    """即使调用方重新计算清单hash，也不能把单成员挪到另一共享账本。"""
    from app.knowledge.repository import fingerprint
    import json
    risk,auth,anchor,cfg,question,*_=authorized_case(tmp_path,monkeypatch)
    manifest=deepcopy(risk.build_manifest([(cfg,question,'synthetic-control')]))
    if fault=='database':manifest['shared_control_database']='other-control'
    if fault=='version':manifest['version']='old-version'
    if fault=='batch':manifest['batch_slot']='another-batch'
    if fault=='order':manifest['dispatch_order']=[]
    if fault=='prior':manifest['prior_receipt']['input_tokens']=0
    if fault=='duplicate':manifest['entries']*=2
    value=cfg['parameters']['answer_budget']['output_contract']
    value['admission']['manifest_sha256']=fingerprint(manifest)
    policy=parse_contract(value)
    if restore:
        # 模拟协调改写磁盘及请求hash；require仍须从Git授权重算身份。
        directory=risk.slot_dir(policy);directory.mkdir(parents=True)
        (risk.batch_dir()/'planned.json').write_text(json.dumps(manifest),encoding='utf-8')
        (directory/'planned.json').write_text(json.dumps(dict(manifest_sha256=fingerprint(manifest),
            entry=manifest['entries'][0])),encoding='utf-8')
        with pytest.raises(ValueError):risk.require(policy)
    else:
        with pytest.raises(ValueError):risk.prepare_manifest(manifest)
        assert not risk.batch_dir().exists()
