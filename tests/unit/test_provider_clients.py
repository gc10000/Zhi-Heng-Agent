"""客户端接线、部分流失败、缓存作用域及本机deadline，全部离线。"""
from types import SimpleNamespace
import httpx
import openai
import pytest
from app.infrastructure.providers.clients import PolicyChatClient, local_call
from app.infrastructure.providers.policy import ProviderPolicy, ProviderFailure
from tests.unit.test_llm_options import llm_options


def test_legacy_default_preserved_but_opt_in_passes_timeout_and_isolates_cache(llm_options, monkeypatch):
    lm, config, calls = llm_options
    legacy = lm.get_llm_client()
    assert 'timeout' not in calls[-1] and 'max_retries' not in calls[-1]
    monkeypatch.setenv('PROVIDER_POLICIES_ENABLED', 'true')
    monkeypatch.setenv('PROVIDER_TEXT_TIMEOUT_SECONDS', '17')
    monkeypatch.setenv('PROVIDER_TEXT_MAX_RETRIES', '0')
    active = lm.get_llm_client()
    assert active is not legacy and calls[-1]['timeout'] == 17 and calls[-1]['max_retries'] == 0
    assert calls[-1]['temperature'] == 0
    monkeypatch.setenv('PROVIDER_TEXT_TIMEOUT_SECONDS', '18')
    assert lm.get_llm_client() is not active and calls[-1]['timeout'] == 18


def test_text_question_does_not_require_vision_or_optional_tools(llm_options, monkeypatch):
    lm, config, calls = llm_options
    monkeypatch.setenv('PROVIDER_POLICIES_ENABLED', 'true')
    monkeypatch.setenv('PROVIDER_VISION_TIMEOUT_SECONDS', 'invalid-optional')
    monkeypatch.delenv('VL_MODEL', raising=False)
    monkeypatch.delenv('MCP_DASHSCOPE_BASE_URL', raising=False)
    assert lm.get_llm_client() is not None


def test_json_client_validates_before_returning_and_caps_additional_calls():
    responses = iter(['invalid', '{"model":"AX"}'])
    client = SimpleNamespace(invoke=lambda prompt: SimpleNamespace(content=next(responses)))
    wrapped = PolicyChatClient(client, ProviderPolicy('text', json_retries=1), json_mode=True)
    assert wrapped.invoke('公开合成输入').content == '{"model":"AX"}'


def test_empty_text_response_is_not_success():
    client = SimpleNamespace(invoke=lambda prompt: SimpleNamespace(content=''))
    with pytest.raises(ProviderFailure) as error: PolicyChatClient(client, ProviderPolicy('text')).invoke('问题')
    assert error.value.code == 'provider_invalid_response'


def test_partial_stream_preserved_then_safe_error_without_restarting_stream():
    calls = []
    def stream(prompt):
        calls.append(1)
        yield SimpleNamespace(content='已生成部分')
        raise openai.APITimeoutError(request=httpx.Request('POST', 'https://private.invalid'))
    client = PolicyChatClient(SimpleNamespace(stream=stream), ProviderPolicy('text'))
    parts = []
    with pytest.raises(ProviderFailure) as error:
        for chunk in client.stream('问题'): parts.append(chunk.content)
    assert parts == ['已生成部分'] and calls == [1]
    assert error.value.code == 'upstream_timeout' and error.value.retryable
    assert 'private.invalid' not in str(error.value)


def test_local_deadline_detects_late_completion_without_automatic_second_inference(monkeypatch):
    import time
    monkeypatch.setenv('PROVIDER_POLICIES_ENABLED', 'true')
    monkeypatch.setenv('PROVIDER_RERANK_TIMEOUT_SECONDS', '1')
    ticks = iter([0., 2.]); monkeypatch.setattr(time, 'monotonic', lambda: next(ticks))
    calls = []
    with pytest.raises(ProviderFailure) as error:
        local_call('rerank', lambda: calls.append(1) or [0.9])
    assert error.value.code == 'upstream_timeout' and calls == [1]


def test_local_unknown_failure_never_blindly_retries(monkeypatch):
    monkeypatch.setenv('PROVIDER_POLICIES_ENABLED', 'true')
    monkeypatch.setenv('PROVIDER_RERANK_MAX_RETRIES', '3')
    calls = []
    def failure(): calls.append(1); raise RuntimeError('合成GPU故障')
    with pytest.raises(ProviderFailure) as error: local_call('rerank', failure)
    assert calls == [1] and not error.value.retryable


def test_host_bridge_uses_embedding_policy_timeout_and_validates_shape(monkeypatch):
    import requests
    from app.infrastructure.queue.model_client import HostEmbedder
    monkeypatch.setenv('MODEL_HOST_URL', 'http://127.0.0.1:9999')
    monkeypatch.setenv('MODEL_HOST_TOKEN', 'synthetic-only')
    monkeypatch.setenv('PROVIDER_POLICIES_ENABLED', 'true')
    monkeypatch.setenv('PROVIDER_EMBEDDING_TIMEOUT_SECONDS', '17')
    seen = []
    class HTTP:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            seen.append(kwargs['timeout'])
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'unexpected': 'payload'})
    monkeypatch.setattr(requests, 'Session', HTTP)
    with pytest.raises(ProviderFailure) as error: HostEmbedder()(['公开合成输入'])
    assert error.value.code == 'provider_invalid_response' and seen == [17]


def test_json_stream_cannot_leak_unvalidated_fragments():
    client = SimpleNamespace(stream=lambda prompt: iter([SimpleNamespace(content='{"broken":')]))
    with pytest.raises(ProviderFailure) as error:
        list(PolicyChatClient(client, ProviderPolicy('text'), json_mode=True).stream('问题'))
    assert error.value.code == 'provider_json_stream_unsupported'


def test_vision_policy_uses_separate_timeout_and_preserves_temperature_zero(monkeypatch):
    from io import BytesIO
    from PIL import Image
    from app.infrastructure.providers.clients import vision_call
    image = BytesIO(); Image.new('RGB', (4, 4), 'white').save(image, format='PNG')
    monkeypatch.setenv('OPENAI_API_KEY', 'synthetic-only')
    monkeypatch.setenv('OPENAI_BASE_URL', 'https://example.invalid/v1')
    monkeypatch.setenv('PROVIDER_POLICIES_ENABLED', 'true')
    monkeypatch.setenv('PROVIDER_VISION_TIMEOUT_SECONDS', '23')
    monkeypatch.setenv('PROVIDER_VISION_MAX_RETRIES', '0')
    seen = []
    class Client:
        def __init__(self, **kwargs):
            seen.append(kwargs)
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.create))
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def create(self, **kwargs):
            seen.append(kwargs)
            return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='合成白图'))])
    monkeypatch.setattr(openai, 'OpenAI', Client)
    assert vision_call(image.getvalue(), '合成上下文', 'synthetic-vision') == '合成白图'
    assert seen[0]['timeout'] == 23 and seen[0]['max_retries'] == 0
    assert seen[1]['temperature'] == 0 and seen[1]['model'] == 'synthetic-vision'
    assert 'extra_body' not in seen[1]


def test_settings_describe_capabilities_without_testing_provider(monkeypatch):
    from app.settings import Settings
    monkeypatch.delenv('VL_MODEL', raising=False)
    result = Settings('unused', 'isolated').provider_capabilities()
    assert result['vision']['configured'] is False and result['vision']['verified'] is False


@pytest.mark.parametrize('scores', [[float('nan')], [float('inf')], []])
def test_reranker_invalid_scores_are_rejected_as_provider_format(monkeypatch, scores):
    from app.runs.query_runner import rerank
    from app.lm import reranker_utils
    monkeypatch.setenv('PROVIDER_POLICIES_ENABLED', 'true')
    monkeypatch.setattr(reranker_utils, 'get_reranker_model', lambda: SimpleNamespace(compute_score=lambda *a, **kw: scores))
    with pytest.raises(ProviderFailure) as failure: rerank('问题', [{'text': '资料'}])
    assert failure.value.code == 'provider_invalid_response'
