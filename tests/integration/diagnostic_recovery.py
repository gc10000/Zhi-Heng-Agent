"""诊断策略在正式continuation中的合成矩阵；不改真实运行。"""
from datetime import datetime,timedelta,timezone
from app.evaluation.jobs import execute_job
from app.runs.query_runner import ExecutionStopped
from tests.integration.test_evaluation_split_ledger import formal_case


def continuation_case(ctx,tmp_path,monkeypatch,*,separate,drift,field):
    cfg,res,prompts,question,repo,service,user,data,catalog=formal_case(ctx,tmp_path,monkeypatch,separate=separate)
    runner=res['query_runner'];old_ranker=runner.ranker
    def stop(*a,**kw):raise ExecutionStopped()
    runner.ranker=stop
    parent=service.create_experiment(user,data);execute_job(repo,catalog,tmp_path/'parent',parent['experiment_id'])
    run=res['db'].runs.find_one({});assert run['state']=='running' and not prompts
    res['commands'].clock=lambda:datetime.now(timezone.utc)+timedelta(hours=1)
    assert run['run_id'] in res['commands'].recover()
    if drift:res['db'].runs.update_one({'run_id':run['run_id']},{'$set':{field:'0'*64}})
    failed=repo.get_experiment(user,parent['experiment_id']);runner.ranker=old_ranker
    child=service.create_experiment(user,data|dict(client_request_id='child',continuation=dict(
        source_experiment_id=failed['experiment_id'],source_attempt=failed['attempt'],source_version=failed['version'],
        reason='合成诊断策略中断后的显式来源接续')))
    execute_job(repo,catalog,tmp_path/'child',child['experiment_id'])
    assert repo.get_experiment(user,child['experiment_id'])['state']==('failed' if drift else 'completed')
    assert res['db'].runs.count_documents({})==(1 if drift else 2)
    assert len(prompts)==(0 if drift else 1)
