"""评测API必须基于登录身份隔离题集与任务，不接受任意本机路径。"""
from tests.contract.test_auth import auth_client, login
from contextlib import asynccontextmanager, contextmanager
from app.main import create_app
from app.settings import Settings
from tests.fakes.identity import IdentityStore
from app.identity.service import IdentityService


@contextmanager
def _maintainer_client():
    store = IdentityStore()
    service = IdentityService(store)
    service.add_user('maintainer', 'safe-test-password', role='maintainer', kb_ids=['kb'])
    class Evaluation:
        def list_sets(self, user, kb_id): return {'items': [], 'next_cursor': None}
        def list_experiments(self, user, kb_id): return {'items': [], 'next_cursor': None}
        def get_experiment(self, user, experiment_id): raise AssertionError('不存在的实验不应绕过授权')
        def create_experiment(self, user, data): return {'experiment_id': 'exp-1', 'state': 'pending'}
    @asynccontextmanager
    async def resources(settings):
        yield {'identity': service, 'evaluations': Evaluation()}
    app = create_app(settings=Settings('unused', 'm2_test_fake', ('http://testserver',), False), resource_factory=resources)
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        result = client.post('/api/v1/auth/login', headers={'Origin': 'http://testserver'},
                             json={'username': 'maintainer', 'password': 'safe-test-password'})
        yield client, result.json()['csrf_token']


def test_evaluation_sets_and_experiments_require_authentication(auth_client):
    client, _, _ = auth_client
    assert client.get('/api/v1/eval-sets?kb_id=kb').status_code == 401
    assert client.get('/api/v1/experiments?kb_id=kb').status_code == 401
    assert client.get('/api/v1/experiments/private-run').status_code == 401


def test_viewer_cannot_submit_experiment(auth_client):
    client, _, _ = auth_client
    login_result = login(client)
    headers = {'Origin': 'http://testserver', 'X-CSRF-Token': login_result.json()['csrf_token']}
    response = client.post('/api/v1/experiments', headers=headers, json={
        'kb_id': 'kb', 'eval_set_id': 'private-set', 'eval_set_version': 'v1',
        'config_id': 'reviewed-dev', 'client_request_id': 'request-1',
    })
    assert response.status_code == 403


def test_experiment_request_cannot_select_a_server_path_or_override_results(auth_client):
    client, store, _ = auth_client
    login_result = login(client)
    user = store.users['viewer']
    user['role'] = 'maintainer'
    headers = {'Origin': 'http://testserver', 'X-CSRF-Token': login_result.json()['csrf_token']}
    response = client.post('/api/v1/experiments', headers=headers, json={
        'kb_id': 'kb', 'eval_set_id': 'private-set', 'eval_set_version': 'v1',
        'config_id': 'reviewed-dev', 'client_request_id': 'request-1',
        'config_path': 'C:/private/eval.yaml', 'summary': {'recall': 1.0},
    })
    assert response.status_code == 422
    assert 'C:/private/eval.yaml' not in response.text


def test_celery_routes_evaluation_to_its_own_queue():
    from app.infrastructure.queue.celery_app import celery_app

    routes = celery_app.conf.task_routes or {}
    route = routes.get('evaluation.execute') if isinstance(routes, dict) else None
    assert isinstance(route, dict) and route.get('queue') == 'knowledge-evaluation'
    assert route['queue'] != celery_app.conf.task_default_queue


def test_evaluation_queue_cannot_be_configured_to_consume_import_budget(monkeypatch):
    import pytest
    from app.infrastructure.queue.celery_app import create_celery
    monkeypatch.setenv('M2_QUEUE_NAME', 'same-queue')
    monkeypatch.setenv('M6_QUEUE_NAME', 'same-queue')
    with pytest.raises(ValueError, match='M6_QUEUE_NAME'):
        create_celery()


def test_maintainer_can_list_and_create_without_client_supplied_result(client_data=None):
    with _maintainer_client() as (client, csrf):
        headers = {'Origin': 'http://testserver', 'X-CSRF-Token': csrf}
        assert client.get('/api/v1/eval-sets?kb_id=kb').status_code == 200
        assert client.get('/api/v1/experiments?kb_id=kb').status_code == 200
        response = client.post('/api/v1/experiments', headers=headers, json={
            'kb_id': 'kb', 'eval_set_id': 'private-set', 'eval_set_version': 'v1',
            'config_id': 'reviewed-dev', 'config_version': 'v1', 'client_request_id': 'request-1',
        })
        assert response.status_code == 202
        assert response.json()['state'] == 'pending'
