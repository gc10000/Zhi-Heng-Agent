"""正式纠错路径的合成Mongo验证；不是实际质量判断。"""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from app.api.errors import APIError
from app.evaluation.reviews import ReviewService, CalibrationInput
from tests.integration.test_evaluation_reviews import review_client
from tests.integration.test_policy_development import policy_rounds
from tests.integration.test_evaluation_run_adapter import evaluation_context

pytestmark = pytest.mark.integration
ARTIFACT = dict(commit='a'*40, path='docs/development/reviews/synthetic-audit.md', sha256='d'*64)


@pytest.fixture
def repair_context(review_client, monkeypatch):
    from app.evaluation.development_policy import DevelopmentPolicy
    client, headers, repo, factory = review_client
    owner = SimpleNamespace(user_id=client.get('/api/v1/me').json()['user']['user_id'], kb_ids=('k',), role='maintainer')
    controller = SimpleNamespace(user_id='synthetic-control', kb_ids=('k',), role='admin')
    policy = DevelopmentPolicy(repo)
    ref = policy.register(controller, 'k')
    repo.experiments.update_one({'experiment_id':'baseline'}, {'$set':{'quality_policy':ref}})
    def change(v, n):
        if n == 1:
            v['scores']['actionability'] = 'not_applicable'
            v['actionability_applicable'] = False
        v['scores']['factuality'] = 1 if n == 1 else 2
        return v
    policy, reviews, _, attestation, originals = policy_rounds(repo, owner, 'baseline', monkeypatch, change)
    sha = reviews._subjects(owner, 'baseline')[1]['q1'][0]
    request = dict(client_request_id='case-1', original_seal_ids=attestation['seal_ids'], artifact=ARTIFACT,
        targets=[dict(question_id='q1', subject_sha256=sha, replace_dimensions=['citation_support'],
            actionability_applicable=False, rationale='合成识别问题，无操作目标', correct_actionability_na=True)])
    return client, headers, repo, owner, controller, policy, reviews, ref, request, originals


def create_case(context):
    from app.evaluation.review_repairs import ReviewRepairs
    _, _, repo, _, controller, _, _, _, request, _ = context
    repairs = ReviewRepairs(repo)
    return repairs, repairs.register(controller, 'baseline', request)


def supplement(repairs, case, owner, *, score=1, critical=None, source_checked=True):
    seals = []
    for n in (1, 2):
        begin = dict(client_request_id=f'repair-{n}', round=n, execution_id=f'synthetic-repair-{n}',
            reviewer_model='synthetic-independent', source_manifest=[dict(source_id='synthetic-original', sha256='e'*64)])
        execution = repairs.begin(owner, 'baseline', case['id'], begin)
        assert repairs.begin(owner, 'baseline', case['id'], begin) == execution
        data = dict(judgments=[dict(question_id='q1', subject_sha256=case['scope']['subjects']['q1'],
            scores={'citation_support':score[n-1] if isinstance(score, tuple) else score}, dimension_evidence={'citation_support':'合成原件页1'},
            source_checked=source_checked, critical_errors=critical or [])])
        sealed = repairs.seal(owner, 'baseline', case['id'], execution['id'], data)
        assert repairs.seal(owner, 'baseline', case['id'], execution['id'], data) == sealed
        seals.append(sealed)
    return seals


def test_formal_append_only_correction_and_dimension_pair(repair_context):
    _, _, repo, owner, controller, policy, reviews, ref, request, originals = repair_context
    before = list(repo.db.evaluation_reviews.find({}))
    repairs, case = create_case(repair_context)
    assert repairs.register(controller, 'baseline', request) == case
    assert reviews._quality(owner, 'baseline')[1]['incomplete']
    with pytest.raises(APIError):
        policy.attest(controller, 'baseline', dict(seal_ids=request['original_seal_ids'], artifact=ARTIFACT))
    seals = supplement(repairs, case, owner)
    att = repairs.attest(controller, 'baseline', case['id'], dict(seal_ids=[s['id'] for s in seals], artifact=ARTIFACT))
    assert repairs.attest(controller, 'baseline', case['id'], dict(seal_ids=[s['id'] for s in seals], artifact=ARTIFACT)) == att
    quality = reviews._quality(owner, 'baseline')[1]
    assert not quality['incomplete'] and not quality['critical']
    assert quality['values']['q1'] == dict(factuality=1, citation_support=1, actionability=None, image_relevance=None)
    sources = quality['dimension_sources']['q1']
    assert {s['kind'] for s in sources['actionability']} == {'controller_rule_correction'}
    assert {s['kind'] for s in sources['citation_support']} == {'repair_review'}
    assert {s['review_id'] for s in sources['factuality']} == {r['review_id'] for r in originals}
    assert list(repo.db.evaluation_reviews.find({})) == before
    calibration = reviews.calibrate(owner, 'baseline', CalibrationInput(client_request_id='new-cal', rationale='合成', quality_policy=ref))
    assert calibration['baseline'] == quality
    assert reviews._quality(owner, 'baseline', human_only=True)[1]['incomplete']


@pytest.mark.parametrize('boundary', ['unknown', 'unchecked', 'critical', 'original_critical', 'scope', 'seal', 'execution', 'original', 'artifact'])
def test_repair_fail_closed_and_preserve_critical(repair_context, monkeypatch, boundary):
    _, _, repo, owner, controller, _, reviews, ref, request, _ = repair_context
    if boundary == 'original_critical':
        # 原critical在缺陷case快照前存在；即便替换该维度也不能抹去。
        # 另造合法原封存的测试在独立用例覆盖；这里检验篡改必被拒绝。
        repo.db.evaluation_reviews.update_one({}, {'$set':{'critical_errors':['wrong_object']}})
        with pytest.raises(APIError): create_case(repair_context)
        return
    repairs, case = create_case(repair_context)
    seals = supplement(repairs, case, owner, score='unknown' if boundary == 'unknown' else 1,
        critical=['wrong_object'] if boundary == 'critical' else None, source_checked=boundary!='unchecked')
    repairs.attest(controller, 'baseline', case['id'], dict(seal_ids=[s['id'] for s in seals], artifact=ARTIFACT))
    if boundary == 'scope': repo.results.update_one({}, {'$set':{'result.answer':'合成漂移'}})
    if boundary == 'seal': repo.db.evaluation_review_repair_seals.update_one({}, {'$set':{'judgments.0.scores.citation_support':2}})
    if boundary == 'execution': repo.db.evaluation_review_executions.update_one({'repair_case_id':case['id']}, {'$set':{'execution_id':'changed'}})
    if boundary == 'original': repo.db.evaluation_reviews.update_one({}, {'$set':{'scores.factuality':2}})
    if boundary == 'artifact':
        def reject(_): raise APIError(409, 'changed', '合成Git依据漂移')
        monkeypatch.setattr('app.evaluation.development_policy.verify_artifact', reject)
    with pytest.raises(APIError):
        reviews.calibrate(owner, 'baseline', CalibrationInput(client_request_id='cal', rationale='合成', quality_policy=ref))
    assert repo.db.evaluation_calibrations.count_documents({}) == 0


def test_repair_authorization_fixed_scope_idempotency_and_order(repair_context):
    _, _, repo, owner, controller, _, reviews, ref, request, _ = repair_context
    from app.evaluation.review_repairs import ReviewRepairs
    repairs = ReviewRepairs(repo)
    for user in (owner, SimpleNamespace(user_id='other', kb_ids=('other',), role='admin')):
        with pytest.raises(APIError): repairs.register(user, 'baseline', request)
    case = repairs.register(controller, 'baseline', request)
    changed = deepcopy(request); changed['targets'][0]['rationale'] = '不得借新请求换范围'
    with pytest.raises(APIError): repairs.register(controller, 'baseline', changed)
    begin = dict(client_request_id='begin', round=2, execution_id='second', reviewer_model='synthetic',
        source_manifest=[dict(source_id='page', sha256='e'*64)])
    with pytest.raises(APIError): repairs.begin(owner, 'baseline', case['id'], begin)
    begin['round'] = 1; begin['execution_id'] = 'synthetic-baseline-1'
    with pytest.raises(APIError): repairs.begin(owner, 'baseline', case['id'], begin)
    begin['execution_id'] = 'new-first'
    with ThreadPoolExecutor(max_workers=3) as pool:
        executions = list(pool.map(lambda _: repairs.begin(owner, 'baseline', case['id'], begin), range(3)))
    assert executions[0] == executions[1] == executions[2]
    bad = dict(judgments=[dict(question_id='q1', subject_sha256=case['scope']['subjects']['q1'], scores={'factuality':2},
        dimension_evidence={'factuality':'越界'}, source_checked=True, critical_errors=[])])
    with pytest.raises(APIError): repairs.seal(owner, 'baseline', case['id'], executions[0]['id'], bad)
    assert reviews._quality(owner, 'baseline')[1]['incomplete']


def test_repair_http_typed_contract(repair_context):
    client, headers, _, _, _, _, _, _, request, _ = repair_context
    assert client.post('/api/v1/experiments/baseline/review-repairs', headers=headers, json=request).status_code == 403
    assert client.post('/api/v1/experiments/baseline/review-repairs', headers=headers, json=request|{'passed':True}).status_code == 422


def test_rule_only_correction_needs_no_new_scores_and_cannot_change_calibration(repair_context):
    from app.evaluation.review_repairs import ReviewRepairs
    _, _, repo, owner, controller, _, reviews, ref, request, _ = repair_context
    request['targets'][0]['replace_dimensions'] = []
    repairs = ReviewRepairs(repo)
    case = repairs.register(controller, 'baseline', request)
    repairs.attest(controller, 'baseline', case['id'], dict(seal_ids=[], artifact=ARTIFACT))
    quality = reviews._quality(owner, 'baseline')[1]
    assert not quality['incomplete'] and quality['values']['q1']['actionability'] is None
    assert quality['values']['q1']['factuality'] == 1
    assert repo.db.evaluation_review_repair_seals.count_documents({}) == 0
    reviews.calibrate(owner, 'baseline', CalibrationInput(client_request_id='cal', rationale='合成', quality_policy=ref))
    assert repairs.register(controller, 'baseline', request) == case
    assert repairs.status(owner, 'baseline')['attestation']


def test_no_new_case_after_existing_valid_calibration(repair_context, monkeypatch):
    from app.evaluation.review_repairs import ReviewRepairs
    _, _, repo, owner, controller, policy, reviews, ref, request, _ = repair_context
    # 合法的新实验对作为已校准历史，不修改现有冲突记录。
    exp = repo.experiments.find_one({'experiment_id':'baseline'})
    new_exp = {k:v for k,v in exp.items() if k != '_id'}
    new_exp.update(experiment_id='valid-history', client_request_id='valid-history')
    repo.experiments.insert_one(new_exp)
    result = {k:v for k,v in repo.results.find_one({'experiment_id':'baseline'}).items() if k != '_id'}
    result['experiment_id'] = 'valid-history'; repo.results.insert_one(result)
    _, _, _, attest, _ = policy_rounds(repo, owner, 'valid-history', monkeypatch)
    calibration = reviews.calibrate(owner, 'valid-history', CalibrationInput(client_request_id='cal', rationale='合成', quality_policy=ref))
    request['original_seal_ids'] = attest['seal_ids']
    with pytest.raises(APIError): ReviewRepairs(repo).register(controller, 'valid-history', request)
    assert reviews._quality(owner, 'valid-history')[1] == calibration['baseline']


@pytest.mark.parametrize('point', ['case', 'seal', 'attest'])
def test_append_ack_loss_reuses_fixed_records(repair_context, monkeypatch, point):
    from app.evaluation.review_repairs import ReviewRepairs
    _, _, repo, owner, controller, _, reviews, _, request, _ = repair_context
    repairs = ReviewRepairs(repo)
    case = None if point == 'case' else repairs.register(controller, 'baseline', request)
    if point == 'seal':
        execution = repairs.begin(owner, 'baseline', case['id'], dict(client_request_id='first', round=1,
            execution_id='fresh', reviewer_model='synthetic', source_manifest=[dict(source_id='page', sha256='e'*64)]))
        operation = lambda: repairs.seal(owner, 'baseline', case['id'], execution['id'], dict(judgments=[dict(
            question_id='q1', subject_sha256=case['scope']['subjects']['q1'], scores={'citation_support':1},
            dimension_evidence={'citation_support':'合成依据'}, source_checked=True, critical_errors=[])]))
        collection = 'evaluation_review_repair_seals'
    elif point == 'attest':
        seals = supplement(repairs, case, owner)
        operation = lambda: repairs.attest(controller, 'baseline', case['id'], dict(seal_ids=[s['id'] for s in seals], artifact=ARTIFACT))
        collection = 'evaluation_review_repair_attestations'
    else:
        operation = lambda: repairs.register(controller, 'baseline', request)
        collection = 'evaluation_review_repairs'
    store = repairs.policy.store
    def ack_lost(*args, **kwargs):
        store(*args, **kwargs)
        raise SystemExit('合成写入后应答丢失')
    monkeypatch.setattr(repairs.policy, 'store', ack_lost)
    with pytest.raises(SystemExit): operation()
    saved = repairs.db[collection].find_one({})
    monkeypatch.setattr(repairs.policy, 'store', store)
    assert operation()['sha256'] == saved['sha256']
    assert repairs.db[collection].count_documents({}) == 1


def test_admin_cannot_be_the_replacement_reviewer_or_self_attest(repair_context):
    _, _, _, owner, controller, _, _, _, _, _ = repair_context
    repairs, case = create_case(repair_context)
    with pytest.raises(APIError): repairs.begin(controller, 'baseline', case['id'], dict(client_request_id='self', round=1,
        execution_id='self', reviewer_model='synthetic', source_manifest=[dict(source_id='page',sha256='e'*64)]))
    seals = supplement(repairs, case, owner)
    with pytest.raises(APIError): repairs.attest(SimpleNamespace(user_id=owner.user_id, kb_ids=owner.kb_ids, role='admin'),
        'baseline', case['id'], dict(seal_ids=[s['id'] for s in seals], artifact=ARTIFACT))
    status = repairs.status(owner, 'baseline')
    assert len(status['seals']) == 2 and 'judgments' not in str(status) and 'scores' not in str(status)


def test_repair_http_success_and_no_score_disclosure(repair_context):
    from app.identity.api import principal
    client, headers, repo, owner, controller, _, reviews, _, request, _ = repair_context
    app = client.app
    app.dependency_overrides[principal] = lambda: controller
    response = client.post('/api/v1/experiments/baseline/review-repairs', headers=headers, json=request)
    assert response.status_code == 201, response.text
    case = response.json()
    base = f"/api/v1/experiments/baseline/review-repairs/{case['id']}"
    for n in (1, 2):
        app.dependency_overrides[principal] = lambda: owner
        response = client.post(base+'/executions', headers=headers, json=dict(client_request_id=f'begin-{n}', round=n,
            execution_id=f'actual-synthetic-task-{n}', reviewer_model='synthetic',source_manifest=[dict(source_id='page',sha256='e'*64)]))
        assert response.status_code == 201, response.text
        execution = response.json()
        response = client.post(base+f"/executions/{execution['id']}/seal", headers=headers, json=dict(judgments=[dict(
            question_id='q1',subject_sha256=case['scope']['subjects']['q1'],scores={'citation_support':1},
            dimension_evidence={'citation_support':'合成物理页1'},source_checked=True,critical_errors=[])]))
        assert response.status_code == 201 and set(response.json()) == {'id','sha256','created_at'}
        status = client.get('/api/v1/experiments/baseline/review-repairs').json()
        assert 'judgments' not in str(status) and 'scores' not in str(status)
    app.dependency_overrides[principal] = lambda: controller
    response = client.post(base+'/independence',headers=headers,json=dict(seal_ids=[s['id'] for s in status['seals']],artifact=ARTIFACT))
    assert response.status_code == 201, response.text
    assert not reviews._quality(owner,'baseline')[1]['incomplete']
    app.dependency_overrides.clear()


def test_review_code_drift_blocks_new_work_but_preserves_sealed_history(repair_context, monkeypatch):
    _, _, _, owner, controller, _, reviews, _, _, _ = repair_context
    repairs, case = create_case(repair_context)
    seals = supplement(repairs, case, owner)
    repairs.attest(controller, 'baseline', case['id'], dict(seal_ids=[s['id'] for s in seals], artifact=ARTIFACT))
    quality = reviews._quality(owner,'baseline')[1]
    monkeypatch.setattr('app.evaluation.review_repairs.audit_code_identity',lambda:'e'*64)
    assert reviews._quality(owner,'baseline')[1] == quality
    with pytest.raises(APIError): repairs.begin(owner, 'baseline', case['id'], dict(client_request_id='changed', round=1,
        execution_id='new-code', reviewer_model='synthetic', source_manifest=[dict(source_id='page',sha256='e'*64)]))


def test_partial_replacement_cannot_skip_actual_answer_image(review_client, monkeypatch):
    from app.evaluation.development_policy import DevelopmentPolicy
    from app.evaluation.review_repairs import ReviewRepairs
    client, _, repo, _ = review_client
    owner = SimpleNamespace(user_id=client.get('/api/v1/me').json()['user']['user_id'],kb_ids=('k',),role='maintainer')
    controller = SimpleNamespace(user_id='synthetic-control',kb_ids=('k',),role='admin')
    ref = DevelopmentPolicy(repo).register(controller,'k')
    repo.experiments.update_one({'experiment_id':'baseline'},{'$set':{'quality_policy':ref}})
    repo.results.update_one({'experiment_id':'baseline'},{'$set':{'result.answer':'![图](/api/v1/assets/diagram)'}})
    def image(v,n):v['scores']['image_relevance']=0;return v
    _, reviews, _, att, _ = policy_rounds(repo,owner,'baseline',monkeypatch,image)
    sha = reviews._subjects(owner,'baseline')[1]['q1'][0]
    repairs = ReviewRepairs(repo)
    case = repairs.register(controller,'baseline',dict(client_request_id='case',original_seal_ids=att['seal_ids'],artifact=ARTIFACT,
        targets=[dict(question_id='q1',subject_sha256=sha,replace_dimensions=['image_relevance'],rationale='合成图像补证')]))
    execution = repairs.begin(owner,'baseline',case['id'],dict(client_request_id='begin',round=1,execution_id='actual-image-review',
        reviewer_model='synthetic',source_manifest=[dict(source_id='page',sha256='e'*64)]))
    data = dict(judgments=[dict(question_id='q1',subject_sha256=sha,scores={'image_relevance':'not_applicable'},
        dimension_evidence={'image_relevance':'不允许跳过可见图'},source_checked=True,critical_errors=[])])
    with pytest.raises(APIError):repairs.seal(owner,'baseline',case['id'],execution['id'],data)
    data['judgments'][0]['scores']['image_relevance']=0
    assert repairs.seal(owner,'baseline',case['id'],execution['id'],data)['judgments'][0]['scores']['image_relevance']==0


def test_new_na_disagreement_remains_pending(repair_context):
    _, _, _, owner, controller, _, reviews, ref, _, _ = repair_context
    repairs, case = create_case(repair_context)
    seals = supplement(repairs, case, owner, score=('not_applicable', 2))
    repairs.attest(controller, 'baseline', case['id'], dict(seal_ids=[s['id'] for s in seals], artifact=ARTIFACT))
    assert reviews._quality(owner, 'baseline')[1]['incomplete'] == ['q1']
    with pytest.raises(APIError): reviews.calibrate(owner, 'baseline', CalibrationInput(client_request_id='cal', rationale='合成', quality_policy=ref))


def test_valid_original_critical_is_never_erased_by_replacement(repair_context, monkeypatch):
    from app.evaluation.review_repairs import ReviewRepairs
    _, _, repo, owner, controller, _, reviews, ref, _, _ = repair_context
    exp = {k:v for k,v in repo.experiments.find_one({'experiment_id':'baseline'}).items() if k != '_id'}
    exp.update(experiment_id='critical-history', client_request_id='critical-history'); repo.experiments.insert_one(exp)
    result = {k:v for k,v in repo.results.find_one({'experiment_id':'baseline'}).items() if k != '_id'}
    result['experiment_id'] = 'critical-history'; repo.results.insert_one(result)
    def critical(v, n): v['critical_errors'] = ['wrong_object']; return v
    _, _, _, att, _ = policy_rounds(repo, owner, 'critical-history', monkeypatch, critical)
    sha = reviews._subjects(owner, 'critical-history')[1]['q1'][0]
    repairs = ReviewRepairs(repo)
    case = repairs.register(controller, 'critical-history', dict(client_request_id='case', original_seal_ids=att['seal_ids'], artifact=ARTIFACT,
        targets=[dict(question_id='q1', subject_sha256=sha, replace_dimensions=[], correct_actionability_na=True,
            actionability_applicable=False, rationale='合成题意规则')]))
    repairs.attest(controller, 'critical-history', case['id'], dict(seal_ids=[], artifact=ARTIFACT))
    assert reviews._quality(owner, 'critical-history')[1]['critical'] == ['q1']
    with pytest.raises(APIError): reviews.calibrate(owner, 'critical-history', CalibrationInput(client_request_id='cal', rationale='合成', quality_policy=ref))


@pytest.mark.parametrize('separate', [False, True])
def test_repaired_baseline_new_code_candidate_and_formal_proof(evaluation_context, tmp_path, monkeypatch, separate):
    """只改审核源码不重生成基线；候选新配置仍走登记题集与正式校准。"""
    import json
    from app.evaluation.catalog import EvaluationCatalog
    from app.evaluation.development_policy import DevelopmentPolicy
    from app.evaluation.review_repairs import ReviewRepairs
    from app.evaluation.jobs import execute_job
    from tests.integration.test_regression_formal_execution import setup_lineage
    cfg, resources, prompts, _, repo, service, owner, data, catalog, ledger, binding = setup_lineage(
        evaluation_context, tmp_path, monkeypatch, separate)
    resources['query_runner'].embedder = lambda texts: dict(dense=[[1.,0.] for _ in texts])
    controller = SimpleNamespace(user_id='synthetic-control', kb_ids=owner.kb_ids, role='admin')
    ref = DevelopmentPolicy(repo).register(controller, data['kb_id'])
    cfg['quality_policy'] = ref
    (tmp_path/'baseline-policy.json').write_text(json.dumps(cfg), encoding='utf8')
    entries = json.loads((tmp_path/'catalog.json').read_text('utf8'))
    entries['configs'].append(dict(id='baseline-policy', version='v1', path='baseline-policy.json'))
    (tmp_path/'catalog.json').write_text(json.dumps(entries), encoding='utf8')
    service.catalog = catalog = EvaluationCatalog(tmp_path/'catalog.json')
    request = data | dict(config_id='baseline-policy', config_version='v1', quality_policy=ref,
        regression_source=ledger.reference(binding), client_request_id='baseline')
    baseline = service.create_experiment(owner, request); eid = baseline['experiment_id']
    execute_job(repo, catalog, tmp_path/'jobs', eid)
    def change(v, n):
        if n == 1: v.update(actionability_applicable=False); v['scores']['actionability'] = 'not_applicable'
        return v
    _, reviews, _, att, _ = policy_rounds(repo, owner, eid, monkeypatch, change)
    sha = reviews._subjects(owner, eid)[1]['q1'][0]
    repairs = ReviewRepairs(repo)
    case = repairs.register(controller, eid, dict(client_request_id='case', original_seal_ids=att['seal_ids'], artifact=ARTIFACT,
        targets=[dict(question_id='q1', subject_sha256=sha, replace_dimensions=[], correct_actionability_na=True,
            actionability_applicable=False, rationale='合成识别题')]))
    repairs.attest(controller, eid, case['id'], dict(seal_ids=[], artifact=ARTIFACT))
    calibration = reviews.calibrate(owner, eid, CalibrationInput(client_request_id='cal', rationale='合成', quality_policy=ref))
    descriptor_before = deepcopy(repo.db.evaluation_sets.find_one({'version':data['eval_set_version']}))
    cfg2 = deepcopy(cfg); cfg2['versions']['code'] = 'new-review-code-identity'
    (tmp_path/'candidate-v2.json').write_text(json.dumps(cfg2), encoding='utf8')
    entries = json.loads((tmp_path/'catalog.json').read_text('utf8'))
    entries['configs'].append(dict(id='candidate', version='v2', path='candidate-v2.json'))
    (tmp_path/'catalog.json').write_text(json.dumps(entries), encoding='utf8')
    service.catalog = catalog = EvaluationCatalog(tmp_path/'catalog.json')
    candidate = service.create_experiment(owner, request | dict(client_request_id='candidate-v2', config_id='candidate', config_version='v2',
        baseline_experiment_id=eid, quality_calibration_id=calibration['calibration_id'], regression_calibration_id=calibration['calibration_id']))
    assert candidate['config_sha256'] != baseline['config_sha256']
    assert repo.db.evaluation_sets.find_one({'version':data['eval_set_version']}) == descriptor_before
    assert repo.get_experiment(owner, eid)['config_sha256'] == baseline['config_sha256']
    execute_job(repo, catalog, tmp_path/'jobs', candidate['experiment_id'])
    def candidate_rule(v, n):
        v.update(actionability_applicable=False); v['scores']['actionability'] = 'not_applicable'
        return v
    policy_rounds(repo, owner, candidate['experiment_id'], monkeypatch, candidate_rule)
    assert reviews.gate(owner, candidate['experiment_id'], calibration['calibration_id'])['status'] == 'passed'
    proof = ledger.proof(owner, ledger.reference(binding), candidate['experiment_id'], calibration['calibration_id'])
    assert proof['quality_policy'] == ref and proof['automatic_publish'] is False
    assert len(prompts) == 3
