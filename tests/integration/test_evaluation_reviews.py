"""真实隔离Mongo与HTTP；合成答案/审核身份不代表真实人工抽检。"""
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.evaluation.repository import EvaluationRepository
from app.evaluation.service import EvaluationService
from app.identity.models import Principal

pytestmark = pytest.mark.integration


@pytest.fixture
def review_client(m2_client):
    client, headers, resources = m2_client
    user = Principal(**client.get('/api/v1/me').json()['user'])
    resources['db'].users.update_one({'user_id': user.user_id}, {'$set': {'role': 'maintainer'}})
    repo = EvaluationRepository(resources['db'])
    resources['evaluations'] = EvaluationService(repo, None)
    def experiment(eid):
        repo.experiments.insert_one(dict(experiment_id=eid, owner_id=user.user_id, kb_id='k',
            client_request_id=eid, state='completed', result_attempt=1, selected_questions=1, dataset_sha256='a'*64,
            manifest_sha256='b'*64, created_at='2020-01-01T00:00:00+00:00'))
        repo.save_results(eid, 1, [dict(id='q1', category='parameter', question='合成测试')],
                          [dict(id='q1', status='completed', result=dict(answer='合成答案', citations=[]))])
    experiment('baseline')
    yield client, headers, repo, experiment


def subject(client, eid='baseline'):
    from app.knowledge.repository import fingerprint
    page = client.get(f'/api/v1/experiments/{eid}/results')
    assert page.status_code == 200
    return fingerprint(page.json()['items'][0])


def payload(sha, key='one', round=1, kind='human'):
    return dict(question_id='q1', subject_sha256=sha, client_request_id=key, round=round,
        reviewer_kind=kind, human_attested=kind == 'human', source_checked=True,
        scores=dict(factuality=2, citation_support=2, actionability=2, image_relevance='not_applicable'),
        critical_errors=[], rationale='合成测试已核对，不是真实人工记录。')


def post(client, headers, data, eid='baseline'):
    return client.post(f'/api/v1/experiments/{eid}/reviews', headers=headers, json=data)


def rounds(client, headers, eid='baseline'):
    sha = subject(client, eid)
    for n in (1, 2):
        assert post(client, headers, payload(sha, str(n), n), eid).status_code == 201


def test_persistent_rounds_bind_actual_answer_and_are_idempotent(review_client):
    client, headers, repo, _ = review_client
    data = payload(subject(client))
    assert client.get('/api/v1/experiments/baseline/reviews').status_code == 200
    first = post(client, headers, data)
    assert first.status_code == 201
    assert post(client, headers, data).json() == first.json()
    assert first.json()['reviewer_id'] == client.get('/api/v1/me').json()['user']['user_id']
    data['rationale'] = '同幂等键改变内容'
    assert post(client, headers, data).status_code == 409
    resources = client.app.state.resources
    resources['evaluations'] = EvaluationService(EvaluationRepository(repo.db), None)
    assert len(client.get('/api/v1/experiments/baseline/reviews').json()['items']) == 1


def test_stale_result_and_same_round_rewrite_rejected(review_client):
    client, headers, repo, _ = review_client
    data = payload(subject(client))
    assert post(client, headers, data).status_code == 201
    data['client_request_id'] = 'rewrite'
    assert post(client, headers, data).status_code == 409
    repo.results.update_one({'experiment_id': 'baseline'}, {'$set': {'result.answer': '新答案'}})
    data.update(client_request_id='stale', round=2)
    assert post(client, headers, data).status_code == 409


def test_unknown_and_assistant_do_not_become_human_quality(review_client):
    client, headers, _, _ = review_client
    for n in (1, 2):
        data = payload(subject(client), str(n), n, 'assistant')
        assert post(client, headers, data).status_code == 201
    response = client.post('/api/v1/experiments/baseline/calibrations', headers=headers,
                           json=dict(client_request_id='cal', rationale='基线校准'))
    assert response.status_code == 409
    assert response.json()['error']['code'] == 'human_review_required'


def test_calibration_precedes_candidate_and_critical_errors_block(review_client):
    client, headers, repo, experiment = review_client
    rounds(client, headers)
    cal = client.post('/api/v1/experiments/baseline/calibrations', headers=headers,
                      json=dict(client_request_id='cal', rationale='固定基线，零非劣化容差'))
    assert cal.status_code == 201
    experiment('candidate')
    repo.experiments.update_one({'experiment_id': 'candidate'}, {'$set': {'created_at': '2099-01-01T00:00:00+00:00'}})
    for n in (1, 2):
        data = payload(subject(client, 'candidate'), 'candidate'+str(n), n)
        if n == 2:
            data['critical_errors'] = ['wrong_model']
        assert post(client, headers, data, 'candidate').status_code == 201
    gate = client.get('/api/v1/experiments/candidate/release-gate', params={'calibration_id': cal.json()['calibration_id']})
    assert gate.status_code == 200
    assert gate.json()['status'] == 'blocked'
    assert 'critical_error' in gate.json()['reasons']


@pytest.mark.parametrize('change', [dict(human_attested=False), dict(source_checked=False),
    dict(scores=dict(factuality=3)), dict(reviewer_id='impersonated')])
def test_review_input_cannot_forge_identity_or_unsupported_scores(review_client, change):
    client, headers, _, _ = review_client
    data = payload(subject(client)) | change
    assert post(client, headers, data).status_code == 422


def test_concurrent_same_round_only_one_record(review_client):
    client, headers, repo, _ = review_client
    sha = subject(client)
    user = Principal(**client.get('/api/v1/me').json()['user'])
    from app.evaluation.reviews import ReviewService, ReviewInput
    from app.api.errors import APIError
    service = ReviewService(repo)
    def save(n):
        try:
            service.submit(user, 'baseline', ReviewInput(**payload(sha, str(n))))
            return 201
        except APIError as exc:
            return exc.status
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save, (1, 2))) == [201, 409]
    assert repo.db.evaluation_reviews.count_documents({}) == 1


@pytest.mark.parametrize('mode,expected', [('pass', 'passed'), ('regress', 'blocked'),
    ('unknown', 'pending'), ('early', 'pending'), ('subset', 'pending'), ('changed', 'pending')])
def test_non_degradation_gate_and_missing_evidence(review_client, mode, expected):
    client, headers, repo, experiment = review_client
    rounds(client, headers)
    response = client.post('/api/v1/experiments/baseline/calibrations', headers=headers,
                          json=dict(client_request_id='cal', rationale='先校准再比较'))
    assert response.status_code == 201
    calibration = response.json()
    experiment('candidate')
    if mode != 'early':
        repo.experiments.update_one({'experiment_id':'candidate'}, {'$set':{'created_at':'2099-01-01T00:00:00+00:00'}})
    for n in (1, 2):
        data = payload(subject(client, 'candidate'), 'candidate'+str(n), n)
        if mode == 'unknown': data['scores']['factuality'] = 'unknown'
        if mode == 'regress': data['scores']['factuality'] = 1
        assert post(client, headers, data, 'candidate').status_code == 201
    if mode == 'subset':
        repo.experiments.update_one({'experiment_id':'candidate'}, {'$set':{'selected_questions':2}})
    if mode == 'changed':
        repo.results.update_one({'experiment_id':'baseline'}, {'$set':{'result.answer':'结果已变'}})
    gate = client.get('/api/v1/experiments/candidate/release-gate', params={'calibration_id':calibration['calibration_id']})
    assert gate.status_code == 200
    assert gate.json()['status'] == expected
    assert gate.json()['automatic_publish'] is False


def test_review_scope_csrf_and_full_result_fingerprint(review_client):
    client, headers, repo, _ = review_client
    data = payload(subject(client))
    assert client.post('/api/v1/experiments/baseline/reviews', json=data).status_code == 403
    repo.experiments.update_one({'experiment_id':'baseline'}, {'$set':{'owner_id':'other'}})
    assert post(client, headers, data).status_code == 404
    assert repo.db.evaluation_reviews.count_documents({}) == 0
