"""总控独立反例：完整dev含澄清题时，成功检查点的发布中断恢复。"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import pytest

from app.evaluation.jobs import execute_job
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_regression_formal_execution import setup_lineage
from tests.unit.test_evaluation_dataset import independent_annotation

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('separate',[False,True])
def test_actual_clarification_source_supplement_and_job_recovery(evaluation_context,tmp_path,monkeypatch,separate):
    from types import SimpleNamespace
    from app.evaluation.query_adapter import RealQueryExecutor
    from app.evaluation.feedback_regression import RegressionService
    from app.evaluation.feedback_triage import review_feedback,TriageInput
    from app.support.feedback import save_feedback,FeedbackInput
    from tests.integration.test_evaluation_split_ledger import formal_case
    evaluation_context[2]['query_runner'].embedder=lambda texts: {'dense':[[1.,0.] for _ in texts]}
    cfg,res,prompts,q,repo,ev,user,data,catalog=formal_case(
        evaluation_context,tmp_path,monkeypatch,separate=separate,reviewed=True)
    unknown=q | dict(question='ZZ-404 的额定电压是多少？',product_names=[],history=[])
    with RealQueryExecutor(cfg,resource_factory=evaluation_context[1]) as executor:
        result=executor(unknown)
    run=res['runs'].get(user,result['run_id'])
    assert run['state']=='awaiting_input' and not run.get('citations') and not prompts
    feedback=save_feedback(repo.db,user,run,FeedbackInput(run_id=run['run_id'],category='model',
        note='合成澄清来源闭环',client_request_id='source-clarification'))
    # 服务端固定随机测试目标映射，HTTP不接受任意库。
    repo.db.support_feedback.update_one({'feedback_id':feedback['feedback_id']},{'$set':{'source_database':res['db'].name}})
    request=SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(resources=dict(db=repo.db,knowledge=res['knowledge']))))
    feedback=review_feedback(request,user,feedback['feedback_id'],TriageInput(expected_version=0,
        decision='confirm',destination='regression',rationale='合成完整题目审核',proposed_question=unknown['question'],
        proposed_expectation='未知型号应先澄清',client_request_id='confirm-source-clarification'))
    ledger=RegressionService(repo,catalog)
    parent=ledger.resolve(dict(dataset_id='set',dataset_version='r1',config_id='control',config_version='r1'),data['kb_id'])
    from app.evaluation.validate_dataset import validate_dataset
    question=deepcopy(validate_dataset(parent['dataset_path'],manifest=parent['manifest_path'])[0])
    question.update(question=unknown['question'],product_names=[],history=[],
        expected=dict(behavior='clarify',key_points=['未知型号应先澄清'],forbidden_claims=[]),
        annotation=dict(method='source_checked_assistant_draft',status='draft'))
    refs=[{k:d[k] for k in ('document_id','revision_id')} for d in cfg['corpus']['documents']]
    draft=ledger.candidate(user,feedback['feedback_id'],question,refs)
    reviewer=user.model_copy(update={'user_id':'control_assistant'})
    monkeypatch.setattr('app.evaluation.feedback_regression.verify_review_artifact',lambda _:None)
    audit=ledger.review(reviewer,draft['id'],independent_annotation(question),draft['evidence_mapping_sha256'])
    binding=ledger.bind(user,feedback['feedback_id'],dict(dataset_id='set',dataset_version='r1',
        config_id='control',config_version='r1',question_id=question['id'],annotation_id=audit['id']))
    ev.register_set(user,dict(kb_id=data['kb_id'],eval_set_id=binding['dataset_id'],version=binding['dataset_version']))
    job=ev.create_experiment(user,data | dict(client_request_id='clarification-bound-job',
        eval_set_version=binding['dataset_version'],config_id=binding['config_id'],config_version=binding['config_version'],
        regression_source=ledger.reference(binding)))
    complete=repo.complete
    def crash(*args,**kwargs): raise SystemExit('合成发布中断')
    monkeypatch.setattr(repo,'complete',crash)
    with pytest.raises(SystemExit): execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
    repo.experiments.update_one({'experiment_id':job['experiment_id']},{'$set':{
        'lease_until':datetime.now(timezone.utc)-timedelta(seconds=1)}})
    monkeypatch.setattr(repo,'complete',complete)
    execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
    actual=repo.get_experiment(user,job['experiment_id'])
    assert actual['state']=='completed' and actual['attempt']==2
    assert not prompts and res['db'].runs.count_documents({})==2
    assert res['runs'].get(user,run['run_id'])==run


@pytest.mark.parametrize('separate', [False, True])
@pytest.mark.parametrize('crash', [False, True])
def test_completed_clarification_evaluation_survives_publication_recovery(
        evaluation_context, tmp_path, monkeypatch, crash, separate):
    evaluation_context[2]['query_runner'].embedder = lambda texts: {'dense':[[1.0, 0.0] for _ in texts]}
    cfg, res, prompts, question, repo, ev, user, data, catalog, ledger, bound = setup_lineage(
        evaluation_context, tmp_path, monkeypatch, separate=separate)
    # 正式来源仍是已完成的旧回答；新增dev题由真正QueryRunner产生awaiting_input。
    feedback = repo.db.support_feedback.find_one({'feedback_id':'synthetic-feedback'})
    fresh = {k:deepcopy(v) for k,v in feedback.items() if k != '_id'}
    fresh['feedback_id'] = 'clarification-feedback'
    fresh['draft']['question'] = 'ZZ-404 的额定电压是多少？'
    fresh['draft']['proposed_expectation'] = '须先明确实际设备型号'
    repo.db.support_feedback.insert_one(fresh)
    row = deepcopy(bound['question'])
    row.update(id='clarification-q', group_id='clarification-family',
               question=fresh['draft']['question'], product_names=[], history=[],
               expected=dict(behavior='clarify', key_points=['须先明确实际设备型号'], forbidden_claims=[]),
               allowed_evidence=[], annotation=dict(method='source_checked_assistant_draft', status='draft'))
    candidate = ledger.candidate(user, fresh['feedback_id'], row)
    reviewer = deepcopy(user).model_copy(update={'user_id':'control_assistant'})
    monkeypatch.setattr('app.evaluation.feedback_regression.verify_review_artifact', lambda _:None)
    annotation = ledger.review(reviewer, candidate['id'], independent_annotation(row))
    binding = ledger.bind(user, fresh['feedback_id'], bound['binding_request'] | dict(
        question_id=row['id'], annotation_id=annotation['id']))
    ev.register_set(user, dict(kb_id=data['kb_id'], eval_set_id=binding['dataset_id'],
                              version=binding['dataset_version']))
    request = data | dict(client_request_id='clarification-job',
        eval_set_version=binding['dataset_version'], config_id=binding['config_id'],
        config_version=binding['config_version'], regression_source=ledger.reference(binding))
    job = ev.create_experiment(user, request)
    complete = repo.complete
    if crash:
        def lost_publish(*args, **kwargs):
            raise SystemExit('合成崩溃：成功结果已落盘，数据库尚未发布')
        monkeypatch.setattr(repo, 'complete', lost_publish)
        with pytest.raises(SystemExit):
            execute_job(repo, catalog, tmp_path/'jobs', job['experiment_id'])
        repo.experiments.update_one({'experiment_id':job['experiment_id']}, {'$set':{
            'lease_until':datetime.now(timezone.utc)-timedelta(seconds=1)}})
        monkeypatch.setattr(repo, 'complete', complete)
    execute_job(repo, catalog, tmp_path/'jobs', job['experiment_id'])
    actual = repo.get_experiment(user, job['experiment_id'])
    rows = [json.loads(line) for line in (tmp_path/'jobs'/job['experiment_id']/'results.jsonl').read_text(
        encoding='utf-8').splitlines()]
    clarify = next(r for r in rows if r['id'] == row['id'])
    assert clarify['status'] == 'completed'
    assert clarify['result']['behavior'] == 'clarify'
    assert clarify['result']['state'] == 'awaiting_input'
    assert res['db'].runs.count_documents({}) == 3
    assert len(prompts) == 2  # 来源回答、dev回答；澄清和恢复均不应启动模型。
    assert actual['state'] == 'completed', actual.get('error')
