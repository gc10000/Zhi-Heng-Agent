import importlib
import socket

import pytest


def test_unexpected_network_fails_explicitly():
    with pytest.raises(AssertionError, match='禁止外部 IO'):
        socket.create_connection(('example.invalid', 443))
    with socket.socket() as sock:
        with pytest.raises(AssertionError, match='禁止外部 IO'):
            sock.connect(('127.0.0.1', 27017))


def test_history_import_does_not_construct_client(monkeypatch):
    import pymongo
    from app.clients import mongo_history_utils
    calls = []
    monkeypatch.setattr(pymongo, 'MongoClient', lambda *a, **kw: calls.append(True))
    importlib.reload(mongo_history_utils)
    assert calls == []


def test_query_api_import_does_not_initialize_graph(monkeypatch):
    import sys
    from types import SimpleNamespace
    monkeypatch.setitem(sys.modules, 'app.query_process.agent.main_graph', SimpleNamespace(query_app=object()))
    from app.query_process.api import query_service
    importlib.reload(query_service)
    # 导入 API 不需要模型加载、图编译或外部仓储连接。
    assert query_service.query_app is None


def test_default_collection_excludes_manual_scripts():
    import tomllib
    from pathlib import Path
    cfg = tomllib.loads(Path('pyproject.toml').read_text(encoding='utf-8'))
    assert cfg['tool']['pytest']['ini_options']['testpaths'] == ['tests/unit', 'tests/contract']


def test_nodes_import_without_external_initialization():
    for name in ('app.query_process.agent.nodes.node_answer_output',
                 'app.query_process.agent.nodes.node_item_name_confirm',
                 'app.import_process.agent.nodes.node_document_split'):
        assert importlib.import_module(name)
    from app.lm import embedding_utils, reranker_utils
    assert embedding_utils._bge_m3_ef is None
    assert reranker_utils._reranker_model is None
