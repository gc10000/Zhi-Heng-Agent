"""生命周期须驱动持久运行扫描，不能只返回pending。"""
import threading
from contextlib import asynccontextmanager
from fastapi.testclient import TestClient
from app.main import create_app
from app.settings import Settings


def test_lifespan_drives_query_dispatch_without_http_stream():
    called = threading.Event()
    class Runner:
        def scan(self):
            called.set()
        def close(self):
            pass
    @asynccontextmanager
    async def resources(settings):
        yield {'query_runner': Runner()}
    app = create_app(settings=Settings('unused', 'unused'), resource_factory=resources)
    with TestClient(app):
        assert called.wait(.5), 'pending运行没有后台执行调度'
