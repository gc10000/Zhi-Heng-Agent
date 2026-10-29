"""完整执行主体恢复矩阵；仅合成模型及随机隔离库，故障记录保留。"""
from datetime import datetime, timedelta, timezone
import json
import pytest

from app.evaluation.jobs import execute_job
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_regression_formal_execution import setup_lineage

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('change',[
    'none','telemetry','question','input_products','support_snapshot','citation','asset',
    'state','candidate','result_behavior','result_state','result_citations','result_answer',
    'history','outcome_missing','link_missing'])
def test_result_publication_full_identity(evaluation_context,tmp_path,monkeypatch,separate,change):
    evaluation_context[2]['query_runner'].embedder = lambda texts: {'dense':[[1.0,0.0] for _ in texts]}
    _,res,prompts,_,repo,ev,user,data,catalog,ledger,bound = setup_lineage(
        evaluation_context,tmp_path,monkeypatch,separate=separate)
    job = ev.create_experiment(user,data | dict(client_request_id='recovery-matrix',regression_source=ledger.reference(bound)))
    complete = repo.complete
    def lost(*args,**kwargs): raise SystemExit('合成结果已落盘、发布中断')
    monkeypatch.setattr(repo,'complete',lost)
    with pytest.raises(SystemExit): execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
    attempts = tmp_path/'jobs'/job['experiment_id']/'attempts.jsonl'
    records = [json.loads(line) for line in attempts.read_text(encoding='utf8').splitlines()]
    result = records[-1]['result']
    rid = result['run_id']
    fields = {
        'question':{'question':'合成另一题'},'input_products':{'input_product_snapshot.product_ids':['changed']},
        'support_snapshot':{'support_snapshot':{'synthetic':'changed'}},
        'citation':{'citations':[]},'asset':{'citations.0.asset_ids':['untrusted-asset']},
        'state':{'state':'awaiting_input'},'candidate':{'candidates':[{'product_id':'changed'}]},
        'telemetry':{'telemetry.stage_seconds.synthetic':3.0}}
    if change in fields:
        res['db'].runs.update_one({'run_id':rid},{'$set':fields[change]})
    if change == 'history':
        run = res['db'].runs.find_one({'run_id':rid})
        res['db'].messages.insert_one(dict(message_id='synthetic-drift',conversation_id=run['conversation_id'],
            owner_id=user.user_id,run_id='changed-history',ordinal=1000,role='user',text='合成漂移历史'))
    if change.startswith('result_'):
        result[change.removeprefix('result_')] = {
            'result_behavior':'clarify','result_state':'awaiting_input',
            'result_citations':[],'result_answer':'合成变动答案'}[change]
        attempts.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in records),encoding='utf8')
    if change == 'outcome_missing': res['db'].evaluation_outcomes.delete_one({'run_id':rid})
    if change == 'link_missing': res['db'].evaluation_execution_links.delete_one({'run_id':rid})
    # 唯一会变的租约仅属于随机合成库；生产通过正式claim/recover协议。
    repo.experiments.update_one({'experiment_id':job['experiment_id']},{'$set':{
        'lease_until':datetime.now(timezone.utc)-timedelta(seconds=1)}})
    monkeypatch.setattr(repo,'complete',complete)
    execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
    actual = repo.get_experiment(user,job['experiment_id'])
    assert actual['state'] == ('completed' if change in {'none','telemetry'} else 'failed')
    assert res['db'].runs.count_documents({}) == 2 and len(prompts) == 2
    if actual['state'] == 'completed':
        published = repo.results.find_one({'experiment_id':job['experiment_id']})['result']
        assert published['logical_provider_calls']['stream_started'] == 1
        assert published['execution_logical_provider_calls']['stream_started'] == 0
