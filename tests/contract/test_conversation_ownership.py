"""会话HTTP契约：未登录和具体资源越权不能泄漏存在性。"""
from tests.contract.test_auth import auth_client, login


def test_conversation_requires_login(auth_client):
    client, _, _ = auth_client
    response = client.get('/api/v1/conversations')
    assert response.status_code == 401
