"""离线测试默认禁止联网，外部能力必须由当前用例显式注入。"""
import copy
import os
import socket
import sys
from types import SimpleNamespace

import pytest


@pytest.fixture(autouse=True)
def offline_boundary(monkeypatch, request):
    # 显式命令授权独立M1测试库才允许真实集成；标记本身不开放网络。
    if request.node.get_closest_marker('integration') and os.getenv('M1_TEST_DB', '').startswith('m1_test_'):
        return
    import dotenv
    monkeypatch.setattr(dotenv, 'load_dotenv', lambda *a, **kw: False)
    for name in list(os.environ):
        if any(part in name for part in ('OPENAI', 'MONGO', 'MINIO', 'MILVUS', 'MCP_DASHSCOPE')):
            monkeypatch.delenv(name)
    for name, value in {'LOG_CONSOLE_ENABLE': 'False', 'LOG_FILE_ENABLE': 'False',
                        'LLM_DEFAULT_TEMPERATURE': '0.1', 'HF_HUB_OFFLINE': '1',
                        'TRANSFORMERS_OFFLINE': '1'}.items():
        monkeypatch.setenv(name, value)

    def forbidden(*args, **kwargs):
        raise AssertionError('离线测试禁止外部 IO；请在当前用例注入 fake 客户端')

    real_connect = socket.socket.connect
    fallback = getattr(socket, '_fallback_socketpair', None)
    def guarded_connect(sock, address):
        # Windows 标准库 socketpair 为 asyncio 内部自唤醒创建回环连接。
        # 仅认定直接调用者代码对象，不放行业务对回环数据库的连接。
        caller = sys._getframe(1).f_code
        if fallback and caller is fallback.__code__ and address[0] in ('127.0.0.1', '::1'):
            return real_connect(sock, address)
        return forbidden(sock, address)
    monkeypatch.setattr(socket.socket, 'connect', guarded_connect)
    monkeypatch.setattr(socket.socket, 'connect_ex', forbidden)
    monkeypatch.setattr(socket, 'create_connection', forbidden)
    monkeypatch.setattr(socket, 'getaddrinfo', forbidden)
    import grpc
    monkeypatch.setattr(grpc, 'insecure_channel', forbidden)
    monkeypatch.setattr(grpc, 'secure_channel', forbidden)
    # 阻止真实客户端构造；不替换业务模块，不跨用例保留 fake。
    import pymongo
    import minio
    import langchain_openai
    monkeypatch.setattr(pymongo, 'MongoClient', forbidden)
    monkeypatch.setattr(minio, 'Minio', forbidden)
    monkeypatch.setattr(langchain_openai, 'ChatOpenAI', forbidden)


class HistoryStore:
    def __init__(self):
        self.records = []
        self.last_sort = None
        self.chat_message = self

    def seed(self, records):
        self.records = copy.deepcopy(records)

    def find(self, query):
        store = self

        class Cursor:
            def __init__(self):
                self.rows = [copy.deepcopy(r) for r in store.records if all(r.get(k) == v for k, v in query.items())]

            def sort(self, keys, direction=None):
                keys = [(keys, direction)] if direction is not None else keys
                store.last_sort = keys
                for key, order in reversed(keys):
                    self.rows.sort(key=lambda row: row[key], reverse=order == -1)
                return self

            def limit(self, n):
                self.rows = self.rows[:n]
                return self

            def __iter__(self):
                return iter(self.rows)

        return Cursor()


@pytest.fixture
def history_store(monkeypatch):
    from app.clients import mongo_history_utils
    store = HistoryStore()
    monkeypatch.setattr(mongo_history_utils, 'get_history_mongo_tool', lambda: store)
    return store


@pytest.fixture
def answer_node(monkeypatch):
    from app.query_process.agent.nodes import node_answer_output as node
    saved = []
    monkeypatch.setattr(node, 'save_chat_message', lambda **kw: saved.append(kw))
    return SimpleNamespace(module=node, saved=saved)


@pytest.fixture
def session():
    from app.utils import sse_utils, task_utils
    sid = 'm0-unit-session'
    task_utils.clear_task(sid)
    q = sse_utils.create_sse_queue(sid)
    yield sid, q
    task_utils.clear_task(sid)
    sse_utils.remove_sse_queue(sid)
