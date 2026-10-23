import pytest


@pytest.mark.parametrize('limit', [0, -1, 'invalid'])
def test_history_invalid_limit_returns_422_without_store_access(monkeypatch, limit):
    from fastapi.testclient import TestClient
    from app.query_process.api import query_service as api
    accessed = []
    def unexpected(*args, **kwargs):
        accessed.append(True)
        return []
    monkeypatch.setattr(api, 'get_recent_messages', unexpected)
    with TestClient(api.app) as client:
        response = client.get(f'/history/m0-api?limit={limit}')
    assert response.status_code == 422
    assert accessed == []


def test_history_serializes_stable_window(history_store, monkeypatch):
    from fastapi.testclient import TestClient
    from app.query_process.api import query_service as api
    from app.clients.mongo_history_utils import get_recent_messages
    monkeypatch.setattr(api, 'get_recent_messages', get_recent_messages)
    history_store.seed([{'_id': i, 'session_id': 'm0-api', 'ts': i, 'role': 'user', 'text': str(i)} for i in range(1, 21)])
    with TestClient(api.app) as client:
        response = client.get('/history/m0-api?limit=10')
    assert response.status_code == 200
    assert [m['_id'] for m in response.json()['items']] == [str(i) for i in range(11, 21)]
