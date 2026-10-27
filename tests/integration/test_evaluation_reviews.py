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


def unknown_rounds(client, headers):
    """正式入口先保存两轮未知，不直接写入人工账本。"""
    originals = []
    for n in (1, 2):
        data = payload(subject(client), 'unknown-'+str(n), n)
        data['scores'].update(actionability='unknown', image_relevance='unknown')
        response = post(client, headers, data)
        assert response.status_code == 201
        originals.append(response.json())
    return originals


def followup_data(original, key='followup'):
    return dict(subject_sha256=original['subject_sha256'], client_request_id=key,
        human_attested=True, source_checked=True,
        resolutions=dict(actionability=dict(score='not_applicable', evidence='合成兼容性判断题，无操作目标或配置步骤，故步骤不适用。'),
                         image_relevance=dict(score=1, evidence='已对照原件与图片：示意连接关系，仅部分支持兼容性结论。')))


def followup(client, headers, original, data=None, eid='baseline'):
    return client.post(f"/api/v1/experiments/{eid}/reviews/{original['review_id']}/followups",
                       headers=headers, json=data or followup_data(original))


def test_review_image_requires_exact_result_source_and_authorized_revision(review_client):
    """审阅图片只能从当前题结果的精确来源读取，且不向客户端暴露对象键。"""
    from io import BytesIO
    from types import SimpleNamespace
    from PIL import Image
    from app.knowledge.gateway import KnowledgeGateway
    from app.knowledge.models import content_hash

    client, _, repo, _ = review_client
    resources = client.app.state.resources
    user = Principal(**client.get('/api/v1/me').json()['user'])

    output = BytesIO()
    Image.new('RGB', (12, 8), 'navy').save(output, format='PNG')
    image_bytes = output.getvalue()
    image_sha = content_hash(image_bytes)
    document_sha = 'd' * 64
    object_key = 'm6-review-image-private/isolated-topology.png'

    class ObjectResponse:
        def __init__(self, data): self.data = BytesIO(data)
        def read(self): return self.data.read()
        def close(self): self.data.close()
        def release_conn(self): pass

    class ObjectClient:
        def __init__(self): self.reads = []
        def get_object(self, bucket, key):
            self.reads.append((bucket, key))
            return ObjectResponse(image_bytes)

    object_client = ObjectClient()
    originals = SimpleNamespace(client=object_client, bucket='m6-test-images')
    gateway = KnowledgeGateway(repo.db, originals, owner_id='m6-review-image-owner')
    knowledge_repo = gateway.repo('k')
    document = knowledge_repo.register_document('review-image-doc', name='隔离图像手册.pdf')
    revision = knowledge_repo.create_revision(document.document_id, 'review-image-rev',
        original_sha256=document_sha, object_key='m6-test/original.pdf')
    repo.db.knowledge_assets.insert_one(dict(asset_id='m6-image-asset', document_id=document.document_id,
        revision_id=revision.revision_id, sha256=image_sha, object_key=object_key,
        media_type='image/png', source_refs=[{'page': 4, 'document_id': document.document_id,
                                              'revision_id': revision.revision_id}], kind='image'))
    resources['knowledge'] = lambda: gateway
    repo.results.update_one({'experiment_id': 'baseline', 'attempt': 1, 'question_id': 'q1'},
        {'$set': {'result.citations': [dict(document_sha256=document_sha, page=4, asset_sha256=image_sha)]}})

    base = f'/api/v1/experiments/baseline/results/q1/images/{document_sha}/4/'
    visible = client.get(base + image_sha)
    assert visible.status_code == 200, visible.text
    assert visible.content == image_bytes
    assert visible.headers['content-type'].startswith('image/png')
    assert visible.headers['cache-control'] == 'private, no-store'
    assert object_client.reads == [('m6-test-images', object_key)]
    repo.experiments.update_one({'experiment_id': 'baseline'}, {'$set': {'result_attempt': 2}})
    stale_attempt = client.get(base + image_sha)
    assert stale_attempt.status_code == 404
    assert object_client.reads == [('m6-test-images', object_key)]
    repo.experiments.update_one({'experiment_id': 'baseline'}, {'$set': {'result_attempt': 1}})

    # 同一账号若同时可访问两个知识库，结果也只能取实验绑定知识库中的资产。
    other_repo = gateway.repo('other-kb')
    other_document = other_repo.register_document('review-image-other-doc', name='其他库同哈希手册.pdf')
    other_revision = other_repo.create_revision(other_document.document_id, 'review-image-other-rev',
        original_sha256='e' * 64, object_key='m6-test/other-original.pdf')
    repo.db.knowledge_assets.insert_one(dict(asset_id='m6-image-other-kb', document_id=other_document.document_id,
        revision_id=other_revision.revision_id, sha256=image_sha,
        object_key='m6-review-image-private/other.png', media_type='image/png',
        source_refs=[{'page': 4, 'document_id': other_document.document_id,
                      'revision_id': other_revision.revision_id}], kind='image'))
    resources['identity'].store.users.update_one({'user_id': user.user_id}, {'$set': {'kb_ids': ['k', 'other-kb']}})
    repo.results.update_one({'experiment_id': 'baseline', 'attempt': 1, 'question_id': 'q1'},
        {'$set': {'result.citations': [dict(document_sha256='e' * 64, page=4, asset_sha256=image_sha)]}})
    other_scope = client.get(f'/api/v1/experiments/baseline/results/q1/images/{"e" * 64}/4/{image_sha}')
    assert other_scope.status_code == 404
    assert object_client.reads == [('m6-test-images', object_key)]

    resources['identity'].store.users.update_one({'user_id': user.user_id}, {'$set': {'kb_ids': ['k']}})
    repo.results.update_one({'experiment_id': 'baseline', 'attempt': 1, 'question_id': 'q1'},
        {'$set': {'result.citations': [dict(document_sha256=document_sha, page=4, asset_sha256=image_sha)]}})

    # 图片散列虽存在于知识库，若没有绑定到当前结果的精确来源，不能被该路由读取。
    assert client.get(base + 'e' * 64).status_code == 404
    assert client.get(f'/api/v1/experiments/baseline/results/q1/images/{document_sha}/5/{image_sha}').status_code == 404
    assert object_client.reads == [('m6-test-images', object_key)]

    # 撤销该账号的知识库授权后，历史结果不能绕过原件/修订权限读取图片。
    resources['identity'].store.users.update_one({'user_id': user.user_id}, {'$set': {'kb_ids': []}})
    denied = client.get(base + image_sha)
    assert denied.status_code == 404
    assert object_client.reads == [('m6-test-images', object_key)]


def test_unknown_followups_preserve_originals_and_unblock_calibration_after_both_rounds(review_client):
    client, headers, repo, _ = review_client
    originals = unknown_rounds(client, headers)
    before = list(repo.db.evaluation_reviews.find({}))
    cal = lambda: client.post('/api/v1/experiments/baseline/calibrations', headers=headers,
                              json=dict(client_request_id='cal-followup', rationale='合成门禁验证'))
    assert cal().status_code == 409
    for index, original in enumerate(originals):
        response = followup(client, headers, original, followup_data(original, 'fix-'+str(index)))
        assert response.status_code == 201, response.text
        assert response.json()['review_id'] == original['review_id']
        if index == 0:
            assert cal().status_code == 409
    result = cal()
    assert result.status_code == 201, result.text
    assert result.json()['baseline']['values']['q1']['actionability'] is None
    assert result.json()['baseline']['values']['q1']['image_relevance'] == 1
    assert list(repo.db.evaluation_reviews.find({})) == before
    listing = client.get('/api/v1/experiments/baseline/reviews').json()
    assert listing['items'] == originals
    assert len(listing['followups']) == 2
    assert all(r['scores']['actionability'] == 'unknown' for r in listing['items'])


def test_followup_idempotent_after_instance_rebuild_but_changed_request_or_second_writer_conflicts(review_client):
    client, headers, repo, _ = review_client
    original = unknown_rounds(client, headers)[0]
    data = followup_data(original)
    first = followup(client, headers, original, data)
    assert first.status_code == 201, first.text
    client.app.state.resources['evaluations'] = EvaluationService(EvaluationRepository(repo.db), None)
    assert followup(client, headers, original, data).json() == first.json()
    data['resolutions']['image_relevance']['score'] = 2
    assert followup(client, headers, original, data).status_code == 409
    data['client_request_id'] = 'other'
    assert followup(client, headers, original, data).status_code == 409
    assert repo.db.evaluation_review_followups.count_documents({}) == 1


@pytest.mark.parametrize('mode,status', [('stale',409),('other_actor',404),('other_experiment',404),
    ('assistant',409),('no_unknown',409),('known_dimension',422),('incomplete',422),
    ('image_na',422),('bad_score',422),('blank_evidence',422),('no_attest',422),('no_source',422)])
def test_followup_rejects_stale_identity_scope_and_invalid_judgments_without_writes(review_client, mode, status):
    client, headers, repo, experiment = review_client
    if mode in ('assistant','no_unknown'):
        data = payload(subject(client), kind='assistant' if mode=='assistant' else 'human')
        original = post(client, headers, data).json()
    else:
        original = unknown_rounds(client, headers)[0]
    data = followup_data(original)
    if mode == 'stale':
        repo.results.update_one({'experiment_id':'baseline'},{'$set':{'result.answer':'新结果'}})
    if mode == 'other_actor':
        repo.db.evaluation_reviews.update_one({'review_id':original['review_id']},{'$set':{'reviewer_id':'other'}})
    if mode == 'other_experiment': experiment('other')
    if mode == 'known_dimension': data['resolutions']['factuality'] = dict(score=2,evidence='不能改确定分数')
    if mode == 'incomplete': data['resolutions'].pop('image_relevance')
    if mode == 'image_na':
        repo.results.update_one({'experiment_id':'baseline'},{'$set':{'result.citations':[{'asset_sha256':'c'*64}]}})
        # 新来源指纹与原审阅一起绑定，单独验证配图不适用的业务拒绝。
        sha = subject(client)
        repo.db.evaluation_reviews.update_one({'review_id':original['review_id']},{'$set':{'subject_sha256':sha}})
        data['subject_sha256'] = sha
        data['resolutions']['image_relevance']['score'] = 'not_applicable'
    if mode == 'bad_score': data['resolutions']['actionability']['score'] = True
    if mode == 'blank_evidence': data['resolutions']['image_relevance']['evidence'] = ' '
    if mode == 'no_attest': data['human_attested'] = False
    if mode == 'no_source': data['source_checked'] = False
    response = followup(client, headers, original, data, eid='other' if mode=='other_experiment' else 'baseline')
    assert response.status_code == status, response.text
    assert repo.db.evaluation_review_followups.count_documents({}) == 0
    assert repo.db.evaluation_calibrations.count_documents({}) == 0


def test_concurrent_followups_have_one_immutable_winner(review_client):
    client, headers, repo, _ = review_client
    original = unknown_rounds(client, headers)[0]
    def save(n):
        return followup(client, headers, original, followup_data(original, 'race-'+str(n))).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(save,(1,2))) == [201,409]
    assert repo.db.evaluation_review_followups.count_documents({}) == 1


def test_followup_keeps_maintainer_permission_boundary(review_client):
    client, headers, repo, _ = review_client
    original = unknown_rounds(client, headers)[0]
    user_id = client.get('/api/v1/me').json()['user']['user_id']
    repo.db.users.update_one({'user_id':user_id},{'$set':{'role':'viewer'}})
    response = followup(client, headers, original)
    assert response.status_code == 403
    assert repo.db.evaluation_review_followups.count_documents({}) == 0


def test_quality_rechecks_persisted_followup_attestation_and_evidence(review_client):
    client, headers, repo, _ = review_client
    originals = unknown_rounds(client, headers)
    saved = [followup(client, headers, original, followup_data(original, 'audit-'+str(n)))
             for n, original in enumerate(originals)]
    assert all(row.status_code == 201 for row in saved)
    from app.evaluation.reviews import ReviewService
    user = Principal(**client.get('/api/v1/me').json()['user'])
    service = ReviewService(repo)
    assert service._quality(user,'baseline')[1]['incomplete'] == []
    repo.db.evaluation_review_followups.update_one({'followup_id':saved[0].json()['followup_id']},
        {'$set':{'source_checked':False}})
    assert service._quality(user,'baseline')[1]['incomplete'] == ['q1']


def test_followups_never_erase_critical_error_or_other_reviewers_unknown(review_client):
    client, headers, repo, _ = review_client
    originals = unknown_rounds(client, headers)
    for n, original in enumerate(originals):
        assert followup(client, headers, original, followup_data(original, 'fixed-'+str(n))).status_code == 201
    from app.evaluation.reviews import ReviewService
    user = Principal(**client.get('/api/v1/me').json()['user'])
    service = ReviewService(repo)
    repo.db.evaluation_reviews.update_one({'review_id':originals[0]['review_id']}, {'$set':{'critical_errors':['wrong_model']}})
    assert service._quality(user,'baseline')[1]['critical'] == ['q1']
    other = dict(repo.db.evaluation_reviews.find_one({'review_id':originals[0]['review_id']}))
    other.pop('_id'); other.update(review_id='different-reviewer',reviewer_id='other',owner_id='other',client_request_id='other',critical_errors=[])
    repo.db.evaluation_reviews.insert_one(other)
    assert service._quality(user,'baseline')[1]['incomplete'] == ['q1']


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
