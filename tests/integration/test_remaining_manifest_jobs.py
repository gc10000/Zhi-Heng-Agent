"""随机隔离库上的共享CAS、正式单题job、原始SDK流及恢复。无产品推理。"""
import copy
import json
from concurrent.futures import ThreadPoolExecutor
import httpx
import pytest
from app.api.errors import APIError
from tests.unit.test_remaining_manifest import make_remaining_case
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_split_ledger import formal_case

pytestmark=pytest.mark.integration


def ledger_case(mongo_db,tmp_path,monkeypatch):
    from app.infrastructure.providers.output_contract import OutputLedger
    c=make_remaining_case(tmp_path,monkeypatch,controls=[mongo_db.name,mongo_db.name+'_c2'],targets=[mongo_db.name+'_t1',mongo_db.name+'_t2'])
    monkeypatch.setattr(c.module,'validate_runtime',lambda *a:None) # 仅隔离原子账户；正式链路用后续未替换的用例验证。
    dbs=[mongo_db.client[cfg['target']['database']] for cfg in c.configs]
    accounts=[OutputLedger(db,p) for db,p in zip(dbs,c.policies)]
    for i,db in enumerate(dbs):db.runs.insert_one(dict(run_id='r'+str(i),identity='identity'+str(i)))
    contexts=[dict(config=cfg,question=q,control_database=control,execution=dict(experiment_id='exp'+str(i),attempt=1,config_sha256=c.fp(cfg))) for i,(cfg,q,control) in enumerate(zip(c.configs,c.questions,c.controls))]
    return c,dbs,accounts,contexts


def begin(a,ctx,i=0):a.begin('r'+str(i),'identity'+str(i),input_reservation=12,risk_context=ctx)
def settle(a,usage=None,completed=True,**kw):
    return a.settle('r0','identity0',usage or dict(input=5,output=6),completed=completed,
        product_state=dict(visible_body=True,truncated=False,finish_reason='stop')|kw,
        logical_calls=dict(invoke_started=0,stream_started=1))


def test_two_control_databases_share_atomic_inflight_and_prior_once(mongo_db,tmp_path,monkeypatch):
    c,dbs,accounts,contexts=ledger_case(mongo_db,tmp_path,monkeypatch)
    assert accounts[0].rows.full_name==accounts[1].rows.full_name
    with ThreadPoolExecutor(max_workers=3) as pool:
        def claim(_):
            try:begin(accounts[0],contexts[0]);return True
            except (APIError,FileExistsError):return False
        assert sum(pool.map(claim,range(3)))==1
    with pytest.raises(APIError):begin(accounts[1],contexts[1],1)
    s=settle(accounts[0]);assert s['state']=='awaiting_review'
    with pytest.raises(APIError):begin(accounts[1],contexts[1],1)
    accounts[0].review(accepted=True,evidence=dict(source_checked=True,input='synthetic',assertions=['来源一致']))
    begin(accounts[1],contexts[1],1)
    s=accounts[1]._read()
    assert (s['prior_input_tokens'],s['prior_output_tokens'])==(10,8)
    assert s['known_new_output_tokens']==6 and s['logical_reservations']==2


@pytest.mark.parametrize('fault',['before_slot','after_slot','before_settlement_file','after_review_file'])
def test_durable_crash_windows_never_regrant(mongo_db,tmp_path,monkeypatch,fault):
    c,dbs,accounts,contexts=ledger_case(mongo_db,tmp_path,monkeypatch);a=accounts[0]
    native=c.module.exclusive
    if fault=='before_slot':
        def crash(path,value):raise SystemExit('合成CAS后磁盘前退出')
        monkeypatch.setattr(c.module,'exclusive',crash)
        with pytest.raises(SystemExit):begin(a,contexts[0])
    else:
        begin(a,contexts[0])
        if fault=='after_slot':pass
        elif fault=='before_settlement_file':
            def crash(path,value):
                if path.name=='settled.json':raise SystemExit('合成结算DB提交后退出')
                return native(path,value)
            monkeypatch.setattr(c.module,'exclusive',crash)
            with pytest.raises(SystemExit):settle(a)
            monkeypatch.setattr(c.module,'exclusive',native)
            settle(a) # 只重放全等持久结算，无模型调用。
        elif fault=='after_review_file':
            settle(a);cas=a._cas
            monkeypatch.setattr(a,'_cas',lambda *x:(_ for _ in ()).throw(SystemExit('来源决定磁盘后退出')))
            with pytest.raises(SystemExit):a.review(accepted=True,evidence=dict(source_checked=True,assertions=['合成']))
            monkeypatch.setattr(a,'_cas',cas)
    with pytest.raises(APIError):begin(accounts[1],contexts[1],1)
    with pytest.raises(APIError):begin(a,contexts[0])
    assert a._read()['logical_reservations']==1


@pytest.mark.parametrize('bad',['missing','negative','boolean','conflicting','over','incomplete','empty','length','no_finish'])
def test_any_usage_or_completion_failure_blocks_both_databases(mongo_db,tmp_path,monkeypatch,bad):
    c,dbs,accounts,contexts=ledger_case(mongo_db,tmp_path,monkeypatch);a=accounts[0];begin(a,contexts[0])
    usage=dict(input=5,output=6);kw={};completed=True
    if bad=='missing':usage=dict(input=5)
    if bad=='negative':usage['output']=-1
    if bad=='boolean':usage['output']=True
    if bad=='conflicting':usage.update(completion_tokens=7)
    if bad=='over':usage['output']=4097
    if bad=='incomplete':completed=False
    if bad=='empty':kw['visible_body']=False
    if bad=='length':kw.update(truncated=True,finish_reason='length')
    if bad=='no_finish':kw['finish_reason']=None
    s=settle(a,usage,completed,**kw);assert s['state']=='blocked'
    with pytest.raises(ValueError):a.review(accepted=True,evidence=dict(source_checked=True,assertions=['不得放行']))
    with pytest.raises(APIError):begin(accounts[1],contexts[1],1)


def test_cumulative_budget_is_one_shared_total_across_control_databases(mongo_db,tmp_path,monkeypatch):
    c,dbs,accounts,contexts=ledger_case(mongo_db,tmp_path,monkeypatch);a=accounts[0]
    begin(a,contexts[0]);settle(a)
    a.review(accepted=True,evidence=dict(source_checked=True,assertions=['合成']))
    # 只在隔离故障库模拟累计已用，不改正式旧账本。
    a.rows.update_one({'_id':a.key},{'$set':{'known_new_output_tokens':212992-8-4095}})
    with pytest.raises(APIError):begin(accounts[1],contexts[1],1)


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('mode',['good','bad_usage','interrupted','length','empty','snapshot_crash','after_create','after_link','before_slot','after_slot'])
def test_formal_remaining_job_and_success_reuse(evaluation_context,tmp_path,monkeypatch,separate,mode):
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
    c=make_remaining_case(tmp_path/'risk',monkeypatch,configs=[source,source],questions=[q,q],expected=[expected,expected],controls=[repo.db.name,repo.db.name+'_c2'])
    cfg.clear();cfg.update(c.configs[0]);(tmp_path/'formal/config.json').write_text(json.dumps(cfg),encoding='utf-8')
    sent=[]
    def handle(req):
        body=json.loads(req.content);sent.append(body)
        assert body['n']==1 and body['max_completion_tokens']==4096 and 'max_tokens' not in body
        assert (c.module.slot_dir(c.policies[0])/'started.json').is_file()
        if mode=='interrupted':raise httpx.ReadTimeout('合成断流')
        chunk=dict(id='synthetic',object='chat.completion.chunk',created=1,model='synthetic',choices=[dict(index=0,
            delta=dict(role='assistant',content='' if mode=='empty' else '合成结果。[1]'),finish_reason='length' if mode=='length' else 'stop')],
            usage=dict(prompt_tokens=20,completion_tokens=8,total_tokens=28,completion_tokens_details=dict(reasoning_tokens=True if mode=='bad_usage' else 2)))
        return httpx.Response(200,headers={'content-type':'text/event-stream'},content='data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n')
    with httpx.Client(transport=httpx.MockTransport(handle),follow_redirects=False) as transport:
        client=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',n=1,stream_usage=True,max_retries=0,timeout=120,temperature=.1,http_client=transport)
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


def test_fixed_shared_account_is_exclusive_across_processes(mongo_db,tmp_path,monkeypatch):
    import subprocess,sys
    c,dbs,accounts,contexts=ledger_case(mongo_db,tmp_path,monkeypatch)
    payload=dict(auth=c.auth,config=c.configs[0],context=contexts[0],manifest=c.manifest,ref=c.module.AUTHORIZED_GIT)
    p=tmp_path/'process.json';p.write_text(json.dumps(payload),encoding='utf-8')
    code="""import json,sys,os
from pathlib import Path
from pymongo import MongoClient
from app.infrastructure.providers import remaining_risk as r
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


@pytest.mark.parametrize('separate',[False,True])
def test_formal_clarification_has_zero_generation_and_exact_candidates(evaluation_context,tmp_path,monkeypatch,separate):
    from app.evaluation.jobs import execute_job
    from app.infrastructure.providers.output_contract import OutputLedger
    from app.knowledge.api import ProductInput
    cfg,factory,res,prompts,q,_=evaluation_context
    q.update(product_names=[],history=[])
    g=res['knowledge']();g.add_product(__import__('app.identity.models',fromlist=['Principal']).Principal(
        user_id=cfg['target']['owner_id'],username='合成澄清',role='maintainer',kb_ids=(cfg['target']['kb_id'],)),cfg['target']['kb_id'],ProductInput(kb_id=cfg['target']['kb_id'],model='BX'))
    res['query_runner'].embedder=lambda texts:dict(dense=[[1.,0.] for _ in texts])
    (tmp_path/'formal').mkdir()
    cfg,res,prompts,q,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path/'formal',monkeypatch,separate=separate)
    products=list(g.products.collection.find({'owner_id':g.owner_id}))
    expected=dict(route='clarify',candidates=[{k:p[k] for k in ('product_id','model')} for p in products])
    source=copy.deepcopy(cfg);source['strategy']='m4-configured';source['parameters']=dict(answer_budget=dict(context_window=32768,output_tokens=4096,reserve_tokens=256,max_chars=12000))
    c=make_remaining_case(tmp_path/'risk',monkeypatch,configs=[source,source],questions=[q,q],expected=[expected,expected],controls=[repo.db.name,repo.db.name+'_c2'])
    cfg.clear();cfg.update(c.configs[0]);(tmp_path/'formal/config.json').write_text(json.dumps(cfg),encoding='utf-8')
    res['query_runner'].llm_factory=lambda:pytest.fail('澄清不能打开生成客户端')
    job=service.create_experiment(user,data);execute_job(repo,catalog,tmp_path/'out',job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']=='completed'
    a=OutputLedger(res['db'],c.policies[0]);s=a._read()
    assert s['logical_reservations']==0 and s['job_reservations']==1 and s['known_new_output_tokens']==0
    assert s['state']=='awaiting_review'
    a.review(accepted=True,evidence=dict(source_checked=True,candidates='exact',inference=0))
    replay=service.create_experiment(user,data|dict(client_request_id='zero-recovery'))
    execute_job(repo,catalog,tmp_path/'replay',replay['experiment_id'])
    assert repo.get_experiment(user,replay['experiment_id'])['state']=='completed'
    assert not prompts and a._read()['job_reservations']==1
