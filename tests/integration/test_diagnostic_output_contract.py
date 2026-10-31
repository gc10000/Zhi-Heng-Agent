"""随机隔离Mongo的诊断串行结算；能力与输出均为明确合成夹具。"""
from copy import deepcopy
import pytest
from app.api.errors import APIError
from app.infrastructure.providers.output_contract import OutputLedger
from tests.unit.test_output_contract import verified_case
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_split_ledger import formal_case
from types import SimpleNamespace

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('out,completed',[(6150,True),(None,True),(4096,False),(4744,True)])
def test_unknown_over_limit_and_interruption_block_next_question(mongo_db,monkeypatch,out,completed):
    p,_,_=verified_case(monkeypatch);ledger=OutputLedger(mongo_db,p)
    # 此处隔离cap/中断故障；非法明细由独立矩阵覆盖，不能当作已知usage。
    reason={6150:5556,4744:3848,4096:3000}.get(out)
    ledger.begin('run1','input1');ledger.settle('run1','input1',{'input':7,'output':out},completed=completed,reasoning=reason)
    with pytest.raises(APIError):ledger.require_open()
    with pytest.raises(APIError):OutputLedger(mongo_db,p).begin('run2','input2')
    saved=ledger._read();assert saved['state']=='blocked'
    assert saved['new_output_tokens']==(out if out is not None and completed else None)
    assert saved['known_new_output_tokens']==(out or 0)
    assert saved['exact_cost'] is None and saved['exact_http_requests'] is None
    if out is None or not completed:assert saved['unknown_windows']


def test_saved_before_stream_unknown_window_does_not_reopen(mongo_db,monkeypatch):
    p,_,_=verified_case(monkeypatch);OutputLedger(mongo_db,p).begin('r','i')
    recovered=OutputLedger(mongo_db,p)
    with pytest.raises(APIError):recovered.begin('r','i')
    with pytest.raises(APIError):recovered.begin('next','i2')
    assert recovered._read()['pending']['run_id']=='r'


def test_atomic_settlement_is_idempotent_but_cannot_change_or_reinvoke(mongo_db,monkeypatch):
    p,_,_=verified_case(monkeypatch);ledger=OutputLedger(mongo_db,p)
    ledger.begin('r','i');a=ledger.settle('r','i',{'input':7,'output':4000},completed=True)
    assert OutputLedger(mongo_db,p).settle('r','i',{'input':7,'output':4000},completed=True)==a
    with pytest.raises(APIError):ledger.settle('r','i',{'input':7,'output':3},completed=True)
    with pytest.raises(APIError):ledger.begin('r','i')
    ledger.begin('second','i2');ledger.settle('second','i2',{'input':8,'output':4000},completed=True)
    assert ledger._read()['new_output_tokens']==8000
    with pytest.raises(APIError):ledger.begin('third','i3')


def test_budget_contract_drift_and_cross_database_do_not_adopt_old_account(mongo_db,monkeypatch):
    p,_,_=verified_case(monkeypatch);ledger=OutputLedger(mongo_db,p);ledger.begin('r','i')
    with pytest.raises(APIError):OutputLedger(mongo_db,p|{'max_total_output_tokens':10000}).begin('x','y')
    other=mongo_db.client[mongo_db.name+'_other']
    # 分库独立账本，不把另一库的未结算窗口写回或标成已完成。
    OutputLedger(other,p).begin('x','y')
    assert ledger._read()['pending']['run_id']=='r'
    assert OutputLedger(other,p)._read()['pending']['run_id']=='x'


def test_prior_and_new_usage_are_separate_and_reasoning_not_added(mongo_db,monkeypatch):
    p,_,_=verified_case(monkeypatch);p.update(prior_input_tokens=23480,prior_output_tokens=16506,
        prior_source_sha256='c'*64,max_total_output_tokens=25000)
    ledger=OutputLedger(mongo_db,p);ledger.begin('r','i')
    r=ledger.settle('r','i',{'input':7,'output':2000},completed=True,reasoning=1500)
    assert r['prior_output_tokens']==16506 and r['new_output_tokens']==2000
    assert ledger.require_open()['state']=='open'


def output_case(ctx,monkeypatch,*,unknown=False,output=40):
    cfg,_,res,prompts,_,_=ctx
    p,client,_=verified_case(monkeypatch)
    if unknown:p['status']='unknown';p['semantics']='unknown';p['evidence']=None
    cfg.update(strategy='m4-configured',parameters=dict(answer_budget=dict(output_contract=p)))
    def stream(prompt,**kw):
        prompts.append(prompt)
        assert kw['extra_body']['max_tokens']==4096
        yield SimpleNamespace(content='合成结果。[1]',usage_metadata={'input_tokens':20,'output_tokens':output,
            'output_token_details':{'reasoning':30}},response_metadata={'finish_reason':'stop'})
    client.stream=stream
    res['query_runner'].llm_factory=lambda:client
    return p


@pytest.mark.parametrize('separate',[False,True])
def test_output_contract_crosses_formal_config_run_checkpoint_and_reuse(evaluation_context,tmp_path,monkeypatch,separate):
    from app.evaluation.jobs import execute_job
    from app.infrastructure.providers.output_contract import payload
    p=output_case(evaluation_context,monkeypatch)
    cfg,res,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch,separate=separate)
    for key in ('first','reuse'):
        job=service.create_experiment(user,data|dict(client_request_id=key));execute_job(repo,catalog,tmp_path/key,job['experiment_id'])
        assert repo.get_experiment(user,job['experiment_id'])['state']=='completed'
        link=res['db'].evaluation_execution_links.find_one({'experiment_id':job['experiment_id']})
        assert link['output_contract']==payload(p)
    run=res['db'].runs.find_one({});checkpoint=res['db'].evaluation_items.find_one({})
    assert run['output_contract']==checkpoint['output_contract']==payload(p)
    assert len(prompts)==1
    account=res['db'].diagnostic_output_accounts.find_one({})
    assert account['new_output_tokens']==40 and account['logical_reservations']==1
    receipt=next(iter(account['settled'].values()))
    assert receipt['output_minus_reasoning']==10 and receipt['visible_tokens'] is None
    assert receipt['logical_provider_calls']==dict(invoke_started=0,stream_started=1)


@pytest.mark.parametrize('unknown,output',[(True,40),(False,6150),(False,None)])
def test_formal_unknown_rejects_before_stream_and_bad_usage_blocks(evaluation_context,tmp_path,monkeypatch,unknown,output):
    from app.evaluation.jobs import execute_job
    output_case(evaluation_context,monkeypatch,unknown=unknown,output=output)
    cfg,res,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch)
    job=service.create_experiment(user,data);execute_job(repo,catalog,tmp_path/'run',job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']=='failed'
    assert len(prompts)==(0 if unknown else 1)
    if unknown:assert res['db'].diagnostic_output_accounts.count_documents({})==0
    else:assert res['db'].diagnostic_output_accounts.find_one({})['state']=='blocked'


@pytest.mark.parametrize('drift',[False,True])
def test_output_contract_first_snapshot_crash_rechecks_frozen_identity(evaluation_context,tmp_path,monkeypatch,drift):
    from app.evaluation.jobs import execute_job
    output_case(evaluation_context,monkeypatch)
    cfg,res,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch)
    execute=res['query_runner'].execute
    def crash(rid):execute(rid);raise RuntimeError('合成已结算、结果快照前退出')
    monkeypatch.setattr(res['query_runner'],'execute',crash)
    first=service.create_experiment(user,data);execute_job(repo,catalog,tmp_path/'first',first['experiment_id'])
    run=res['db'].runs.find_one({});assert run['state']=='completed' and len(prompts)==1
    if drift:res['db'].runs.update_one({'run_id':run['run_id']},{'$set':{'output_contract_sha256':'0'*64}})
    monkeypatch.setattr(res['query_runner'],'execute',execute)
    second=service.create_experiment(user,data|dict(client_request_id='resume'));execute_job(repo,catalog,tmp_path/'second',second['experiment_id'])
    assert repo.get_experiment(user,second['experiment_id'])['state']==('failed' if drift else 'completed')
    assert len(prompts)==1 and res['db'].diagnostic_output_accounts.find_one({})['logical_reservations']==1


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('drift',[False,True])
def test_output_contract_explicit_continuation(evaluation_context,tmp_path,monkeypatch,separate,drift):
    from tests.integration.diagnostic_recovery import continuation_case
    output_case(evaluation_context,monkeypatch)
    continuation_case(evaluation_context,tmp_path,monkeypatch,separate=separate,drift=drift,field='output_parameters_sha256')


def test_pending_usage_and_cumulative_input_cap_are_not_zero(mongo_db,monkeypatch):
    p,_,_=verified_case(monkeypatch);p['max_total_input_tokens']=100
    ledger=OutputLedger(mongo_db,p)
    with pytest.raises(APIError):ledger.begin('r','i',input_reservation=101)
    ledger.begin('r','i',input_reservation=80)
    assert ledger._read()['new_output_tokens'] is None
    saved=ledger.settle('r','i',{'input':101,'output':3},completed=True)
    assert saved['state']=='blocked'
