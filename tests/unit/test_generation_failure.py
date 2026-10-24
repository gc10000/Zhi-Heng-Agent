from types import SimpleNamespace
import pytest


def failing_llm(stream, fail_at_start=False):
    def chunks(prompt, **options):
        if not fail_at_start:
            yield SimpleNamespace(content='部分答案')
        raise TimeoutError('synthetic-provider-timeout')
    def invoke(prompt, **options):
        raise TimeoutError('synthetic-provider-timeout')
    return SimpleNamespace(stream=chunks, invoke=invoke)


@pytest.mark.parametrize('stream', [True, False])
def test_generation_failure_propagates_without_success_history(monkeypatch, answer_node, session, stream):
    node = answer_node.module
    sid, q = session
    monkeypatch.setattr(node, 'get_llm_client', lambda: failing_llm(stream))
    with pytest.raises(RuntimeError) as caught:
        node.node_answer_output({'session_id': sid, 'is_stream': stream})
    assert type(caught.value).__name__ == 'AnswerGenerationError'
    assert caught.value.partial_answer == ('部分答案' if stream else '')
    assert answer_node.saved == []
    assert all(m['event'] != 'final' for m in list(q.queue))


def test_client_initialization_failure_is_normalized(monkeypatch, answer_node, session):
    sid, _ = session
    def fail():
        raise ValueError('缺少合成配置')
    monkeypatch.setattr(answer_node.module, 'get_llm_client', fail)
    with pytest.raises(RuntimeError) as caught:
        answer_node.module.step_3_generate_response({'session_id': sid}, 'synthetic')
    assert type(caught.value).__name__ == 'AnswerGenerationError'
    assert caught.value.partial_answer == ''


def test_failure_before_first_delta_has_empty_partial(monkeypatch, answer_node, session):
    from app.answering.errors import AnswerGenerationError
    sid, q = session
    monkeypatch.setattr(answer_node.module, 'get_llm_client', lambda: failing_llm(True, True))
    with pytest.raises(AnswerGenerationError) as caught:
        answer_node.module.node_answer_output({'session_id': sid, 'is_stream': True})
    assert caught.value.partial_answer == ''
    assert not any(e['event'] in ('final', 'delta') for e in list(q.queue))
