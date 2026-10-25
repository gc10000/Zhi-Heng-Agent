"""确认入口使用真实身份与输入契约，存储行为另由独立Mongo验证。"""
import pytest
from tests.contract.test_auth import auth_client, login


def test_case_commands_require_identity_before_storage(auth_client):
    client, _, _ = auth_client
    assert client.get('/api/v1/cases').status_code == 401
    assert client.post('/api/v1/cases', json={'run_id':'r','expected_support_version':0}).status_code == 401


@pytest.mark.parametrize('path,payload', [('/cases', {'run_id':'r','expected_support_version':-1}),
    ('/cases/c/confirm', {'expected_version':0,'owner_id':'foreign'}),
    ('/cases/c/confirm', {'expected_version':-1})])
def test_case_invalid_or_forged_fields_rejected_without_store(auth_client, path, payload):
    client, _, _ = auth_client
    result = login(client)
    headers = {'Origin':'http://testserver','X-CSRF-Token':result.json()['csrf_token']}
    assert client.post('/api/v1'+path, headers=headers, json=payload).status_code == 422


def test_case_write_requires_csrf(auth_client):
    client, _, _ = auth_client
    login(client)
    assert client.post('/api/v1/cases/c/confirm',headers={'Origin':'http://testserver'},json={'expected_version':0}).status_code == 403
