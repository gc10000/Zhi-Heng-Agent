"""浏览器身份契约：同源、防伪、会话撤销及功能授权。"""
from contextlib import asynccontextmanager
from types import SimpleNamespace
import pytest
from fastapi.testclient import TestClient
from app.main import create_app
from app.settings import Settings


@pytest.fixture
def auth_client():
    from datetime import datetime, timezone
    from app.identity.service import IdentityService
    from tests.fakes.identity import IdentityStore
    now = [datetime(2026, 10, 23, tzinfo=timezone.utc)]
    store = IdentityStore()
    service = IdentityService(store, session_seconds=60, clock=lambda: now[0])
    service.add_user('viewer', 'safe-test-password', role='viewer', kb_ids=['kb'])
    @asynccontextmanager
    async def resources(settings):
        yield {'identity': service}
    app = create_app(settings=Settings('unused', 'm2_test_fake', ('http://testserver',), False), resource_factory=resources)
    with TestClient(app) as client:
        yield client, store, now


def login(client, password='safe-test-password'):
    return client.post('/api/v1/auth/login', headers={'Origin': 'http://testserver'},
                       json={'username': 'viewer', 'password': password})


def test_login_rejects_foreign_or_missing_origin_before_credentials():
    @asynccontextmanager
    async def resources(settings):
        yield {'identity': SimpleNamespace(login=lambda *a: pytest.fail('错误来源不能校验密码'))}
    app = create_app(settings=Settings('unused', 'm2_test_fake', ('http://testserver',), False), resource_factory=resources)
    with TestClient(app) as client:
        for headers in ({}, {'Origin': 'https://evil.invalid'}, {'Origin': 'null'}):
            response = client.post('/api/v1/auth/login', headers=headers, json={'username': 'a', 'password': 'b'})
            assert response.status_code == 403
            assert response.json()['error']['code'] == 'origin_rejected'


def test_login_cookie_logout_and_session_revocation(auth_client):
    from app.identity.api import COOKIE
    client, store, now = auth_client
    assert client.get('/api/v1/me').status_code == 401
    result = login(client)
    assert result.status_code == 200
    assert 'httponly' in result.headers['set-cookie'].lower() and 'samesite=strict' in result.headers['set-cookie'].lower()
    assert 'password' not in result.text
    assert all(client.cookies[COOKIE] != key for key in store.sessions)
    assert client.get('/api/v1/me').json()['user']['role'] == 'viewer'
    assert client.post('/api/v1/auth/logout', headers={'Origin': 'http://testserver'}).status_code == 403
    token = client.cookies[COOKIE]
    headers = {'Origin': 'http://testserver', 'X-CSRF-Token': result.json()['csrf_token']}
    assert client.post('/api/v1/auth/logout', headers=headers).status_code == 200
    client.cookies.set(COOKIE, token)
    assert client.get('/api/v1/me').status_code == 401


def test_expiry_and_disabled_user_revoke_access(auth_client):
    from datetime import timedelta
    client, store, now = auth_client
    assert login(client).status_code == 200
    now[0] += timedelta(seconds=61)
    assert client.get('/api/v1/me').status_code == 401
    assert login(client).status_code == 200
    store.users['viewer']['enabled'] = False
    assert client.get('/api/v1/me').status_code == 401


def test_credentials_and_rate_limit_and_validation_do_not_leak(auth_client):
    client, store, now = auth_client
    for _ in range(10):
        result = login(client, 'wrong-secret-password')
        assert result.status_code == 401 and 'wrong-secret-password' not in result.text
    assert login(client).status_code == 429
    result = client.post('/api/v1/auth/login', headers={'Origin': 'http://testserver'},
                         json={'username': 'viewer', 'password': {'secret': 'private'}})
    assert result.status_code == 422 and 'private' not in result.text


def test_password_hash_and_role_scope_boundaries():
    from app.identity.service import hash_password, verify_password
    from app.identity.api import require_writer, require_kb
    from app.identity.models import Principal
    from app.api.errors import APIError
    first, second = hash_password('test-password-12'), hash_password('test-password-12')
    assert first != second and verify_password('test-password-12', first)
    assert not verify_password('wrong', first) and not verify_password('wrong', 'invalid')
    user = Principal(user_id='a', username='a', role='viewer', kb_ids=('k',))
    with pytest.raises(APIError) as denied:
        require_writer(user)
    assert denied.value.status == 403
    with pytest.raises(APIError) as missing:
        require_kb(user, 'other')
    assert missing.value.status == 404
