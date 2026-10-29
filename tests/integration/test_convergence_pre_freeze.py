"""首次结果快照前退出及正式组合；仅合成模型、随机隔离库。"""
from datetime import datetime,timedelta,timezone
import pytest
from app.evaluation.jobs import execute_job
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_regression_formal_execution import setup_lineage
from tests.integration.test_query_runs import query_context
from tests.integration.test_run_claim import run_context,request
from tests.integration.test_source_prerequisite_run import setup_source

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('change',['none','question','products','support','history','missing_link'])
def test_before_first_outcome_uses_original_input(evaluation_context,tmp_path,monkeypatch,separate,change):
    evaluation_context[2]['query_runner'].embedder=lambda texts:dict(dense=[[1.,0.] for _ in texts])
    _,res,prompts,_,repo,ev,user,data,catalog,ledger,bound=setup_lineage(evaluation_context,tmp_path,monkeypatch,separate)
    job=ev.create_experiment(user,data|dict(client_request_id='pre-freeze',regression_source=ledger.reference(bound)))
    import app.evaluation.execution_identity as module
    freeze=module.freeze_outcome
    def crash(*args,**kwargs):raise SystemExit('合成首次快照前退出')
    monkeypatch.setattr(module,'freeze_outcome',crash)
    with pytest.raises(SystemExit):execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
    link=res['db'].evaluation_execution_links.find_one({'experiment_id':job['experiment_id']})
    rid=link['run_id'];run=res['db'].runs.find_one({'run_id':rid})
    changes={'question':{'question':'合成不同问题'},'products':{'input_product_snapshot.product_ids':['other']},
        'support':{'support_snapshot':{'synthetic':'changed'}}}
    if change in changes:res['db'].runs.update_one({'run_id':rid},{'$set':changes[change]})
    if change=='missing_link':res['db'].evaluation_execution_links.delete_one({'_id':link['_id']})
    if change=='history':res['db'].messages.insert_one(dict(message_id='synthetic-new-history',
        conversation_id=run['conversation_id'],owner_id=user.user_id,run_id='other',ordinal=1000,role='user',text='合成历史漂移'))
    repo.experiments.update_one({'experiment_id':job['experiment_id']},{'$set':{'lease_until':datetime.now(timezone.utc)-timedelta(seconds=1)}})
    monkeypatch.setattr(module,'freeze_outcome',freeze)
    execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
    actual=repo.get_experiment(user,job['experiment_id'])
    assert actual['state']==('completed' if change=='none' else 'failed')
    assert len(prompts)==2 and res['db'].runs.count_documents({})==2


@pytest.mark.parametrize('exclude',[False,True])
@pytest.mark.parametrize('variant',['authorized','rrf','weights','budget','request_mismatch'])
def test_official_combination_and_rollback(query_context,exclude,variant):
    from app.runs.models import InternalRunInput
    from app.retrieval.search import RetrievalPolicy
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    cfg,calls,prompts=setup_source(query_context)
    overrides={'rrf':{'fusion':'rrf'},'weights':{'dense_weight':.6},'budget':{'dense_limit':21}}
    runner.retrieval_policy=RetrievalPolicy(exclude_image_descriptions=exclude,**overrides.get(variant,{}))
    source=cfg if variant!='request_mismatch' else cfg.model_copy(update={'enabled':False}) if hasattr(cfg,'model_copy') else cfg|{'enabled':False}
    rid=service.create(user,cid,InternalRunInput(**request().model_dump(),source_prerequisites=source))['run_id']
    runner.execute(rid)
    assert repo.get(user,rid)['state']==('completed' if variant=='authorized' else 'failed')
    assert len(calls)==(1 if variant=='authorized' else 0)
    assert len(prompts)==(1 if variant=='authorized' else 0)


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('drift',[False,True])
def test_clarification_before_outcome(evaluation_context,tmp_path,monkeypatch,separate,drift):
    from copy import deepcopy
    from tests.unit.test_evaluation_dataset import independent_annotation
    evaluation_context[2]['query_runner'].embedder=lambda texts:dict(dense=[[1.,0.] for _ in texts])
    _,res,prompts,_,repo,ev,user,data,catalog,ledger,bound=setup_lineage(evaluation_context,tmp_path,monkeypatch,separate)
    feedback=deepcopy(repo.db.support_feedback.find_one({'feedback_id':'synthetic-feedback'}))
    feedback.pop('_id');feedback['feedback_id']='synthetic-clarify'
    feedback['draft'].update(question='ZZ-404 的额定电压是多少？',proposed_expectation='须先明确实际设备型号')
    repo.db.support_feedback.insert_one(feedback)
    question=deepcopy(bound['question'])
    question.update(id='clarification-q',group_id='clarification-family',question=feedback['draft']['question'],
        product_names=[],history=[],expected=dict(behavior='clarify',key_points=['须先明确实际设备型号'],forbidden_claims=[]),
        allowed_evidence=[],annotation=dict(method='source_checked_assistant_draft',status='draft'))
    candidate=ledger.candidate(user,feedback['feedback_id'],question)
    monkeypatch.setattr('app.evaluation.feedback_regression.verify_review_artifact',lambda _:None)
    annotation=ledger.review(user.model_copy(update={'user_id':'control_assistant'}),candidate['id'],independent_annotation(question))
    binding=ledger.bind(user,feedback['feedback_id'],bound['binding_request']|dict(question_id=question['id'],annotation_id=annotation['id']))
    ev.register_set(user,dict(kb_id=data['kb_id'],eval_set_id=binding['dataset_id'],version=binding['dataset_version']))
    job=ev.create_experiment(user,data|dict(client_request_id='clarify-pre-freeze',eval_set_version=binding['dataset_version'],
        config_id=binding['config_id'],config_version=binding['config_version'],regression_source=ledger.reference(binding)))
    import app.evaluation.execution_identity as module
    freeze=module.freeze_outcome
    def crash(db,cfg,key,run,result):
        if run['state']=='awaiting_input':raise SystemExit('合成澄清首次快照前退出')
        return freeze(db,cfg,key,run,result)
    monkeypatch.setattr(module,'freeze_outcome',crash)
    with pytest.raises(SystemExit):execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
    link=res['db'].evaluation_execution_links.find_one({'experiment_id':job['experiment_id'],'question_id':'clarification-q'})
    assert res['db'].runs.find_one({'run_id':link['run_id']})['state']=='awaiting_input'
    if drift:res['db'].runs.update_one({'run_id':link['run_id']},{'$set':{'support_snapshot':{'synthetic':'changed'}}})
    repo.experiments.update_one({'experiment_id':job['experiment_id']},{'$set':{'lease_until':datetime.now(timezone.utc)-timedelta(seconds=1)}})
    monkeypatch.setattr(module,'freeze_outcome',freeze)
    execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']==('failed' if drift else 'completed')
    assert len(prompts)==2 and res['db'].runs.count_documents({})==3
