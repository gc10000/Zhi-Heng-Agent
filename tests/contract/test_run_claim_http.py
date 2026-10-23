from tests.contract.test_auth import auth_client


def test_run_creation_is_authenticated(auth_client):
    client, _, _ = auth_client
    response = client.post('/api/v1/conversations/unknown/runs', json={'question': '参数', 'client_request_id': 'one', 'kb_id': 'kb'})
    assert response.status_code == 401
