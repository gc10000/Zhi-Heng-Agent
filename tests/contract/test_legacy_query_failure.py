from types import SimpleNamespace
import pytest


def install_graph(monkeypatch, answer_node, llm):
    from app.query_process.api import query_service as api
    monkeypatch.setattr(answer_node.module, 'get_llm_client', lambda: llm)
    monkeypatch.setattr(api, 'query_app', SimpleNamespace(invoke=answer_node.module.node_answer_output))
    return api


@pytest.mark.parametrize('stream', [True, False])
def test_partial_timeout_reaches_outer_failed_state(monkeypatch, answer_node, session, stream):
    from app.utils import task_utils
    sid, q = session
    def chunks(prompt):
        yield SimpleNamespace(content='部分答案')
        raise TimeoutError('synthetic')
    def invoke(prompt):
        raise TimeoutError('synthetic')
    api = install_graph(monkeypatch, answer_node, SimpleNamespace(stream=chunks, invoke=invoke))
    api.run_query_graph(sid, '合成问题', stream)
    assert task_utils.get_task_status(sid) == 'failed'
    assert task_utils.get_task_result(sid, 'partial_answer') == ('部分答案' if stream else '')
    assert task_utils.get_task_result(sid, 'answer') == ''
    assert answer_node.saved == []
    events = list(q.queue)
    assert not any(m['event'] == 'final' or m['data'].get('status') == 'completed' for m in events)
    if stream:
        assert len([m for m in events if m['event'] == 'error']) == 1


@pytest.mark.parametrize('stream', [True, False])
def test_success_has_one_terminal_and_one_saved_answer(monkeypatch, answer_node, session, stream):
    from app.utils import task_utils
    sid, q = session
    llm = SimpleNamespace(stream=lambda p: iter([SimpleNamespace(content='完'), SimpleNamespace(content='整')]), invoke=lambda p: SimpleNamespace(content='完整'))
    api = install_graph(monkeypatch, answer_node, llm)
    api.run_query_graph(sid, '问题', stream)
    assert task_utils.get_task_status(sid) == 'completed'
    assert task_utils.get_task_result(sid, 'answer') == '完整'
    assert [m['text'] for m in answer_node.saved] == ['完整']
    finals = [m for m in list(q.queue) if m['event'] == 'final']
    assert len(finals) == (1 if stream else 0)
    if finals:
        assert finals[0]['data']['status'] == 'completed'


def test_blocking_http_failure_is_not_success_response(monkeypatch, answer_node):
    from fastapi.testclient import TestClient
    def fail(prompt):
        raise TimeoutError('synthetic')
    api = install_graph(monkeypatch, answer_node, SimpleNamespace(invoke=fail))
    with TestClient(api.app) as client:
        response = client.post('/query', json={'query': '问题', 'session_id': 'm0-http-failure', 'is_stream': False})
    assert response.status_code == 502
    assert response.json()['status'] == 'failed'
    assert response.json()['answer'] == ''


def test_direct_graph_exception_and_retry_do_not_reuse_old_answer(monkeypatch, answer_node, session):
    from app.utils import task_utils
    sid, q = session
    api = install_graph(monkeypatch, answer_node, SimpleNamespace(invoke=lambda p: SimpleNamespace(content='旧答案')))
    api.run_query_graph(sid, '问题', False)
    def fail(state):
        raise TimeoutError('synthetic-graph')
    monkeypatch.setattr(api, 'query_app', SimpleNamespace(invoke=fail))
    api.run_query_graph(sid, '新问题', True)
    assert task_utils.get_task_status(sid) == 'failed'
    assert task_utils.get_task_result(sid, 'answer') == ''
    assert len([m for m in list(q.queue) if m['event'] == 'error']) == 1


def test_injected_typed_graph_failure_preserves_partial(monkeypatch, answer_node, session):
    from app.answering.errors import AnswerGenerationError
    from app.utils import task_utils
    sid, q = session
    api = install_graph(monkeypatch, answer_node, None)
    def fail(state):
        raise AnswerGenerationError(partial_answer='图级部分答案')
    monkeypatch.setattr(api, 'query_app', SimpleNamespace(invoke=fail))
    api.run_query_graph(sid, '问题', True)
    assert task_utils.get_task_status(sid) == 'failed'
    assert task_utils.get_task_result(sid, 'partial_answer') == '图级部分答案'
    assert all(e['event'] != 'final' for e in list(q.queue))


def test_blocking_http_success_is_compatible(monkeypatch, answer_node):
    from fastapi.testclient import TestClient
    api = install_graph(monkeypatch, answer_node, SimpleNamespace(invoke=lambda p: SimpleNamespace(content='完成答案')))
    with TestClient(api.app) as client:
        response = client.post('/query', json={'query': '问题', 'session_id': 'm0-http-success'})
    assert response.status_code == 200
    assert response.json()['answer'] == '完成答案'
    assert response.json()['status'] == 'completed'
