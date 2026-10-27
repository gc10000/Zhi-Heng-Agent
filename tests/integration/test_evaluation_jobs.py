"""独立Mongo验证评测预算、所有者和迟到工作代际；不调用模型。"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import pytest
from app.api.errors import APIError
from app.identity.models import Principal
from app.evaluation.repository import EvaluationRepository

pytestmark = pytest.mark.integration


def setup(repo, owner='one'):
    user = Principal(user_id=owner, username=owner, role='maintainer', kb_ids=('kb',))
    descriptor = dict(id='set', version='r1', kb_id='kb', dataset_sha256='a'*64,
        manifest_sha256='b'*64, question_count=50, dev_count=35, review_eligible_count=0,
        configs=[dict(id='dev', version='v1')])
    repo.register_set(user, descriptor)
    resolved = dict(config_sha256='c'*64, selected_questions=35, eligible_questions=0)
    data = dict(kb_id='kb', eval_set_id='set', eval_set_version='r1', config_id='dev',
                config_version='v1', client_request_id='request')
    return user, descriptor, resolved, data


def create(repo, owner='one'):
    user, descriptor, resolved, data = setup(repo, owner)
    return user, repo.create(user, data, descriptor=descriptor, resolved=resolved)


def test_private_sets_and_runs_do_not_leak_to_another_owner(mongo_db):
    repo = EvaluationRepository(mongo_db)
    owner, row = create(repo)
    other, _, _, _ = setup(repo, 'two')
    assert repo.list_experiments(other, 'kb')['items'] == []
    with pytest.raises(APIError) as error:
        repo.get_experiment(other, row['experiment_id'])
    assert error.value.status == 404
    assert repo.get_experiment(owner, row['experiment_id'])['owner_id'] == owner.user_id


def test_queue_budget_cannot_expire_while_pending_and_allow_second_job(mongo_db):
    repo = EvaluationRepository(mongo_db)
    user, row = create(repo)
    mongo_db.evaluation_slots.update_one({'_id': user.user_id}, {'$set': {
        'lease_until': datetime.now(timezone.utc)-timedelta(hours=1)}})
    _, descriptor, resolved, data = setup(repo)
    data['client_request_id'] = 'second'
    with pytest.raises(APIError) as error:
        repo.create(user, data, descriptor=descriptor, resolved=resolved)
    assert error.value.code == 'evaluation_queue_full'


def test_stale_worker_cannot_replace_visible_results_or_release_budget(mongo_db):
    repo = EvaluationRepository(mongo_db)
    user, row = create(repo)
    eid = row['experiment_id']
    old = repo.claim(eid)
    mongo_db.evaluation_experiments.update_one({'experiment_id': eid}, {'$set': {
        'lease_until': datetime.now(timezone.utc)-timedelta(seconds=1)}})
    current = repo.claim(eid)
    question = dict(id='q', category='parameter', question='合成问题')
    report = dict(status='completed', completed=1, failed=0)
    def finish(claim, answer):
        return repo.complete(eid, claim['attempt'], claim['worker_token'], report=report,
            questions=[question], results=[dict(id='q', status='completed', result=dict(answer=answer))])
    assert finish(current, '新答案') is not None
    assert finish(old, '旧答案') is None
    assert repo.results_page(eid)['items'][0]['result']['answer'] == '新答案'


def test_duplicate_requests_and_worker_claims_are_idempotent(mongo_db):
    repo = EvaluationRepository(mongo_db)
    user, descriptor, resolved, data = setup(repo)
    first = repo.create(user, data, descriptor=descriptor, resolved=resolved)
    assert repo.create(user, data, descriptor=descriptor, resolved=resolved) == first
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(repo.claim, [first['experiment_id']]*2))
    assert sum(row is not None for row in claims) == 1


def test_failed_retry_requires_version_and_reuses_identity(mongo_db):
    repo = EvaluationRepository(mongo_db)
    user, row = create(repo)
    claim = repo.claim(row['experiment_id'])
    failed = repo.fail(row['experiment_id'], claim['attempt'], claim['worker_token'],
                       error_code='upstream_timeout', retryable=True)
    with pytest.raises(APIError) as error:
        repo.retry(user, row['experiment_id'], failed['version']-1)
    assert error.value.code == 'version_conflict'
    retried = repo.retry(user, row['experiment_id'], failed['version'])
    assert retried['state'] == 'pending'
    assert retried['experiment_id'] == row['experiment_id']


def test_terminal_result_pagination_and_pending_cancel_release(mongo_db):
    repo = EvaluationRepository(mongo_db)
    user, row = create(repo)
    eid = row['experiment_id']
    cancelled = repo.cancel(user, eid, row['version'])
    assert cancelled['state'] == 'cancelled'
    assert repo.claim(eid) is None
    _, descriptor, resolved, data = setup(repo)
    data['client_request_id'] = 'second'
    second = repo.create(user, data, descriptor=descriptor, resolved=resolved)
    claim = repo.claim(second['experiment_id'])
    questions = [dict(id=f'q{i}', category='parameter', question='问题') for i in range(3)]
    results = [dict(id=q['id'], status='completed', result=dict(answer=q['id'])) for q in questions]
    repo.complete(second['experiment_id'], claim['attempt'], claim['worker_token'],
        report=dict(status='completed', completed=3, failed=0), questions=questions, results=results)
    page = repo.results_page(second['experiment_id'], limit=2)
    assert [r['question_id'] for r in page['items']] == ['q0', 'q1']
    assert repo.results_page(second['experiment_id'], cursor=page['next_cursor'])['items'][0]['question_id'] == 'q2'


def test_worker_runs_frozen_dev_only_and_reuses_completed_file_checkpoint(mongo_db, tmp_path, monkeypatch):
    import importlib.util
    assert importlib.util.find_spec('app.evaluation.jobs') is not None, '需要正式评测任务执行入口'
    from app.evaluation.jobs import execute_job
    from app.evaluation.catalog import EvaluationCatalog
    from app.evaluation.service import EvaluationService
    from tests.unit.test_evaluation_catalog import create_catalog
    _, catalog_file, _, _ = create_catalog(tmp_path)
    catalog = EvaluationCatalog(catalog_file)
    repo = EvaluationRepository(mongo_db)
    user = Principal(user_id='one', username='one', role='maintainer', kb_ids=('kb-test',))
    service = EvaluationService(repo, catalog)
    service.register_set(user, dict(kb_id='kb-test', eval_set_id='support-dev', version='r1'))
    data = dict(kb_id='kb-test', eval_set_id='support-dev', eval_set_version='r1',
                config_id='control', config_version='v1', client_request_id='dev-job')
    row = service.create_experiment(user, data)
    calls, retry_keys = [], []
    class Executor:
        def __init__(self, config): self.retry_key = None
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def __call__(self, question):
            calls.append(question['id'])
            retry_keys.append(self.retry_key)
            assert question['split'] == 'dev'
            return dict(answer='合成测试答案，不是真实生成', citations=[])
    monkeypatch.setattr('app.evaluation.query_adapter.RealQueryExecutor', Executor)
    execute_job(repo, catalog, tmp_path/'out', row['experiment_id'])
    result = service.get_experiment(user, row['experiment_id'])
    assert result['state'] == 'completed' and result['completed'] == 35
    assert len(calls) == 35
    assert set(retry_keys) == {f"dev-job:{row['experiment_id']}:1"}
    execute_job(repo, catalog, tmp_path/'out', row['experiment_id'])
    assert len(calls) == 35
    assert service.results_page(user, row['experiment_id'])['items'][0]['result']['answer'].startswith('合成测试')


def test_dispatch_failure_keeps_pending_intent(mongo_db):
    import importlib.util
    assert importlib.util.find_spec('app.evaluation.jobs') is not None, '需要持久派发入口'
    from app.evaluation.jobs import dispatch
    repo = EvaluationRepository(mongo_db)
    _, row = create(repo)
    def fail(eid): raise ConnectionError('测试broker不可达')
    with pytest.raises(ConnectionError): dispatch(repo, fail)
    assert repo.experiments.find_one({'experiment_id': row['experiment_id']})['dispatch_pending']
    sent = []
    assert dispatch(repo, sent.append) == 1
    assert sent == [row['experiment_id']]


def test_baseline_results_are_compared_by_question_identity(mongo_db):
    from app.evaluation.service import EvaluationService
    repo = EvaluationRepository(mongo_db)
    user, baseline = create(repo)
    question = dict(id='q', question='问题', category='parameter')
    def complete(row, answer):
        claim = repo.claim(row['experiment_id'])
        repo.complete(row['experiment_id'], claim['attempt'], claim['worker_token'],
            report=dict(status='completed', completed=1, failed=0), questions=[question],
            results=[dict(id='q', status='completed', result=dict(answer=answer, citations=[]))])
    complete(baseline, '旧答案')
    _, descriptor, resolved, data = setup(repo)
    data.update(client_request_id='comparison', baseline_experiment_id=baseline['experiment_id'])
    baseline = repo.get_experiment(user, baseline['experiment_id'])
    row = repo.create(user, data, descriptor=descriptor, resolved=resolved, baseline=baseline)
    complete(row, '新答案')
    result = EvaluationService(repo, None).results_page(user, row['experiment_id'])['items'][0]
    assert result['baseline']['answer'] == '旧答案'
    assert result['difference']['answer_changed'] is True


def test_expired_cancel_requested_worker_recovers_cancel_without_execution(mongo_db):
    repo = EvaluationRepository(mongo_db)
    user, row = create(repo)
    claim = repo.claim(row['experiment_id'])
    repo.cancel(user, row['experiment_id'], claim['version'])
    repo.experiments.update_one({'experiment_id': row['experiment_id']}, {'$set': {
        'lease_until': datetime.now(timezone.utc)-timedelta(seconds=1)}})
    current = repo.claim(row['experiment_id'])
    assert repo.cancel_requested(row['experiment_id'], current['attempt'], current['worker_token'])
    finished = repo.complete(row['experiment_id'], current['attempt'], current['worker_token'],
        report=dict(status='completed', completed=0, failed=0), questions=[], results=[])
    assert finished['state'] == 'cancelled'


def test_crash_between_budget_reservation_and_insert_recovers_after_reservation_deadline(mongo_db, monkeypatch):
    import app.evaluation.repository as module
    from uuid import uuid4
    repo = EvaluationRepository(mongo_db)
    user, descriptor, resolved, data = setup(repo)
    repo._reserve(user.user_id, str(uuid4()))  # 精确停在先占用、未写入任务的窗口。
    future = datetime.now(timezone.utc)+timedelta(minutes=2)
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None): return future
    monkeypatch.setattr(module, 'datetime', Clock)
    row = repo.create(user, data, descriptor=descriptor, resolved=resolved)
    assert row['state'] == 'pending'
    assert repo.claim(row['experiment_id']) is not None
