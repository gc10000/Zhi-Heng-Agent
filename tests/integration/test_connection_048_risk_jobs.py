"""新模式独立CAS账户的故障矩阵；仅随机短前缀合成Mongo。"""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest

from app.api.errors import APIError
from tests.unit.test_connection_048_admission import contract
from tests.integration.test_evaluation_run_adapter import evaluation_context

pytestmark=pytest.mark.integration


def isolated(mongo_db,tmp_path,monkeypatch,separate):
    from app.infrastructure.providers import connection_comparison_048_risk as risk
    from app.infrastructure.providers.output_contract import OutputLedger
    control=mongo_db.name+'_ctl' if separate else mongo_db.name
    policy=contract(True);slot=risk.SLOT
    member=dict(fixed_slot=slot,expected_generation=True)
    entry=dict(member=member,config_subject=dict(target=dict(database=mongo_db.name)),question=dict(id=risk.QUESTION_ID))
    manifest=dict(shared_control_database=control,dispatch_order=[slot],entries=[entry])
    monkeypatch.setattr(risk,'require',lambda _:manifest)
    monkeypatch.setattr(risk,'sources',lambda _:(dict(runtime={},budget={}),member,dict(result=dict(budget=dict(input_tokens=28416))),{}))
    monkeypatch.setattr(risk,'validate_config',lambda *a,**kw:None)
    monkeypatch.setattr(risk,'validate_runtime',lambda *a:None)
    monkeypatch.setattr(risk,'batch_dir',lambda:tmp_path/'batch')
    monkeypatch.setattr(risk,'slot_dir',lambda _:tmp_path/'batch/members'/slot)
    (tmp_path/'batch/members'/slot).mkdir(parents=True)
    mongo_db.runs.insert_one(dict(run_id='new-run',identity='new-identity'))
    context=dict(config={},question=dict(id=risk.QUESTION_ID),control_database=control,
        execution=dict(experiment_id='synthetic-experiment',attempt=1,config_sha256='a'*64))
    ledger=OutputLedger(mongo_db,policy)
    assert isinstance(ledger,risk.ConnectionComparison048Ledger)
    return SimpleNamespace(ledger=ledger,context=context,db=mongo_db,policy=policy,risk=risk,control=control)


def begin(c):
    c.ledger.begin('new-run','new-identity',input_reservation=28416,risk_context=c.context)


def settle(c,*,usage=None,completed=True,finish='stop',reasoning=False):
    return c.ledger.settle('new-run','new-identity',{'input':12,'output':18} if usage is None else usage,
        completed=completed,logical_calls=dict(invoke_started=0,stream_started=1),
        product_state=dict(visible_body=True,truncated=False,finish_reason=finish,observed_reasoning=reasoning))


@pytest.mark.parametrize('separate',[False,True])
def test_new_single_slot_reserves_settles_idempotently_and_never_reclaims(mongo_db,tmp_path,monkeypatch,separate):
    c=isolated(mongo_db,tmp_path,monkeypatch,separate);begin(c)
    pending=c.ledger._read()
    assert pending['pending']['input_reservation']==28416 and pending['pending']['output_reservation']==4096
    first=settle(c);again=settle(c)
    assert first==again and first['state']=='awaiting_review'
    assert (first['prior_input_tokens'],first['prior_output_tokens'])==(56239,30516)
    assert (first['known_new_input_tokens'],first['known_new_output_tokens'])==(12,18)
    assert first['logical_reservations']==1 and first['exact_http_requests'] is None and first['exact_cost'] is None
    assert c.ledger.rows.database.name==c.control
    assert c.db.diagnostic_comparison_answer_048_v2_accounts.count_documents({})==0
    assert c.db.diagnostic_comparison_answer_048_accounts.count_documents({})==0
    with pytest.raises(APIError):begin(c)
    c.ledger.review(accepted=False,evidence=dict(source_checked=True,reason='合成质量拒绝'))
    c.ledger.halt(dict(no_more_provider_calls=True,reason='合成失败停止'))
    with pytest.raises(APIError):begin(c)
    assert c.ledger._read()['state']=='blocked' and c.ledger._read()['logical_reservations']==1


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('fault',['unknown_usage','interruption','filter','reasoning','overflow'])
def test_bad_usage_or_termination_blocks_without_refund(mongo_db,tmp_path,monkeypatch,separate,fault):
    c=isolated(mongo_db,tmp_path,monkeypatch,separate);begin(c)
    values={'unknown_usage':dict(usage={}), 'interruption':dict(completed=False),
        'filter':dict(finish='content_filter'), 'reasoning':dict(reasoning=True),
        'overflow':dict(usage={'input':12,'output':4097})}[fault]
    saved=settle(c,**values)
    assert saved['state']=='blocked' and saved['pending'] is None and saved['logical_reservations']==1
    if fault=='unknown_usage':
        assert saved['new_input_tokens'] is None and saved['new_output_tokens'] is None and saved['unknown_windows']
    with pytest.raises(APIError):begin(c)
    with pytest.raises(ValueError):c.ledger.review(accepted=True,evidence=dict(source_checked=True))


def test_concurrent_new_slot_has_only_one_winner(mongo_db,tmp_path,monkeypatch):
    from app.infrastructure.providers.output_contract import OutputLedger
    c=isolated(mongo_db,tmp_path,monkeypatch,True)
    peer=OutputLedger(c.db,c.policy)
    def reserve(ledger):
        try:
            ledger.begin('new-run','new-identity',input_reservation=28416,risk_context=c.context)
            return True
        except (APIError,FileExistsError):return False
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(reserve,[c.ledger,peer]))==1
    saved=c.ledger._read()
    assert saved['logical_reservations']==saved['job_reservations']==1


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('fault',[None,'interruption','unknown_usage','reasoning'])
def test_formal_connection_job_settles_new_account(evaluation_context,tmp_path,monkeypatch,separate,fault):
    """准入来源/wire以合成端口替换；正式job、Run、usage和新账本实际执行。"""
    import json
    from app.evaluation.jobs import execute_job
    from app.infrastructure.providers import connection_comparison_048_risk as risk
    from app.knowledge.repository import fingerprint
    from tests.integration.test_connection_comparison_jobs import case, RAW
    cfg,res,prompts,question,repo,service,user,data,catalog=case(
        evaluation_context,tmp_path,monkeypatch,separate=separate)
    cfg['parameters']['answer_budget'].update(output_tokens=4096,reserve_tokens=256,
        output_token_field='max_completion_tokens',output_contract=contract(True))
    (tmp_path/'config.json').write_text(json.dumps(cfg),encoding='utf-8')
    entry=dict(member=dict(fixed_slot=risk.SLOT,expected_generation=True),
        config_subject=dict(target=dict(database=res['db'].name)),question=dict(id=question['id']))
    manifest=dict(shared_control_database=repo.db.name,dispatch_order=[risk.SLOT],entries=[entry])
    observed={}
    monkeypatch.setattr(risk,'require',lambda _:manifest)
    monkeypatch.setattr(risk,'validate_config',lambda *a,**kw:None)
    monkeypatch.setattr(risk,'validate_runtime',lambda *a:None)
    def prompt_checked(policy,prompt,state):observed['budget']=state['prompt_budget']
    monkeypatch.setattr(risk,'validate_prompt',prompt_checked)
    monkeypatch.setattr(risk,'sources',lambda _:(dict(runtime={},budget={}),entry['member'],dict(result=observed),{}))
    monkeypatch.setattr(risk,'batch_dir',lambda:tmp_path/'risk-batch')
    monkeypatch.setattr(risk,'slot_dir',lambda _:tmp_path/'risk-batch/members'/risk.SLOT)
    (tmp_path/'risk-batch/members'/risk.SLOT).mkdir(parents=True)
    monkeypatch.setattr('app.infrastructure.providers.clients.output_limit_options',lambda *a,**kw:{})
    class Model:
        def stream(self,prompt,**kwargs):
            prompts.append(prompt)
            yield SimpleNamespace(content=RAW,response_metadata=dict(finish_reason='stop',**(
                {} if fault=='unknown_usage' else dict(token_usage=dict(prompt_tokens=12,completion_tokens=18,total_tokens=30)))),
                additional_kwargs=dict(reasoning_content='合成思考') if fault=='reasoning' else {})
            if fault=='interruption':raise TimeoutError('合成断流')
    res['query_runner'].llm_factory=Model
    job=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'formal',job['experiment_id'])
    run=res['db'].runs.find_one({})
    account=repo.db[risk.ACCOUNT_COLLECTION].find_one({'_id':fingerprint([risk.VERSION,risk.BATCH])})
    assert account and account['pending'] is None and account['logical_reservations']==1
    assert account['state']==('awaiting_review' if fault is None else 'blocked')
    assert len(prompts)==1 and res['db'].runs.count_documents({})==1
    assert run['state']==('completed' if fault is None else 'failed')
    receipt=account['settled'][risk.SLOT]
    if fault is None:
        assert receipt['product_state']==dict(visible_body=True,truncated=False,finish_reason='stop',
            observed_reasoning=False,mode_observations=[])
        assert (account['known_new_input_tokens'],account['known_new_output_tokens'])==(12,18)
    if fault=='reasoning':assert receipt['product_state']['observed_reasoning'] is True
    if fault=='unknown_usage':assert account['unknown_windows'] and account['new_input_tokens'] is None
    if fault=='interruption':assert not receipt['completed'] and run['comparison_answer_failure']['raw_selection']==RAW
    assert res['db'].diagnostic_comparison_answer_048_v2_accounts.count_documents({})==0
    # 重建实验只观察同一成功/失败Run，不领取第二份额度或再次生成。
    reuse=service.create_experiment(user,data|dict(client_request_id='reuse'))
    execute_job(repo,catalog,tmp_path/'reuse',reuse['experiment_id'])
    assert len(prompts)==1 and res['db'].runs.count_documents({})==1
    assert repo.db[risk.ACCOUNT_COLLECTION].find_one({'_id':account['_id']})==account
