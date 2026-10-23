"""新API生命周期、公开错误与旧入口边界；不连接真实服务。"""
from contextlib import asynccontextmanager
from types import SimpleNamespace
import importlib
import sys
import pytest
from fastapi.testclient import TestClient


def test_import_does_not_initialize_resources(monkeypatch):
    import pymongo
    monkeypatch.setattr(pymongo, 'MongoClient', lambda *a, **k: pytest.fail('导入不能创建客户端'))
    import app.main
    importlib.reload(app.main)
    assert 'app.query_process.agent.main_graph' not in sys.modules
    assert app.main.app is not None


def test_resources_acquired_and_closed_once_and_health_is_versioned():
    from app.main import create_app
    calls = []
    @asynccontextmanager
    async def resources(settings):
        calls.append('open')
        try:
            yield {'db': object()}
        finally:
            calls.append('close')
    app = create_app(settings=SimpleNamespace(), resource_factory=resources)
    with TestClient(app) as client:
        assert client.get('/api/v1/health').json() == {'ready': True, 'version': 'v1'}
        result = client.get('/query')
        assert result.status_code == 404
        assert result.json()['error']['code'] == 'http_error'
        assert result.json()['request_id'] == result.headers['X-Request-ID']
    assert calls == ['open', 'close'] and not app.state.ready


def test_startup_missing_config_reports_names_only(monkeypatch):
    from app.main import create_app
    from app.settings import ConfigurationError
    monkeypatch.delenv('M2_DB_NAME', raising=False)
    with pytest.raises(ConfigurationError, match='M2_DB_NAME'):
        with TestClient(create_app()):
            pytest.fail('缺配置不能就绪')


def test_validation_and_unexpected_errors_do_not_expose_inputs():
    from app.main import create_app
    @asynccontextmanager
    async def resources(settings):
        yield {}
    app = create_app(settings=SimpleNamespace(), resource_factory=resources)
    @app.get('/api/v1/probe')
    def probe(number: int):
        raise RuntimeError('private-server-secret')
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get('/api/v1/probe?number=private-password')
        assert response.status_code == 422 and 'private-password' not in response.text
        response = client.get('/api/v1/probe?number=1')
        assert response.status_code == 500 and 'private-server-secret' not in response.text
        assert response.json()['request_id']


def test_failed_resource_startup_closes_resources():
    from app.main import create_app
    closed = []
    @asynccontextmanager
    async def resources(settings):
        try:
            raise RuntimeError('合成启动失败')
            yield {}
        finally:
            closed.append(True)
    with pytest.raises(RuntimeError, match='合成启动失败'):
        with TestClient(create_app(settings=SimpleNamespace(), resource_factory=resources)):
            pass
    assert closed == [True]
