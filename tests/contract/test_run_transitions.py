"""运行命令共享认证，不允许迟到请求绕过状态判断。"""
from tests.contract.test_auth import auth_client
import pytest


def test_cancel_command_requires_authentication(auth_client):
    client, _, _ = auth_client
    assert client.post('/api/v1/runs/unknown/cancel', json={'expected_version': 0}).status_code == 401


@pytest.mark.parametrize('source,target', [('completed', 'running'), ('failed', 'pending'), ('cancelled', 'pending'),
    ('interrupted', 'running'), ('cancel_requested', 'completed'), ('awaiting_input', 'completed'), ('pending', 'awaiting_input')])
def test_illegal_transitions_cannot_revive_or_skip_stages(source, target):
    from app.runs.state_machine import check
    from app.api.errors import APIError
    with pytest.raises(APIError) as denied:
        check(source, target)
    assert denied.value.status == 409


@pytest.mark.parametrize('key', ['RUN_LEASE_SECONDS', 'RUN_INPUT_WAIT_SECONDS', 'RUN_PENDING_SECONDS'])
def test_run_timeouts_reject_nonpositive_configuration(monkeypatch, key):
    from app.settings import Settings, ConfigurationError
    monkeypatch.setenv('MONGO_URL', 'synthetic-url')
    monkeypatch.setenv('M2_DB_NAME', 'synthetic-db')
    monkeypatch.setenv(key, '0')
    with pytest.raises(ConfigurationError) as invalid:
        Settings.load()
    assert key in str(invalid.value) and 'synthetic-url' not in str(invalid.value)
