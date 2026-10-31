"""正式单题风险job的合成SDK流、固定槽与恢复，不证明产品质量。"""
import copy,json
from types import SimpleNamespace
import httpx,pytest
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_split_ledger import formal_case
from tests.unit.test_single_product_risk import make_risk_case

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('mode',['good','bad_usage','interrupted','snapshot_crash','before_slot','after_slot'])
def test_formal_single_product_path_is_bounded(evaluation_context,tmp_path,monkeypatch,separate,mode):
    from app.evaluation.jobs import execute_job
    from app.evaluation.query_adapter import RealQueryExecutor
    from app.evaluation.catalog import EvaluationCatalog
    from app.infrastructure.providers.diagnostic_usage import preserving_chat_class
    cfg,factory,res,prompts,question,_=evaluation_context
    runner=res['query_runner'];original=runner.evidence_prompt;captured=[]
    def capture(*a,**kw):
        state,prompt=original(*a,**kw);captured.append((copy.deepcopy(state),prompt));return state,prompt
    monkeypatch.setattr(runner,'evidence_prompt',capture)
    # 仅合成旧消费者输出，用它冻结夹具输入；不触及真实模型或真实产品。
    with RealQueryExecutor(cfg,resource_factory=factory) as e:e(question)
    state,prompt=captured[-1]
    (tmp_path/'formal').mkdir()
    cfg,res,prompts,q,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path/'formal',monkeypatch,separate=separate)
    expected=dict(prompt=prompt,context=state['prompt_used_docs'],groups=state.get('evidence_groups',[]),excluded=[],
        prompt_reference_map=state.get('prompt_reference_map',[]),budget=state['prompt_budget'])
    source=copy.deepcopy(cfg);source['strategy']='m4-configured'
    source['parameters']=dict(answer_budget=dict(context_window=32768,output_tokens=4096,reserve_tokens=256,max_chars=12000))
    c=make_risk_case(tmp_path/'risk',monkeypatch,source_config=source,question=q,expected=expected,control_database=repo.db.name)
    cfg.clear();cfg.update(c.config)
    (tmp_path/'formal/config.json').write_text(json.dumps(cfg),encoding='utf-8')
    sent=[]
    def handle(request):
        body=json.loads(request.content);sent.append(body)
        assert (c.module.slot_dir()/'started.json').is_file()
        assert body['n']==1 and body['max_completion_tokens']==4096 and 'max_tokens' not in body
        assert body['messages']==[dict(role='user',content=prompt)]
        if mode=='interrupted':raise httpx.ReadTimeout('合成中断')
        chunk=dict(id='synthetic',object='chat.completion.chunk',created=1,model='synthetic',
            choices=[dict(index=0,delta=dict(role='assistant',content='合成结果。[1]'),finish_reason='stop')],
            usage=dict(prompt_tokens=20,completion_tokens=8,total_tokens=28,
                completion_tokens_details={'reasoning_tokens':True if mode=='bad_usage' else 2}))
        return httpx.Response(200,headers={'content-type':'text/event-stream'},content='data: '+json.dumps(chunk)+'\n\ndata: [DONE]\n\n')
    with httpx.Client(transport=httpx.MockTransport(handle),follow_redirects=False) as transport:
        client=preserving_chat_class()(model='synthetic',base_url='https://synthetic.invalid/v1',api_key='synthetic-not-a-secret',
            n=1,stream_usage=True,max_retries=0,timeout=120,temperature=0.1,http_client=transport)
        runner.llm_factory=lambda:client
        if mode=='snapshot_crash':
            execute=runner.execute
            def crash(rid):execute(rid);raise RuntimeError('合成结果快照前中断')
            monkeypatch.setattr(runner,'execute',crash)
        if mode in ('before_slot','after_slot'):
            start=c.module.start
            def exit_at_slot(*a,**kw):
                if mode=='after_slot':start(*a,**kw)
                raise SystemExit('合成持久预留后退出')
            monkeypatch.setattr(c.module,'start',exit_at_slot)
        job=service.create_experiment(user,data)
        if mode in ('before_slot','after_slot'):
            with pytest.raises(SystemExit,match='合成持久预留后退出'):
                execute_job(repo,catalog,tmp_path/'out',job['experiment_id'])
            assert not sent
            from app.infrastructure.providers.output_contract import OutputLedger
            from app.api.errors import APIError
            account=OutputLedger(res['db'],c.policy)
            assert account._read()['state']=='pending' and account._read()['logical_reservations']==1
            assert (c.module.slot_dir()/'started.json').exists()==(mode=='after_slot')
            assert not (c.module.slot_dir()/'settled.json').exists()
            with pytest.raises(APIError):account.begin('another-run','another-input')
            return
        execute_job(repo,catalog,tmp_path/'out',job['experiment_id'])
        row=repo.get_experiment(user,job['experiment_id'])
        assert row['state']==('completed' if mode=='good' else 'failed')
        assert len(sent)==1
        account=res['db'].diagnostic_output_accounts.find_one({})
        assert account['state']==('blocked' if mode in ('bad_usage','interrupted') else 'open')
        assert account['prior_input_tokens']==10 and account['prior_output_tokens']==8
        assert (c.module.slot_dir()/'settled.json').exists()
        if mode=='snapshot_crash':
            monkeypatch.setattr(runner,'execute',execute)
            again=service.create_experiment(user,data|dict(client_request_id='readonly-recovery'))
            execute_job(repo,catalog,tmp_path/'recover',again['experiment_id'])
            assert repo.get_experiment(user,again['experiment_id'])['state']=='completed' and len(sent)==1
        # 换实验nonce仍只能观察旧Run，不能再次消费stream。
        replay=service.create_experiment(user,data|dict(client_request_id='another-nonce'))
        execute_job(repo,catalog,tmp_path/'replay',replay['experiment_id'])
        assert len(sent)==1
