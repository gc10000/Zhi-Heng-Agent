"""助手政策端到端协议；所有审核、模型和来源均为合成，不是真实质量。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from app.api.errors import APIError
from app.evaluation.reviews import ReviewService,ReviewInput,CalibrationInput
from tests.integration.test_evaluation_reviews import review_client,payload
from tests.integration.test_evaluation_run_adapter import evaluation_context

pytestmark=pytest.mark.integration


def test_development_policy_registration_and_sealed_rounds(review_client,monkeypatch):
    from app.evaluation.development_policy import DevelopmentPolicy
    client,headers,repo,experiment=review_client
    owner=SimpleNamespace(user_id=client.get('/api/v1/me').json()['user']['user_id'],kb_ids=('k',),role='maintainer')
    control=SimpleNamespace(user_id='synthetic-control',kb_ids=('k',),role='admin')
    policy=DevelopmentPolicy(repo)
    reference=policy.register(control,'k')
    assert policy.register(control,'k')==reference
    repo.experiments.update_one({'experiment_id':'baseline'},{'$set':{'quality_policy':reference}})
    reviews=ReviewService(repo)
    _,subjects=reviews._subjects(owner,'baseline');sha=subjects['q1'][0]
    sealed=[]
    for round in (1,2):
        execution=policy.begin(owner,'baseline',dict(client_request_id='exec-'+str(round),round=round,
            execution_id='synthetic-review-'+str(round),reviewer_model='synthetic-auditor',
            source_manifest=[dict(source_id='synthetic-original-page',sha256='c'*64)]))
        values=payload(sha,key='review-'+str(round),round=round,kind='assistant') | dict(
            rubric_version='question-purpose-v1',actionability_applicable=True,applicability_rationale='合成操作题',
            quality_policy=reference,review_execution_id=execution['id'],
            dimension_evidence={d:'合成原件页及适用性依据' for d in ('factuality','citation_support','actionability','image_relevance')})
        row=policy.seal(owner,'baseline',execution['id'],[values])
        assert policy.seal(owner,'baseline',execution['id'],[values])==row
        sealed.append((execution,row,values))
        # 未有总控独立性核验时可保存真实assistant身份评分，但不能用于校准。
        reviews.submit(owner,'baseline',ReviewInput(**values))
        if round==1:
            assert reviews.list(owner,'baseline')['items']==[]
    assert len(reviews.list(owner,'baseline')['items'])==2
    with pytest.raises(APIError): reviews.calibrate(owner,'baseline',CalibrationInput(client_request_id='early',rationale='合成',quality_policy=reference))
    monkeypatch.setattr('app.evaluation.development_policy.verify_artifact',lambda _:None)
    artifact=dict(commit='a'*40,path='docs/development/reviews/synthetic-audit.md',sha256='d'*64)
    with pytest.raises(APIError):policy.attest(owner,'baseline',dict(seal_ids=[r['id'] for _,r,_ in sealed],artifact=artifact))
    attestation=policy.attest(control,'baseline',dict(seal_ids=[r['id'] for _,r,_ in sealed],artifact=artifact))
    assert policy.attest(control,'baseline',dict(seal_ids=[r['id'] for _,r,_ in sealed],artifact=artifact))==attestation
    _,quality=reviews._quality(owner,'baseline')
    assert not quality['incomplete'] and quality['policy']==reference
    assert len(quality['independence_attestations'])==1
    calibration=reviews.calibrate(owner,'baseline',CalibrationInput(client_request_id='calibration',rationale='合成政策校准',quality_policy=reference))
    assert calibration['quality_policy']==reference
    assert reviews._quality(owner,'baseline',human_only=True)[1]['incomplete']
    assert repo.db.evaluation_reviews.count_documents({'reviewer_kind':'human'})==0


def test_default_human_gate_does_not_accept_assistant_policy_implicitly(review_client):
    client,headers,repo,_=review_client
    owner=SimpleNamespace(user_id=client.get('/api/v1/me').json()['user']['user_id'],kb_ids=('k',))
    reviews=ReviewService(repo);_,subjects=reviews._subjects(owner,'baseline')
    for n in (1,2):reviews.submit(owner,'baseline',ReviewInput(**payload(subjects['q1'][0],str(n),n,'assistant')))
    assert reviews._quality(owner,'baseline')[1]['incomplete']


def policy_rounds(repo,user,eid,monkeypatch,overrides=None):
    from app.evaluation.development_policy import DevelopmentPolicy
    policy=DevelopmentPolicy(repo);reviews=ReviewService(repo)
    exp,subjects=reviews._subjects(user,eid)
    seals=[];saved=[]
    for n in (1,2):
        execution=policy.begin(user,eid,dict(client_request_id=f'{eid}-{n}',round=n,
            execution_id=f'synthetic-{eid}-{n}',reviewer_model='synthetic-independent-auditor',
            source_manifest=[dict(source_id='synthetic-page-1',sha256='c'*64)]))
        inputs=[]
        for qid,(sha,_) in subjects.items():
            values=payload(sha,key=f'{eid}-{qid}-{n}',round=n,kind='assistant')|dict(question_id=qid,
                quality_policy=exp['quality_policy'],review_execution_id=execution['id'],
                rubric_version='question-purpose-v1',actionability_applicable=True,applicability_rationale='合成操作题',
                dimension_evidence={d:'合成原件物理页1及维度证据' for d in ('factuality','citation_support','actionability','image_relevance')})
            if overrides: values=overrides(values,n)
            inputs.append(values)
        seals.append(policy.seal(user,eid,execution['id'],inputs))
        for v in inputs:saved.append(reviews.submit(user,eid,ReviewInput(**v)))
    controller=SimpleNamespace(user_id='synthetic-control',kb_ids=user.kb_ids,role='admin')
    monkeypatch.setattr('app.evaluation.development_policy.verify_artifact',lambda _:None)
    attestation=dict(seal_ids=[s['id'] for s in seals],artifact=dict(commit='a'*40,
        path='docs/development/reviews/synthetic-audit.md',sha256='d'*64))
    policy.attest(controller,eid,attestation)
    return policy,reviews,controller,attestation,saved


@pytest.mark.parametrize('separate',[False,True])
def test_policy_formal_feedback_chain(evaluation_context,tmp_path,monkeypatch,separate):
    import json
    from app.evaluation.development_policy import DevelopmentPolicy
    from app.evaluation.jobs import execute_job
    from tests.integration.test_regression_formal_execution import setup_lineage
    evaluation_context[2]['query_runner'].embedder=lambda texts:dict(dense=[[1.,0.] for _ in texts])
    cfg,res,prompts,_,repo,service,user,data,catalog,ledger,bound=setup_lineage(
        evaluation_context,tmp_path,monkeypatch,separate)
    reference=DevelopmentPolicy(repo).register(SimpleNamespace(user_id='synthetic-control',kb_ids=user.kb_ids,role='admin'),data['kb_id'])
    cfg['quality_policy']=reference
    (tmp_path/'policy-config.json').write_text(json.dumps(cfg),encoding='utf8')
    catalog_data=json.loads((tmp_path/'catalog.json').read_text(encoding='utf8'))
    catalog_data['configs'].append(dict(id='policy',version='v1',path='policy-config.json'))
    (tmp_path/'catalog.json').write_text(json.dumps(catalog_data),encoding='utf8')
    from app.evaluation.catalog import EvaluationCatalog
    catalog=EvaluationCatalog(tmp_path/'catalog.json')
    service.catalog=catalog
    request=data|dict(config_id='policy',config_version='v1',quality_policy=reference,
        regression_source=ledger.reference(bound),client_request_id='policy-baseline')
    baseline=service.create_experiment(user,request)
    execute_job(repo,catalog,tmp_path/'jobs',baseline['experiment_id'])
    assert repo.get_experiment(user,baseline['experiment_id'])['state']=='completed'
    with pytest.raises(APIError):service.create_experiment(user,request|dict(
        client_request_id='too-early',baseline_experiment_id=baseline['experiment_id']))
    policy,reviews,_,_,_=policy_rounds(repo,user,baseline['experiment_id'],monkeypatch)
    calibration=reviews.calibrate(user,baseline['experiment_id'],CalibrationInput(client_request_id='policy-cal',rationale='合成开发预校准',quality_policy=reference))
    candidate=service.create_experiment(user,request|dict(client_request_id='policy-candidate',
        baseline_experiment_id=baseline['experiment_id'],quality_calibration_id=calibration['calibration_id'],
        regression_calibration_id=calibration['calibration_id']))
    execute_job(repo,catalog,tmp_path/'jobs',candidate['experiment_id'])
    assert repo.get_experiment(user,candidate['experiment_id'])['state']=='completed'
    policy_rounds(repo,user,candidate['experiment_id'],monkeypatch)
    assert reviews.gate(user,candidate['experiment_id'],calibration['calibration_id'])['status']=='passed'
    assert reviews.gate(user,candidate['experiment_id'],calibration['calibration_id'],human_only=True)['status']=='pending'
    proof=ledger.proof(user,ledger.reference(bound),candidate['experiment_id'],calibration['calibration_id'])
    assert proof['quality_policy']==reference and proof['purpose']=='development_acceptance'
    assert ledger.proof(user,ledger.reference(bound),candidate['experiment_id'],calibration['calibration_id'])==proof
    links=list(res['db'].evaluation_execution_links.find({'quality_policy':reference}))
    assert len(links)==2 and len({l['run_id'] for l in links})==2
    assert len(prompts)==3 and repo.db.evaluation_reviews.count_documents({'reviewer_kind':'human'})==0
    repo.results.update_one({'experiment_id':candidate['experiment_id']},{'$set':{'result.answer':'合成漂移'}})
    with pytest.raises(APIError):ledger.proof(user,ledger.reference(bound),candidate['experiment_id'],calibration['calibration_id'])


@pytest.mark.parametrize('boundary',['unknown','unchecked','critical','low','drift','registry','timestamp','self_attest','resolution'])
def test_policy_quality_boundaries(review_client,monkeypatch,boundary):
    from app.evaluation.development_policy import DevelopmentPolicy
    client,_,repo,_=review_client
    owner=SimpleNamespace(user_id=client.get('/api/v1/me').json()['user']['user_id'],kb_ids=('k',),role='maintainer')
    ref=DevelopmentPolicy(repo).register(SimpleNamespace(user_id='synthetic-control',kb_ids=('k',),role='admin'),'k')
    repo.experiments.update_one({'experiment_id':'baseline'},{'$set':{'quality_policy':ref}})
    def change(v,n):
        if boundary in {'unknown','resolution'} and n==1:v['scores']['factuality']='unknown'
        if boundary=='critical':v['critical_errors']=['wrong_object']
        if boundary=='unchecked':v['source_checked']=False
        if boundary=='low' and n==2:v['scores']['factuality']=0
        return v
    policy,reviews,controller,attestation,saved=policy_rounds(repo,owner,'baseline',monkeypatch,change)
    if boundary=='self_attest':
        owner.role='admin'
        with pytest.raises(APIError):policy.attest(owner,'baseline',attestation)
        return
    if boundary=='drift':repo.results.update_one({'experiment_id':'baseline'},{'$set':{'result.answer':'合成漂移'}})
    if boundary=='registry':repo.db.evaluation_quality_policies.update_one({'_id':ref['id']},{'$set':{'purpose':'publication'}})
    if boundary=='timestamp':repo.db.evaluation_review_seals.update_one({'round':1},{'$set':{'created_at':'2000-01-01T00:00:00+00:00'}})
    if boundary in {'drift','registry','timestamp'}:
        with pytest.raises(APIError):reviews.calibrate(owner,'baseline',CalibrationInput(client_request_id='cal',rationale='合成',quality_policy=ref))
        return
    if boundary=='resolution':
        resolution=dict(client_request_id='resolve',resolutions=dict(factuality=dict(score=2,evidence='合成新原件物理页2')),
            source_manifest=[dict(source_id='synthetic-new-page-2',sha256='e'*64)])
        row=policy.resolve(owner,'baseline',saved[0]['review_id'],resolution)
        assert policy.resolve(owner,'baseline',saved[0]['review_id'],resolution)==row
        assert reviews._quality(owner,'baseline')[1]['incomplete']
        policy.attest(controller,'baseline',attestation)
        assert not reviews._quality(owner,'baseline')[1]['incomplete']
        assert repo.db.evaluation_reviews.find_one({'review_id':saved[0]['review_id']})['scores']['factuality']=='unknown'
    elif boundary in {'unknown','unchecked','critical'}:
        with pytest.raises(APIError):reviews.calibrate(owner,'baseline',CalibrationInput(client_request_id='cal',rationale='合成',quality_policy=ref))
    else:assert reviews._quality(owner,'baseline')[1]['values']['q1']['factuality']==0


def test_policy_blind_seal_rejection_matrix(review_client):
    from app.evaluation.development_policy import DevelopmentPolicy
    client,headers,repo,_=review_client
    owner=SimpleNamespace(user_id=client.get('/api/v1/me').json()['user']['user_id'],kb_ids=('k',),role='maintainer')
    policy=DevelopmentPolicy(repo)
    with pytest.raises(APIError):policy.register(owner,'k')
    ref=policy.register(SimpleNamespace(user_id='synthetic-control',kb_ids=('k',),role='admin'),'k')
    repo.experiments.update_one({'experiment_id':'baseline'},{'$set':{'quality_policy':ref,'quality_execution_key':'generator'}})
    begin=dict(client_request_id='begin',round=1,execution_id='generator',reviewer_model='synthetic',
        source_manifest=[dict(source_id='synthetic-page',sha256='c'*64)])
    for values in (begin,begin|dict(round=2,execution_id='second')):
        with pytest.raises(APIError):policy.begin(owner,'baseline',values)
    first=policy.begin(owner,'baseline',begin|dict(execution_id='first'))
    assert policy.begin(owner,'baseline',begin|dict(execution_id='first'))==first
    with pytest.raises(APIError):policy.seal(owner,'baseline',first['id'],[])
    assert client.get('/api/v1/experiments/baseline/reviews').json()['items']==[]
    assert client.get('/api/v1/experiments/baseline/observations').json()['items']==[]


def test_policy_http_schema_and_seal_contract(review_client,monkeypatch):
    client,headers,repo,_=review_client
    uid=client.get('/api/v1/me').json()['user']['user_id']
    assert client.post('/api/v1/evaluation-quality-policies/k',headers=headers).status_code==403
    repo.db.users.update_one({'user_id':uid},{'$set':{'role':'admin'}})
    response=client.post('/api/v1/evaluation-quality-policies/k',headers=headers)
    assert response.status_code==201
    reference=response.json()
    repo.experiments.update_one({'experiment_id':'baseline'},{'$set':{'quality_policy':reference}})
    user=SimpleNamespace(user_id=uid,kb_ids=('k',),role='admin')
    reviews=ReviewService(repo);_,subjects=reviews._subjects(user,'baseline')
    seals=[]
    for n in (1,2):
        begin=dict(client_request_id=f'http-{n}',round=n,execution_id=f'synthetic-http-{n}',
            reviewer_model='synthetic',source_manifest=[dict(source_id='synthetic-page-1',sha256='c'*64)])
        response=client.post('/api/v1/experiments/baseline/review-executions',headers=headers,json=begin)
        assert response.status_code==201,response.text
        execution=response.json()['id']
        data=payload(subjects['q1'][0],key=f'http-review-{n}',round=n,kind='assistant')|dict(
            quality_policy=reference,review_execution_id=execution,rubric_version='question-purpose-v1',
            actionability_applicable=True,applicability_rationale='合成操作目的',
            dimension_evidence={d:'合成原件页1' for d in ('factuality','citation_support','actionability','image_relevance')})
        assert client.post('/api/v1/experiments/baseline/reviews',headers=headers,json=data).status_code==409
        sealed=client.post(f'/api/v1/experiments/baseline/review-executions/{execution}/seal',headers=headers,json={'reviews':[data]})
        assert sealed.status_code==201,sealed.text
        assert set(sealed.json())=={'id','sha256','created_at'}
        seals.append(sealed.json()['id'])
        assert client.post('/api/v1/experiments/baseline/reviews',headers=headers,json=data).status_code==201
    # 当前审核账号即使是admin也不能自签独立性。
    response=client.post('/api/v1/experiments/baseline/review-independence',headers=headers,json=dict(
        seal_ids=seals,artifact=dict(commit='a'*40,path='docs/development/reviews/synthetic-audit.md',sha256='d'*64)))
    assert response.status_code==409
    assert client.post('/api/v1/experiments/baseline/calibrations',headers=headers,json=dict(
        client_request_id='http-early-cal',rationale='合成',quality_policy=reference)).status_code==409
    assert client.post('/api/v1/experiments/baseline/review-executions',headers=headers,json=begin|{'passed':True}).status_code==422


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('point',['before_outcome','after_results'])
def test_policy_formal_crash_recovery(evaluation_context,tmp_path,monkeypatch,separate,point):
    import json
    from datetime import datetime,timedelta,timezone
    from app.evaluation.development_policy import DevelopmentPolicy
    from app.evaluation.jobs import execute_job
    from tests.integration.test_evaluation_split_ledger import formal_case
    evaluation_context[2]['query_runner'].embedder=lambda texts:dict(dense=[[1.,0.] for _ in texts])
    cfg,res,prompts,_,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch,separate=separate)
    reference=DevelopmentPolicy(repo).register(SimpleNamespace(user_id='synthetic-control',kb_ids=user.kb_ids,role='admin'),data['kb_id'])
    cfg['quality_policy']=reference
    (tmp_path/'config.json').write_text(json.dumps(cfg),encoding='utf8')
    job=service.create_experiment(user,data|dict(quality_policy=reference))
    import app.evaluation.execution_identity as module
    owner=module if point=='before_outcome' else repo
    name='freeze_outcome' if point=='before_outcome' else 'complete'
    real=getattr(owner,name)
    def crash(*args,**kwargs):raise SystemExit('合成政策执行中断')
    monkeypatch.setattr(owner,name,crash)
    with pytest.raises(SystemExit):execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
    repo.experiments.update_one({'experiment_id':job['experiment_id']},{'$set':{'lease_until':datetime.now(timezone.utc)-timedelta(seconds=1)}})
    monkeypatch.setattr(owner,name,real)
    execute_job(repo,catalog,tmp_path/'jobs',job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']=='completed'
    assert len(prompts)==1 and res['db'].runs.count_documents({})==1
    links=list(res['db'].evaluation_execution_links.find({'quality_policy':reference}))
    assert len(links)==2 and links[0]['run_input_sha256']==links[1]['run_input_sha256']
