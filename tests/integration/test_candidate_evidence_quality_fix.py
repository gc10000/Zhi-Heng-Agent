"""集中补修的正式路径；随机隔离Mongo与明确合成审核/模型，非真实质量。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from app.api.errors import APIError
from app.evaluation.reviews import DIMENSIONS
from app.evaluation.review_repairs import ReviewRepairs
from app.evaluation.development_policy import DevelopmentPolicy
from app.knowledge.repository import fingerprint
from tests.integration.test_evaluation_reviews import review_client
from tests.integration.test_policy_development import policy_rounds
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_split_ledger import formal_case
from tests.integration.test_combination_adapter import configure

pytestmark=pytest.mark.integration
ARTIFACT=dict(commit='a'*40,path='docs/development/reviews/synthetic-audit.md',sha256='d'*64)


@pytest.mark.parametrize('all_dimensions,old_checked,new_checked,critical,rule',[
    (True,False,True,False,False),(False,False,True,False,False),
    (True,True,False,False,False),(True,True,True,False,False),
    (True,False,True,True,False),(False,False,True,False,True),
])
def test_formal_effective_checks_selected_sources_without_rewriting_originals(review_client,monkeypatch,all_dimensions,old_checked,new_checked,critical,rule):
    client,_,repo,_=review_client
    owner=SimpleNamespace(user_id=client.get('/api/v1/me').json()['user']['user_id'],kb_ids=('k',),role='maintainer')
    controller=SimpleNamespace(user_id='synthetic-controller',kb_ids=('k',),role='admin')
    policy=DevelopmentPolicy(repo);ref=policy.register(controller,'k')
    repo.experiments.update_one({'experiment_id':'baseline'},{'$set':{'quality_policy':ref}})
    def change(v,n):
        v['source_checked']=old_checked
        if critical:v['critical_errors']=['wrong_object']
        return v
    policy,reviews,_,att,_=policy_rounds(repo,owner,'baseline',monkeypatch,change)
    originals=list(repo.db.evaluation_reviews.find({}));subject=reviews._subjects(owner,'baseline')[1]['q1'][0]
    dims=list(DIMENSIONS) if all_dimensions else [] if rule else ['citation_support']
    request=dict(client_request_id='repair',original_seal_ids=att['seal_ids'],artifact=ARTIFACT,targets=[dict(question_id='q1',
        subject_sha256=subject,replace_dimensions=dims,correct_actionability_na=rule,
        actionability_applicable=False if rule else True if all_dimensions else None,rationale='合成操作题' if not rule else '合成识别题')])
    repairs=ReviewRepairs(repo);case=repairs.register(controller,'baseline',request)
    assert repairs.register(controller,'baseline',request)==case
    seals=[]
    if dims:
        for n in (1,2):
            execution=repairs.begin(owner,'baseline',case['id'],dict(client_request_id=f'e{n}',round=n,execution_id=f'new-{n}',
                reviewer_model='synthetic',source_manifest=[dict(source_id='synthetic-original',sha256='e'*64)]))
            judgment=dict(question_id='q1',subject_sha256=subject,scores={d:('not_applicable' if d=='image_relevance' else 2) for d in dims},
                dimension_evidence={d:'合成原页已核' for d in dims},source_checked=new_checked,critical_errors=[])
            seal=repairs.seal(owner,'baseline',case['id'],execution['id'],dict(judgments=[judgment]));seals.append(seal)
            assert repairs.seal(owner,'baseline',case['id'],execution['id'],dict(judgments=[judgment]))==seal
    repairs.attest(controller,'baseline',case['id'],dict(seal_ids=[s['id'] for s in seals],artifact=ARTIFACT))
    projected,_=repairs.effective(owner,'baseline')
    assert all(r['source_checked']==(new_checked if all_dimensions else old_checked and (new_checked or rule)) for r in projected)
    assert all(r['critical_errors']==(['wrong_object'] if critical else []) for r in projected)
    assert list(repo.db.evaluation_reviews.find({}))==originals
    assert repo.db.evaluation_calibrations.count_documents({})==0


def attribution_config(ctx):
    configure(ctx)
    cfg=ctx[0];combo=cfg['parameters']['retrieval_combination'];snapshot=cfg['corpus']['snapshot']
    policy=dict(enabled=True,function_version='attributed_assertions_v1',scope=deepcopy(combo['scope']),
        corpus_snapshot_sha256=combo['corpus_snapshot_sha256'],
        documents=[{k:d[k] for k in ('document_id','revision_id','original_sha256')} for d in snapshot['documents']],
        products={p['product_id']:p['model'] for p in snapshot['products']})
    cfg['parameters']['evidence_attribution']=policy
    from app.answering.evidence_attribution import payload
    return payload(policy)


@pytest.mark.parametrize('separate',[False,True])
def test_formal_attribution_identity_checkpoint_completed_reuse(evaluation_context,tmp_path,monkeypatch,separate):
    from app.evaluation.jobs import execute_job
    attribution=attribution_config(evaluation_context)
    cfg,resources,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch,separate=separate)
    for key in ('first','reuse'):
        job=service.create_experiment(user,data|dict(client_request_id=key))
        execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
        assert repo.get_experiment(user,job['experiment_id'])['state']=='completed'
        link=resources['db'].evaluation_execution_links.find_one({'experiment_id':job['experiment_id']})
        assert link['evidence_attribution']==attribution
        result=repo.results.find_one({'experiment_id':job['experiment_id']})['result']
        assert result['state']=='completed'
    checkpoint=resources['db'].evaluation_items.find_one({})
    assert checkpoint['evidence_attribution']==attribution and checkpoint['evidence_attribution_sha256']==fingerprint(attribution)
    run=resources['db'].runs.find_one({});assert run['evidence_attribution']==attribution and run['prompt_reference_map'][0]['reference_number']==1
    assert len(prompts)==1 and 'attributed_assertions_v1' in prompts[0]


@pytest.mark.parametrize('boundary',['snapshot','product','source','hash'])
def test_attribution_drift_rejected_before_resources(evaluation_context,boundary):
    from app.evaluation.query_adapter import RealQueryExecutor
    attribution_config(evaluation_context);cfg=evaluation_context[0]
    p=cfg['parameters']['evidence_attribution']
    if boundary=='snapshot':p['corpus_snapshot_sha256']='0'*64
    if boundary=='product':p['products']={k:'changed' for k in p['products']}
    if boundary=='source':p['documents'][0]['revision_id']='changed'
    if boundary=='hash':p['documents'][0]['original_sha256']='0'*64
    with pytest.raises(ValueError):RealQueryExecutor(cfg,resource_factory=lambda _:pytest.fail('漂移不能装载资源'))


@pytest.mark.parametrize('point',['before_create','after_create','after_link'])
def test_attribution_create_windows_resume_same_run(evaluation_context,tmp_path,monkeypatch,point):
    from tests.integration import test_combination_adapter as prior
    monkeypatch.setattr(prior,'configure',attribution_config)
    prior.test_crash_before_completion_reuses_fixed_request(evaluation_context,tmp_path,monkeypatch,point)
    run=evaluation_context[2]['db'].runs.find_one({})
    assert run['evidence_attribution']['enabled'] and run['prompt_reference_map']


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('drift',[False,True])
def test_completed_attribution_input_rechecked_before_first_snapshot(evaluation_context,tmp_path,monkeypatch,separate,drift):
    from app.evaluation.jobs import execute_job
    attribution_config(evaluation_context)
    cfg,res,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch,separate=separate)
    execute=res['query_runner'].execute
    def crash(rid):
        execute(rid)
        raise RuntimeError('合成归属Run完成、首次快照前退出')
    monkeypatch.setattr(res['query_runner'],'execute',crash)
    first=service.create_experiment(user,data);execute_job(repo,catalog,tmp_path/'first',first['experiment_id'])
    row=res['db'].runs.find_one({});assert row['state']=='completed' and len(prompts)==1
    if drift:res['db'].runs.update_one({'run_id':row['run_id']},{'$set':{'evidence_attribution_sha256':'0'*64}})
    monkeypatch.setattr(res['query_runner'],'execute',execute)
    second=service.create_experiment(user,data|dict(client_request_id='resume'))
    execute_job(repo,catalog,tmp_path/'second',second['experiment_id'])
    assert repo.get_experiment(user,second['experiment_id'])['state']==('failed' if drift else 'completed')
    assert len(prompts)==1 and res['db'].runs.count_documents({})==1


@pytest.mark.parametrize('drift',[False,True])
def test_saved_attribution_checkpoint_rechecks_map_without_generation(evaluation_context,tmp_path,monkeypatch,drift):
    from datetime import datetime,timedelta
    import app.evaluation.repository as repository_module
    from app.evaluation.jobs import execute_job
    attribution_config(evaluation_context)
    cfg,res,prompts,question,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch)
    complete=repo.complete
    def crash(*a,**kw):raise SystemExit('合成归属结果已存、发布前退出')
    monkeypatch.setattr(repo,'complete',crash)
    job=service.create_experiment(user,data)
    with pytest.raises(SystemExit):execute_job(repo,catalog,tmp_path/'run',job['experiment_id'])
    row=res['db'].runs.find_one({});assert len(prompts)==1
    if drift:res['db'].runs.update_one({'run_id':row['run_id']},{'$set':{'prompt_reference_map.0.chunk_uid':'changed'}})
    class Future(datetime):
        @classmethod
        def now(cls,tz=None):return datetime.now(tz)+timedelta(hours=1)
    monkeypatch.setattr(repository_module,'datetime',Future)
    monkeypatch.setattr(repo,'complete',complete)
    execute_job(repo,catalog,tmp_path/'run',job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']==('failed' if drift else 'completed')
    assert len(prompts)==1
