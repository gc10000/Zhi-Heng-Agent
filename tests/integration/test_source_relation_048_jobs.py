"""单成员正式job与故障窗口；合成流，只写随机隔离Mongo库。"""
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.api.errors import APIError
from tests.unit.test_source_relation_048_risk import make_sr048_case
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration import test_nonthinking_manifest_jobs as prior

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('mode',['good','bad_usage','interrupted','length','empty','snapshot_crash','after_create','after_link','before_slot','after_slot','gateway400','reasoning_content','reasoning_count','reasoning_early'])
def test_formal_single_job_and_checkpoint_reuse(evaluation_context,tmp_path,monkeypatch,separate,mode):
    monkeypatch.setattr(prior,'make_nonthinking_case',make_sr048_case)
    prior.test_formal_nonthinking_job_and_success_reuse(evaluation_context,tmp_path,monkeypatch,separate,mode)


def single_ledger(mongo_db,tmp_path,monkeypatch):
    from app.infrastructure.providers.output_contract import OutputLedger
    c=make_sr048_case(tmp_path,monkeypatch,controls=[mongo_db.name],target_database=mongo_db.name)
    monkeypatch.setattr(c.module,'validate_runtime',lambda *a:None) # 仅原子账户测试；上方正式job保持Run/link核验。
    db=mongo_db.client[c.configs[0]['target']['database']]
    a=OutputLedger(db,c.policies[0]);db.runs.insert_one(dict(run_id='single',identity='identity'))
    ctx=dict(config=c.configs[0],question=c.questions[0],control_database=c.controls[0],
        execution=dict(experiment_id='synthetic',attempt=1,config_sha256=c.fp(c.configs[0])))
    return c,a,ctx


def begin(a,ctx):return a.begin('single','identity',input_reservation=12,risk_context=ctx)
def settle(a,usage=None,completed=True,**kw):
    return a.settle('single','identity',usage if usage is not None else dict(input=5,output=6),completed=completed,
        product_state=dict(visible_body=True,truncated=False,finish_reason='stop',observed_reasoning=False)|kw,
        logical_calls=dict(invoke_started=0,stream_started=1))


def test_single_cas_and_source_rejection_never_regrant(mongo_db,tmp_path,monkeypatch):
    c,a,ctx=single_ledger(mongo_db,tmp_path,monkeypatch)
    def claim(_):
        try:begin(a,ctx);return True
        except (APIError,FileExistsError):return False
    with ThreadPoolExecutor(max_workers=3) as pool:assert sum(pool.map(claim,range(3)))==1
    settle(a);a.review(accepted=False,evidence=dict(source_checked=True,assertions=['合成来源拒绝']))
    a.halt(dict(reason='synthetic_source_failure'))
    with pytest.raises(APIError):begin(a,ctx)
    assert a._read()['state']=='blocked' and a._read()['logical_reservations']==1


@pytest.mark.parametrize('fault',['before_settlement_file','after_review_file'])
def test_single_durable_seal_window_never_regrant(mongo_db,tmp_path,monkeypatch,fault):
    c,a,ctx=single_ledger(mongo_db,tmp_path,monkeypatch);begin(a,ctx);native=c.module.exclusive
    if fault=='before_settlement_file':
        def crash(path,value):
            if path.name=='settled.json':raise SystemExit('合成DB提交后退出')
            return native(path,value)
        monkeypatch.setattr(c.module,'exclusive',crash)
        with pytest.raises(SystemExit):settle(a)
        monkeypatch.setattr(c.module,'exclusive',native);settle(a)
    else:
        settle(a);cas=a._cas
        monkeypatch.setattr(a,'_cas',lambda *x:(_ for _ in ()).throw(SystemExit('合成来源文件后退出')))
        with pytest.raises(SystemExit):a.review(accepted=True,evidence=dict(source_checked=True,assertions=['合成']))
        monkeypatch.setattr(a,'_cas',cas)
    with pytest.raises(APIError):begin(a,ctx)
    assert a._read()['logical_reservations']==1


@pytest.mark.parametrize('bad',['missing','negative','boolean','conflicting','over','incomplete','empty','length','reasoning'])
def test_single_invalid_observation_persistently_stops(mongo_db,tmp_path,monkeypatch,bad):
    c,a,ctx=single_ledger(mongo_db,tmp_path,monkeypatch);begin(a,ctx)
    usage=dict(input=5,output=6);kw={};completed=True
    if bad=='missing':usage.pop('output')
    if bad=='negative':usage['output']=-1
    if bad=='boolean':usage['output']=True
    if bad=='conflicting':usage['completion_tokens']=7
    if bad=='over':usage['output']=4097
    if bad=='incomplete':completed=False
    if bad=='empty':kw['visible_body']=False
    if bad=='length':kw.update(finish_reason='length',truncated=True)
    if bad=='reasoning':kw['observed_reasoning']=True
    assert settle(a,usage,completed,**kw)['state']=='blocked'
    with pytest.raises(ValueError):a.review(accepted=True,evidence=dict(source_checked=True,assertions=['不可放行']))
    with pytest.raises(APIError):begin(a,ctx)
