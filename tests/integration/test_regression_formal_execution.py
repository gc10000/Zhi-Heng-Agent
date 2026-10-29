"""正式job与Run接线，供应商及双轮均为明确合成夹具，隔离库不删除。"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import json
from copy import deepcopy
import pytest

from app.api.errors import APIError
from app.evaluation.feedback_regression import RegressionService
from app.evaluation.feedback_triage import review_feedback, TriageInput
from app.evaluation.jobs import execute_job
from app.evaluation.reviews import ReviewService, ReviewInput, CalibrationInput
from app.evaluation.validate_dataset import fingerprint
from tests.integration.test_evaluation_split_ledger import formal_case
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_reviews import payload

pytestmark = pytest.mark.integration


def setup_lineage(ctx,tmp_path,monkeypatch,separate=True):
    cfg,resources,prompts,question,repo,service,user,data,catalog = formal_case(
        ctx,tmp_path,monkeypatch,separate=separate,reviewed=True)
    # 先经正式job创建一个合成反馈来源；不伪造真实业务反馈或历史Run。
    source = service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'out',source['experiment_id'])
    rid = resources['db'].evaluation_execution_links.find_one({'experiment_id':source['experiment_id']})['run_id']
    run = resources['db'].runs.find_one({'run_id':rid})
    # 反馈控制账本可以独立于Run目标；来源Run用显式source_database读取，绝不复制Run。
    fid = 'synthetic-feedback'
    feedback = dict(feedback_id=fid,run_id=rid,owner_id=user.user_id,kb_id=data['kb_id'],state='pending_review',
        version=0,source_database=resources['db'].name,citations=run['citations'])
    repo.db.support_feedback.insert_one(feedback)
    request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(resources=dict(
        db=repo.db,knowledge=resources['knowledge']))))
    # 分库来源审核通过正式入口完成，来源数据库由服务端夹具固定。
    reviewed = review_feedback(request,user,fid,TriageInput(expected_version=0,decision='confirm',
        destination='regression',rationale='明确标识合成反馈审核',proposed_question=question['question'],
        proposed_expectation='24 V',client_request_id='synthetic-triage'))
    ledger = RegressionService(repo,catalog)
    bound = ledger.bind(user,fid,dict(dataset_id='set',dataset_version='r1',config_id='control',
                                   config_version='r1',question_id='q1'))
    return cfg,resources,prompts,question,repo,service,user,data,catalog,ledger,bound


def synthetic_rounds(reviews,user,eid):
    _,subjects = reviews._subjects(user,eid)
    for qid,(sha,_) in subjects.items():
        for n in (1,2):
            data = payload(sha,key=f'{eid}-{qid}-{n}',round=n) | dict(question_id=qid)
            reviews.submit(user,eid,ReviewInput(**data))


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('derived',[False,True])
def test_full_formal_source_baseline_calibration_candidate_proof(evaluation_context,tmp_path,monkeypatch,separate,derived):
    cfg,res,prompts,q,repo,ev,user,data,catalog,ledger,bound = setup_lineage(evaluation_context,tmp_path,monkeypatch,separate)
    if derived:
        from tests.unit.test_evaluation_dataset import independent_annotation
        from app.identity.models import Principal
        # 新反馈经正式triage，变化标签独立审核；未覆盖第一条已绑定反馈。
        old=repo.db.support_feedback.find_one({'feedback_id':'synthetic-feedback'})
        fresh={k:v for k,v in old.items() if k not in {'_id','draft','review_identity'}}
        fresh.update(feedback_id='changed-feedback',state='pending_review',version=0)
        repo.db.support_feedback.insert_one(fresh)
        request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(resources=dict(db=repo.db,knowledge=res['knowledge']))))
        review_feedback(request,user,'changed-feedback',TriageInput(expected_version=0,decision='confirm',
            destination='regression',rationale='合成变化标签反馈',proposed_question=q['question'],
            proposed_expectation='合成修订行为',client_request_id='changed-triage'))
        changed=deepcopy(bound['question'])
        changed['expected']['key_points']=['合成修订验收点，不得进入prompt']
        changed['annotation']=dict(method='source_checked_assistant_draft',status='draft')
        draft=ledger.candidate(user,'changed-feedback',changed)
        reviewer=Principal(user_id='control_assistant',username='合成独立审核',role='maintainer',kb_ids=user.kb_ids)
        monkeypatch.setattr('app.evaluation.feedback_regression.verify_review_artifact',lambda _:None)
        audited=ledger.review(reviewer,draft['id'],independent_annotation(changed))
        bound=ledger.bind(user,'changed-feedback',bound['binding_request'] | {'annotation_id':audited['id']})
        ev.register_set(user,dict(kb_id=data['kb_id'],eval_set_id=bound['dataset_id'],version=bound['dataset_version']))
        data=data | dict(eval_set_version=bound['dataset_version'],config_id=bound['config_id'],config_version=bound['config_version'])
    ref = ledger.reference(bound)
    baseline = ev.create_experiment(user,data | dict(client_request_id='bound-baseline',regression_source=ref))
    execute_job(repo,catalog,tmp_path/'out',baseline['experiment_id'])
    assert repo.get_experiment(user,baseline['experiment_id'])['state']=='completed'
    reviews = ReviewService(repo)
    synthetic_rounds(reviews,user,baseline['experiment_id'])
    calibration = reviews.calibrate(user,baseline['experiment_id'],CalibrationInput(
        client_request_id='synthetic-calibration',rationale='合成双轮夹具，仅证明协议'))
    candidate = ev.create_experiment(user,data | dict(client_request_id='bound-candidate',regression_source=ref,
        baseline_experiment_id=baseline['experiment_id'],regression_calibration_id=calibration['calibration_id']))
    execute_job(repo,catalog,tmp_path/'out',candidate['experiment_id'])
    with pytest.raises(APIError): ledger.proof(user,ref,candidate['experiment_id'],calibration['calibration_id'])
    synthetic_rounds(reviews,user,candidate['experiment_id'])
    proof = ledger.proof(user,ref,candidate['experiment_id'],calibration['calibration_id'])
    assert ledger.proof(user,ref,candidate['experiment_id'],calibration['calibration_id'])==proof
    assert proof['automatic_publish'] is False
    assert len(prompts)==3  # 来源、基线、候选均经正式Run且彼此独立，模型为合成。
    assert all('合成修订验收点' not in str(p) for p in prompts)
    links = list(res['db'].evaluation_execution_links.find({'regression_source':ref}))
    assert len(links)==2 and len({r['run_id'] for r in links})==2
    # 证明写入成功但应答丢失，重放必须返回同一不可变记录。
    real=ledger.store
    def ack_loss(collection,*args,**kwargs):
        real(collection,*args,**kwargs)
        raise SystemExit('合成证明应答丢失')
    monkeypatch.setattr(ledger,'store',ack_loss)
    with pytest.raises(SystemExit): ledger.proof(user,ref,candidate['experiment_id'],calibration['calibration_id'])
    monkeypatch.setattr(ledger,'store',real)
    assert ledger.proof(user,ref,candidate['experiment_id'],calibration['calibration_id'])==proof
    for eid in (baseline['experiment_id'],candidate['experiment_id']):
        saved = json.loads((tmp_path/'out'/eid/'manifest.json').read_text(encoding='utf-8'))
        assert saved['config_sha256'] != repo.get_experiment(user,eid)['config_sha256']
    # 结果变化时既有证明不允许直接重放成仍有效。
    repo.results.update_one({'experiment_id':candidate['experiment_id']},{'$set':{'result.answer':'合成变动'}})
    with pytest.raises(APIError): ledger.proof(user,ref,candidate['experiment_id'],calibration['calibration_id'])


def test_binding_concurrency_and_hash_change_before_run(evaluation_context,tmp_path,monkeypatch):
    cfg,res,prompts,q,repo,ev,user,data,catalog,ledger,bound = setup_lineage(evaluation_context,tmp_path,monkeypatch)
    target = bound['binding_request']
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _:ledger.bind(user,'synthetic-feedback',target),range(4)))
    assert all(r['sha256']==bound['sha256'] for r in results)
    ref = ledger.reference(bound)
    job = ev.create_experiment(user,data | dict(client_request_id='revoked',regression_source=ref))
    before = res['db'].runs.count_documents({})
    repo.db.support_feedback.update_one({'feedback_id':'synthetic-feedback'},{'$inc':{'version':1}})
    execute_job(repo,catalog,tmp_path/'out',job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']=='failed'
    assert res['db'].runs.count_documents({})==before and len(prompts)==1


@pytest.mark.parametrize('point',['after_create','after_link','after_results'])
def test_crash_window_reuses_pending_run_after_formal_recovery(evaluation_context,tmp_path,monkeypatch,point):
    cfg,res,prompts,q,repo,ev,user,data,catalog,ledger,bound = setup_lineage(evaluation_context,tmp_path,monkeypatch)
    job = ev.create_experiment(user,data | dict(client_request_id='crash',regression_source=ledger.reference(bound)))
    if point=='after_create':
        real = res['run_service'].create
        def crash(*args,**kwargs):
            result=real(*args,**kwargs)
            raise SystemExit('合成创建后进程退出')
        monkeypatch.setattr(res['run_service'],'create',crash)
    elif point=='after_link':
        import app.evaluation.execution_links as module
        real=module.bind_execution
        def crash(*args,**kwargs):
            real(*args,**kwargs)
            raise SystemExit('合成关联后进程退出')
        monkeypatch.setattr(module,'bind_execution',crash)
    else:
        real=repo.complete
        def crash(*args,**kwargs): raise SystemExit('合成结果文件已写、发布前退出')
        monkeypatch.setattr(repo,'complete',crash)
    with pytest.raises(SystemExit): execute_job(repo,catalog,tmp_path/'out',job['experiment_id'])
    # 仅随机隔离库到期模拟，生产不手改租约；正式claim恢复同实验attempt。
    repo.experiments.update_one({'experiment_id':job['experiment_id']},{'$set':{
        'lease_until':datetime.now(timezone.utc)-timedelta(seconds=1)}})
    if point=='after_create': monkeypatch.setattr(res['run_service'],'create',real)
    elif point=='after_link': monkeypatch.setattr(module,'bind_execution',real)
    else: monkeypatch.setattr(repo,'complete',real)
    execute_job(repo,catalog,tmp_path/'out',job['experiment_id'])
    row=repo.get_experiment(user,job['experiment_id'])
    assert row['state']=='completed' and len(prompts)==2
    assert res['db'].runs.count_documents({})==2
    link=res['db'].evaluation_execution_links.find_one(dict(experiment_id=job['experiment_id'],attempt=row['attempt']))
    assert link and link['regression_source']==ledger.reference(bound)
    if point=='after_results':
        result=repo.results.find_one(dict(experiment_id=job['experiment_id'],attempt=row['result_attempt']))['result']
        assert result['logical_provider_calls']['stream_started']==1
        assert result['execution_logical_provider_calls']['stream_started']==0


def test_candidate_requires_calibration_before_creation(evaluation_context,tmp_path,monkeypatch):
    cfg,res,prompts,q,repo,ev,user,data,catalog,ledger,bound = setup_lineage(evaluation_context,tmp_path,monkeypatch)
    baseline=ev.create_experiment(user,data | dict(client_request_id='baseline',regression_source=ledger.reference(bound)))
    execute_job(repo,catalog,tmp_path/'out',baseline['experiment_id'])
    with pytest.raises(APIError):
        ev.create_experiment(user,data | dict(client_request_id='too-early',regression_source=ledger.reference(bound),
            baseline_experiment_id=baseline['experiment_id']))
    assert repo.experiments.count_documents({'client_request_id':'too-early'})==0


def test_bound_continuation_keeps_parent_source_and_refuses_rebinding(evaluation_context,tmp_path,monkeypatch):
    from tests.integration.test_evaluation_split_ledger import interrupt
    cfg,res,prompts,q,repo,ev,user,data,catalog,ledger,bound = setup_lineage(evaluation_context,tmp_path,monkeypatch)
    ref=ledger.reference(bound)
    parent=ev.create_experiment(user,data | dict(client_request_id='interrupted-parent',regression_source=ref))
    real=res['query_runner'].execute
    def interrupted(rid):
        real(rid)
        interrupt(res,rid)
        raise RuntimeError('合成中断')
    monkeypatch.setattr(res['query_runner'],'execute',interrupted)
    execute_job(repo,catalog,tmp_path/'out',parent['experiment_id'])
    failed=repo.get_experiment(user,parent['experiment_id'])
    assert failed['state']=='failed'
    continuation=dict(source_experiment_id=failed['experiment_id'],source_attempt=failed['attempt'],
                      source_version=failed['version'],reason='合成来源一致continuation')
    with pytest.raises(APIError):
        ev.create_experiment(user,data | dict(client_request_id='wrong-source',continuation=continuation))
    child=ev.create_experiment(user,data | dict(client_request_id='child',continuation=continuation,regression_source=ref))
    monkeypatch.setattr(res['query_runner'],'execute',real)
    execute_job(repo,catalog,tmp_path/'out',child['experiment_id'])
    assert repo.get_experiment(user,child['experiment_id'])['state']=='completed'
    assert len(prompts)==3
    saved=res['db'].evaluation_continuations.find_one({})
    assert saved['source_run_id'] != saved['run_id']
    link=res['db'].evaluation_execution_links.find_one({'experiment_id':child['experiment_id']})
    assert link['regression_source']==ref
