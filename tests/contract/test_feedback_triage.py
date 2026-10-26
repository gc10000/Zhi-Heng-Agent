from tests.contract.test_auth import auth_client, login


def test_feedback_queue_requires_maintainer_and_cannot_forge_owner(auth_client):
    client, store, _=auth_client
    assert client.get('/api/v1/feedback?kb_id=kb').status_code==401
    result=login(client)
    headers={'Origin':'http://testserver','X-CSRF-Token':result.json()['csrf_token']}
    assert client.get('/api/v1/feedback?kb_id=kb').status_code==403
    assert client.post('/api/v1/feedback/f/review',headers=headers,json=dict(
        expected_version=0,decision='reject',rationale='无效反馈',client_request_id='one',owner_id='foreign')).status_code==422
