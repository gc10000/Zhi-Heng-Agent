"""旧生成节点必须优先使用本轮sink，不依赖session全局队列。"""
from concurrent.futures import ThreadPoolExecutor
from contextvars import ContextVar
from types import SimpleNamespace


def test_old_generation_uses_bound_run_sink_instead_of_session_queue(monkeypatch):
    from app.utils import sse_utils as sse
    from app.query_process.agent.nodes import node_answer_output as node
    queue = sse.create_sse_queue('shared-session')
    calls = []
    # 先以现有生成行为建立反例，不将缺少新接口的ImportError当红测。
    class Model:
        def stream(self, prompt):
            yield SimpleNamespace(content=prompt)
    monkeypatch.setattr(node, 'get_llm_client', lambda: Model())
    binding = getattr(sse, 'run_event_sink', ContextVar('missing_sink', default=None))
    token = binding.set(lambda sid, kind, data: calls.append((sid, kind, data)))
    try:
        result = node.step_3_generate_response({'session_id': 'shared-session', 'is_stream': True}, '独立回答')
        assert result['answer'] == '独立回答'
        assert calls == [('shared-session', 'delta', {'delta': '独立回答'})]
        assert queue.empty()
    finally:
        binding.reset(token)
        sse.remove_sse_queue('shared-session')


def test_same_legacy_session_concurrent_runs_are_isolated(monkeypatch):
    from app.utils import sse_utils as sse
    from app.query_process.agent.nodes import node_answer_output as node
    class Model:
        def stream(self, prompt):
            for value in [prompt, '完成']:
                yield SimpleNamespace(content=value)
    monkeypatch.setattr(node, 'get_llm_client', lambda: Model())
    binding = getattr(sse, 'run_event_sink', ContextVar('missing_sink', default=None))
    def run(label):
        received = []
        token = binding.set(lambda sid, kind, data: received.append(data['delta']))
        try:
            node.step_3_generate_response({'session_id': 'same', 'is_stream': True}, label)
            return received
        finally:
            binding.reset(token)
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert list(pool.map(run, ['甲', '乙'])) == [['甲', '完成'], ['乙', '完成']]
