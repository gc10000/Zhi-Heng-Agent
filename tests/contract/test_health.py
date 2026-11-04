"""健康探针只检查依赖，不构造模型、泄漏配置或请求供应商。"""
from contextlib import asynccontextmanager
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import create_app


def client_for(checks):
    @asynccontextmanager
    async def resources(settings):
        yield {'readiness_checks': checks}
    return TestClient(create_app(settings=SimpleNamespace(), resource_factory=resources))


def test_live_never_checks_dependencies():
    def forbidden():
        raise AssertionError('live不能访问依赖')
    with client_for({'mongo': forbidden}) as client:
        assert client.get('/health/live').json() == {'live': True}


def test_ready_classifies_required_failure_and_redacts_exception():
    def broken():
        raise RuntimeError('mongodb://secret-user:secret-password@private-host')
    with client_for({'mongo': broken, 'minio': lambda: {'status': 'ok'}}) as client:
        response = client.get('/health/ready')
        assert response.status_code == 503
        assert response.json()['checks']['mongo'] == {'status': 'unavailable', 'required': True}
        assert 'secret-' not in response.text and 'private-host' not in response.text


def test_optional_tool_and_disabled_generation_do_not_block_ready():
    checks = {'mongo': lambda: {'status': 'ok'},
              'models': lambda: {'status': 'disabled', 'required': False},
              'tools': lambda: {'status': 'disabled', 'required': False}}
    with client_for(checks) as client:
        assert client.get('/health/ready').status_code == 200
        assert client.get('/health/ready').json()['ready'] is True


def test_readiness_reports_missing_configuration_separately():
    with client_for({'models': lambda: {'status': 'configuration_missing', 'required': True}}) as client:
        response = client.get('/health/ready')
        assert response.status_code == 503
        assert response.json()['checks']['models']['status'] == 'configuration_missing'


def test_preview_generation_guard_precedes_run_creation(monkeypatch):
    from app.runs.api import create_run
    from app.api.errors import APIError
    import pytest
    monkeypatch.setenv('M7_GENERATION_ENABLED', 'false')
    with pytest.raises(APIError) as error:
        create_run('unused', None, None, user=None)
    assert error.value.code == 'generation_disabled'
