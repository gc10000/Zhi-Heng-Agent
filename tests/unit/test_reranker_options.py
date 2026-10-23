import sys
from types import SimpleNamespace


def test_configured_cpu_is_passed_to_sdk_devices(monkeypatch):
    from app.lm import reranker_utils
    calls = []
    def construct(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(options=kwargs)
    monkeypatch.setitem(sys.modules, 'FlagEmbedding', SimpleNamespace(FlagReranker=construct))
    monkeypatch.setattr(reranker_utils, '_reranker_model', None)
    monkeypatch.setattr(reranker_utils, 'reranker_config', SimpleNamespace(bge_reranker_large='local-model', bge_reranker_device='cpu', bge_reranker_fp16=False))
    first = reranker_utils.get_reranker_model()
    assert first.options['devices'] == 'cpu'
    assert 'device' not in first.options
    assert reranker_utils.get_reranker_model() is first
    assert len(calls) == 1
