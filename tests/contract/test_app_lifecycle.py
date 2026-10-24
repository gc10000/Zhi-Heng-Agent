"""新API生命周期、公开错误与旧入口边界；不连接真实服务。"""
from contextlib import asynccontextmanager
from types import SimpleNamespace
import importlib
import sys
import pytest
from fastapi.testclient import TestClient


def test_import_does_not_initialize_resources():
    # 旧图本身也有正式回归，已加载模块不能当作新API导入的副作用。
    # 在新进程保留原有两项断言，并禁止真实资源构造，避免依赖测试顺序。
    import subprocess
    code='''
import importlib, sys
import dotenv, pymongo
dotenv.load_dotenv=lambda *a, **kw: False
def forbidden(*a, **kw): raise AssertionError('导入不能创建客户端')
pymongo.MongoClient=forbidden
import app.main
importlib.reload(app.main)
assert 'app.query_process.agent.main_graph' not in sys.modules
assert app.main.app is not None
'''
    result=subprocess.run([sys.executable,'-c',code],capture_output=True,text=True,timeout=60)
    assert result.returncode==0, result.stderr


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
