"""非思考固定清单的正式单题集成；全部合成流，随机隔离库。"""
import copy
import json
import httpx
import pytest
from app.api.errors import APIError
from tests.unit.test_nonthinking_manifest import make_nonthinking_case
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_split_ledger import formal_case
from tests.integration import test_remaining_manifest_jobs as old
pytestmark=pytest.mark.integration


@pytest.fixture
def ledger_adapter(monkeypatch):
    native=old.settle
    monkeypatch.setattr(old,'make_remaining_case',make_nonthinking_case)
    monkeypatch.setattr(old,'settle',lambda a,usage=None,completed=True,**kw:native(a,usage,completed,observed_reasoning=False,**kw))


@pytest.mark.parametrize('case',['shared','budget','before_slot','after_slot','before_settlement_file','after_review_file'])
def test_nonthinking_shared_and_crash_windows(mongo_db,tmp_path,monkeypatch,ledger_adapter,case):
    if case=='shared':old.test_two_control_databases_share_atomic_inflight_and_prior_once(mongo_db,tmp_path,monkeypatch)
    elif case=='budget':old.test_cumulative_budget_is_one_shared_total_across_control_databases(mongo_db,tmp_path,monkeypatch)
    else:old.test_durable_crash_windows_never_regrant(mongo_db,tmp_path,monkeypatch,case)


@pytest.mark.parametrize('bad',['missing','negative','boolean','conflicting','over','incomplete','empty','length','no_finish'])
def test_nonthinking_bad_usage_or_completion_stops_both_databases(mongo_db,tmp_path,monkeypatch,ledger_adapter,bad):
    old.test_any_usage_or_completion_failure_blocks_both_databases(mongo_db,tmp_path,monkeypatch,bad)


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('mode',['good','bad_usage','interrupted','length','empty','snapshot_crash','after_create','after_link','before_slot','after_slot','gateway400','reasoning_content','reasoning_count','reasoning_early'])
def test_formal_nonthinking_job_and_success_reuse(evaluation_context,tmp_path,monkeypatch,separate,mode):
    from app.evaluation.jobs import execute_job
    from app.evaluation.query_adapter import RealQueryExecutor
    from app.infrastructure.providers.diagnostic_usage import preserving_chat_class
    from app.infrastructure.providers.output_contract import OutputLedger
    cfg,factory,res,prompts,q,_=evaluation_context
    runner=res['query_runner'];original=runner.evidence_prompt;captured=[]
    def capture(*a,**kw):
        state,prompt=original(*a,**kw);captured.append((copy.deepcopy(state),prompt));return state,prompt
    monkeypatch.setattr(runner,'evidence_prompt',capture)
    with RealQueryExecutor(cfg,resource_factory=factory) as execute:execute(q)
    state,prompt=captured[-1];(tmp_path/'formal').mkdir()
    cfg,res,prompts,q,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path/'formal',monkeypatch,separate=separate)
    expected=dict(prompt=prompt,context=state['prompt_used_docs'],groups=state.get('evidence_groups',[]),prompt_reference_map=state.get('prompt_reference_map',[]),budget=state['prompt_budget'])
    source=copy.deepcopy(cfg);source['strategy']='m4-configured'
    source['parameters']=dict(answer_budget=dict(context_window=32768,output_tokens=4096,reserve_tokens=256,max_chars=12000))
    c=make_nonthinking_case(tmp_path/'risk',monkeypatch,configs=[source,source],questions=[q,q],expected=[expected,expected],controls=[repo.db.name,repo.db.name+'_c2'])
    monkeypatch.setattr(c.module,'validate_previous_account',lambda *a:None) # 合成旧账；正式Run／租约／关联检查保持。
    cfg.clear();cfg.update(c.configs[0]);(tmp_path/'formal/config.json').write_text(json.dumps(cfg),encoding='utf-8')
    sent=[]
    def handle(req):
        body=json.loads(req.content);sent.append(body)
        assert body['enable_thinking'] is False
        assert body['n']==1 and body['max_completion_tokens']==4096 and 'max_tokens' not in body
        assert (c.module.slot_dir(c.policies[0])/'started.json').is_file()
        if mode=='gateway400':return httpx.Response(400,json=dict(error=dict(message='synthetic parameter rejected',type='invalid_request_error')))
        if mode=='interrupted':raise httpx.ReadTimeout('合成断流')
        chunk=dict(id='synthetic',object='chat.completion.chunk',created=1,model='synthetic',choices=[dict(index=0,
            delta=dict(role='assistant',content='' if mode=='empty' else '合成结果。[1]',reasoning_content='合成推理' if mode=='reasoning_content' else ''),finish_reason='length' if mode=='length' else 'stop')],
            usage=dict(prompt_tokens=20,completion_tokens=8,total_tokens=28,completion_tokens_details=dict(reasoning_tokens=True if mode=='bad_usage' else 2 if mode in ('reasoning_count','reasoning_early') else 0)))
        chunks=[chunk]
        if mode=='reasoning_early':
            tail=copy.deepcopy(chunk);tail['choices']=[];tail['usage'].pop('completion_tokens_details');chunks.append(tail)
        return httpx.Response(200,headers={'content-type':'text/event-stream'},content=''.join('data: '+json.dumps(v)+'\n\n' for v in chunks)+'data: [DONE]\n\n')
    with httpx.Client(transport=httpx.MockTransport(handle),follow_redirects=False) as transport:
        client=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',n=1,stream_usage=True,max_retries=0,timeout=120,temperature=.1,http_client=transport,extra_body={'enable_thinking':False})
        runner.llm_factory=lambda:client
        native_execute=runner.execute
        if mode=='after_create':
            native_create=res['run_service'].create
            def crash_create(*a,**kw):native_create(*a,**kw);raise SystemExit('合成登记后关联前退出')
            monkeypatch.setattr(res['run_service'],'create',crash_create)
        if mode=='after_link':
            from app.evaluation import execution_links
            native_link=execution_links.bind_execution
            def crash_link(*a,**kw):native_link(*a,**kw);raise SystemExit('合成关联后预留前退出')
            monkeypatch.setattr(execution_links,'bind_execution',crash_link)
        if mode in ('before_slot','after_slot'):
            native_exclusive=c.module.exclusive
            def crash_slot(path,value):
                if path.name=='started.json':
                    if mode=='after_slot':native_exclusive(path,value)
                    raise SystemExit('合成预留后磁盘窗口退出')
                return native_exclusive(path,value)
            monkeypatch.setattr(c.module,'exclusive',crash_slot)
        if mode=='snapshot_crash':
            def crash(rid):native_execute(rid);raise RuntimeError('合成快照前退出')
            monkeypatch.setattr(runner,'execute',crash)
        job=service.create_experiment(user,data)
        if mode in ('after_create','after_link','before_slot','after_slot'):
            with pytest.raises(SystemExit):execute_job(repo,catalog,tmp_path/'out',job['experiment_id'])
            assert not sent
            a=OutputLedger(res['db'],c.policies[0])
            if mode in ('before_slot','after_slot'):
                assert a._read()['state']=='pending' and a._read()['logical_reservations']==1
            else:
                assert a.rows.count_documents({'_id':a.key})==0
            assert (c.module.slot_dir(c.policies[0])/'started.json').exists()==(mode=='after_slot')
            return
        execute_job(repo,catalog,tmp_path/'out',job['experiment_id'])
        assert repo.get_experiment(user,job['experiment_id'])['state']==('completed' if mode=='good' else 'failed')
        assert len(sent)==1
        a=OutputLedger(res['db'],c.policies[0]);s=a._read()
        assert s['state']==('awaiting_review' if mode in ('good','snapshot_crash') else 'blocked')
        assert (c.module.slot_dir(c.policies[0])/'settled.json').is_file()
        if mode=='snapshot_crash':monkeypatch.setattr(runner,'execute',native_execute)
        replay=service.create_experiment(user,data|dict(client_request_id='recovery'))
        execute_job(repo,catalog,tmp_path/'replay',replay['experiment_id'])
        assert len(sent)==1
        if mode in ('good','snapshot_crash'):
            assert repo.get_experiment(user,replay['experiment_id'])['state']=='completed'
            a.review(accepted=True,evidence=dict(source_checked=True,assertions=['合成来源一致']))
            assert a._read()['cursor']==1


def test_nonthinking_cross_process_one_reservation(mongo_db,tmp_path,monkeypatch,ledger_adapter):
    import subprocess,sys
    c,dbs,accounts,contexts=old.ledger_case(mongo_db,tmp_path,monkeypatch)
    payload=dict(auth=c.auth,config=c.configs[0],context=contexts[0],manifest=c.manifest,ref=c.module.AUTHORIZED_GIT)
    p=tmp_path/'process.json';p.write_text(json.dumps(payload),encoding='utf-8')
    code="""import json,sys,os
from pathlib import Path
from pymongo import MongoClient
from app.infrastructure.providers import nonthinking_risk as r
from app.infrastructure.providers.output_contract import OutputLedger
p=Path(sys.argv[1]);v=json.loads(p.read_text('utf-8'));r.ROOT=p.parent;r.AUTHORIZED_GIT=v['ref']
r.evidence_bytes=lambda _:json.dumps(v['auth']).encode();r.prior_receipt=lambda:v['manifest']['prior_receipt']
r.code_version=lambda:v['config']['versions']['code'];r.authorized_inputs=lambda a,m:v['manifest']['entries'][0]['question']
r.validate_runtime=lambda *a:None
with MongoClient(os.environ['MONGO_URL'],serverSelectionTimeoutMS=5000) as client:
 a=OutputLedger(client[v['config']['target']['database']],v['config']['parameters']['answer_budget']['output_contract'])
 a.begin('r0','identity0',input_reservation=12,risk_context=v['context'])
"""
    processes=[subprocess.Popen([sys.executable,'-c',code,str(p)],stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(3)]
    statuses=[]
    for process in processes:process.communicate(timeout=45);statuses.append(process.returncode)
    assert sorted(statuses)==[0,1,1]
    assert accounts[0]._read()['logical_reservations']==1
