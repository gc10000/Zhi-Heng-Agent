"""默认关闭组合的正式job/adapter同库、分库及崩溃恢复矩阵；只有合成模型。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_split_ledger import formal_case
from app.knowledge.repository import fingerprint

pytestmark=pytest.mark.integration


def configure(ctx):
    from app.evaluation.corpus import corpus_snapshot
    from app.knowledge.models import content_hash
    from app.knowledge.index import V2Index
    from app.retrieval.combination import rows_digest,payload
    from app.retrieval.source_terms import collect_network_terms
    cfg,factory,resources,prompts,question,scoped=ctx;g=resources['knowledge']();t=cfg['target']
    entity=deepcopy(g.index_factory().search()[0]['entity']);pid=g.products.collection.find_one({})['product_id']
    entity.update(ordinal=0,text='Cable网络连接。额定电压24 V。')
    entity['metadata'].update(heading_path=['概述'],product_ids=[pid])
    row=entity|dict(owner_id=t['owner_id'],kb_id=t['kb_id'],content_sha256=content_hash(entity['text'].encode()),
        dense_vector=[1.,0.],sparse_vector={1:.5})
    class Index:
        collection=t['collection'];payload=staticmethod(V2Index.payload)
        def revision_rows(self,*a,**kw):return [deepcopy(row)]
        def search(self,*a,**kw):
            assert kw['branch_retention'] is True
            return [dict(entity=deepcopy(entity))]
        def prerequisite_rows(self,*a,**kw):return [deepcopy(row)]
    g.index_factory=Index
    original=b'synthetic original for combination integration'
    original_sha=content_hash(original);g.originals=SimpleNamespace(read=lambda rev:original)
    scoped.revisions.update_one({'revision_id':entity['revision_id']},{'$set':{'original_sha256':original_sha}})
    cfg['corpus']['documents'][0]['original_sha256']=original_sha
    snapshot=corpus_snapshot(g,t,cfg['corpus']['documents']);cfg['corpus']['snapshot']=snapshot
    scope={k:t[k] for k in ('owner_id','kb_id','database','collection')}
    scope.update(revisions={entity['document_id']:entity['revision_id']},product_ids=[pid])
    combo=payload(dict(enabled=True,scope=scope,corpus_snapshot_sha256=fingerprint(snapshot),
        corpus_rows_sha256=rows_digest([row]),terms=collect_network_terms([row],revision_ids=[entity['revision_id']],product_ids=[pid]),
        reviewed_sources=[dict(document_id=entity['document_id'],revision_id=entity['revision_id'],chunk_uid=entity['chunk_uid'],
            row_sha256=rows_digest([row]),proof_sha256='b'*64)]))
    cfg.update(strategy='m4-configured',parameters=dict(retrieval_combination=combo,
        source_prerequisites=dict(enabled=True,scope=scope),retrieval=dict(exclude_image_descriptions=True,
        query_projection='scoped_subject_v1',comparison_context='scope_first_v1')))
    return combo


@pytest.mark.parametrize('separate',[False,True])
def test_formal_job_saves_full_identity_and_reconstructs_completed(evaluation_context,tmp_path,monkeypatch,separate):
    from app.evaluation.jobs import execute_job
    combo=configure(evaluation_context)
    cfg,resources,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch,separate=separate)
    for key in ['first','reuse']:
        job=service.create_experiment(user,data|dict(client_request_id=key))
        execute_job(repo,catalog,tmp_path/'out',job['experiment_id'])
        assert repo.get_experiment(user,job['experiment_id'])['state']=='completed'
        link=resources['db'].evaluation_execution_links.find_one({'experiment_id':job['experiment_id']})
        assert link['retrieval_combination']==combo and link['retrieval_combination_sha256']==fingerprint(combo)
        assert link['run_input_sha256'] and link['control_database']==repo.db.name
    checkpoint=resources['db'].evaluation_items.find_one({})
    assert checkpoint['retrieval_combination']==combo and checkpoint['retrieval_combination_sha256']==fingerprint(combo)
    assert resources['db'].runs.count_documents({})==1 and len(prompts)==1


@pytest.mark.parametrize('point',['before_create','after_create','after_link'])
def test_crash_before_completion_reuses_fixed_request(evaluation_context,tmp_path,monkeypatch,point):
    from app.evaluation.jobs import execute_job
    configure(evaluation_context)
    cfg,resources,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch)
    if point in {'before_create','after_create'}:
        original=resources['run_service'].create
        def crash(*a,**kw):
            if point=='after_create':original(*a,**kw)
            raise RuntimeError('合成创建窗口崩溃')
        monkeypatch.setattr(resources['run_service'],'create',crash)
    else:
        import app.evaluation.execution_links as links
        original=links.bind_execution
        def crash(*a,**kw):original(*a,**kw);raise RuntimeError('合成关联后崩溃')
        monkeypatch.setattr(links,'bind_execution',crash)
    first=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'first',first['experiment_id'])
    prior=list(resources['db'].runs.find({}));assert len(prior)==(0 if point=='before_create' else 1) and not prompts
    if point in {'before_create','after_create'}:monkeypatch.setattr(resources['run_service'],'create',original)
    else:monkeypatch.setattr(links,'bind_execution',original)
    # 正式恢复扫描保留未到期pending，随后同一配置请求继续，不手写state/lease。
    resources['commands'].recover()
    second=service.create_experiment(user,data|dict(client_request_id='resume'))
    execute_job(repo,catalog,tmp_path/'second',second['experiment_id'])
    assert repo.get_experiment(user,second['experiment_id'])['state']=='completed'
    assert resources['db'].runs.count_documents({})==1 and len(prompts)==1
    if prior:assert resources['db'].runs.find_one({})['run_id']==prior[0]['run_id']


def test_completed_input_drift_before_result_snapshot_is_rejected(evaluation_context,tmp_path,monkeypatch):
    from app.evaluation.jobs import execute_job
    configure(evaluation_context)
    cfg,resources,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch)
    original=resources['query_runner'].execute
    def exit_after_completion(rid):
        original(rid)
        raise RuntimeError('合成Run完成、实验结果发布前退出')
    monkeypatch.setattr(resources['query_runner'],'execute',exit_after_completion)
    first=service.create_experiment(user,data);execute_job(repo,catalog,tmp_path/'first',first['experiment_id'])
    row=resources['db'].runs.find_one({});assert row['state']=='completed' and len(prompts)==1
    resources['db'].runs.update_one({'run_id':row['run_id']},{'$set':{'retrieval_combination_sha256':'0'*64}})
    monkeypatch.setattr(resources['query_runner'],'execute',original)
    second=service.create_experiment(user,data|dict(client_request_id='reject'))
    execute_job(repo,catalog,tmp_path/'second',second['experiment_id'])
    assert repo.get_experiment(user,second['experiment_id'])['state']=='failed' and len(prompts)==1


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('drift',[False,True])
def test_explicit_continuation_preserves_policy_and_refuses_parent_drift(evaluation_context,tmp_path,monkeypatch,separate,drift):
    from datetime import datetime,timedelta,timezone
    from app.evaluation.jobs import execute_job
    from app.runs.query_runner import ExecutionStopped
    configure(evaluation_context)
    cfg,res,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch,separate=separate)
    runner=res['query_runner'];old_ranker=runner.ranker
    def stop(*a,**kw):raise ExecutionStopped()
    runner.ranker=stop
    parent=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'parent',parent['experiment_id'])
    run=res['db'].runs.find_one({});assert run['state']=='running' and not prompts
    res['commands'].clock=lambda:datetime.now(timezone.utc)+timedelta(hours=1)
    assert run['run_id'] in res['commands'].recover()
    if drift:res['db'].runs.update_one({'run_id':run['run_id']},{'$set':{'retrieval_combination_sha256':'0'*64}})
    failed=repo.get_experiment(user,parent['experiment_id']);runner.ranker=old_ranker
    child=service.create_experiment(user,data|dict(client_request_id='child',continuation=dict(
        source_experiment_id=failed['experiment_id'],source_attempt=failed['attempt'],
        source_version=failed['version'],reason='合成组合中断后的显式来源接续')))
    execute_job(repo,catalog,tmp_path/'child',child['experiment_id'])
    assert repo.get_experiment(user,child['experiment_id'])['state']==('failed' if drift else 'completed')
    assert res['db'].runs.count_documents({})==(1 if drift else 2)
    assert len(prompts)==(0 if drift else 1)


@pytest.mark.parametrize('drift',[False,True])
def test_saved_success_checkpoint_rechecks_combination_without_generation(evaluation_context,tmp_path,monkeypatch,drift):
    from datetime import datetime,timedelta,timezone
    from app.evaluation.jobs import execute_job
    import app.evaluation.repository as repository_module
    configure(evaluation_context)
    cfg,res,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch)
    original=repo.complete
    def exit_before_publish(*a,**kw):raise SystemExit('合成结果已存、发布前退出')
    monkeypatch.setattr(repo,'complete',exit_before_publish)
    job=service.create_experiment(user,data)
    with pytest.raises(SystemExit):execute_job(repo,catalog,tmp_path/'job',job['experiment_id'])
    row=res['db'].runs.find_one({});assert row['state']=='completed' and len(prompts)==1
    if drift:res['db'].runs.update_one({'run_id':row['run_id']},{'$set':{'retrieval_combination_sha256':'0'*64}})
    class Future(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.now(tz)+timedelta(hours=1)
    # 只推进合成控制账本的时钟，正式claim接管过期任务；不手写租约/state。
    monkeypatch.setattr(repository_module,'datetime',Future)
    monkeypatch.setattr(repo,'complete',original)
    execute_job(repo,catalog,tmp_path/'job',job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']==('failed' if drift else 'completed')
    assert len(prompts)==1 and res['db'].runs.count_documents({})==1
