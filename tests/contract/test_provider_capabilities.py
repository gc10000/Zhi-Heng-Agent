"""真实SDK异常分类与无付费格式反例；不会调用供应商或下载模型。"""
from types import SimpleNamespace
import httpx
import openai
import pytest
from app.infrastructure.providers.policy import ProviderPolicy, capabilities, classify, invoke_json


def test_configuration_is_per_capability_and_zero_retries_are_preserved():
    env = {'PROVIDER_TEXT_TIMEOUT_SECONDS': '12.5', 'PROVIDER_TEXT_MAX_RETRIES': '0',
           'PROVIDER_VISION_TIMEOUT_SECONDS': '45', 'PROVIDER_VISION_MAX_RETRIES': '1'}
    text = ProviderPolicy.load('text', env); vision = ProviderPolicy.load('vision', env)
    assert (text.timeout, text.max_retries) == (12.5, 0)
    assert (vision.timeout, vision.max_retries) == (45, 1)
    assert ProviderPolicy.load('embedding', env).max_retries == 0
    assert not ProviderPolicy.load('rerank', env).json_supported


@pytest.mark.parametrize('name,value', [('PROVIDER_TEXT_TIMEOUT_SECONDS', '0'),
    ('PROVIDER_TEXT_TIMEOUT_SECONDS', 'nan'), ('PROVIDER_TEXT_TIMEOUT_SECONDS', 'inf'),
    ('PROVIDER_TEXT_MAX_RETRIES', '-1'), ('PROVIDER_TEXT_MAX_RETRIES', '1.5'),
    ('PROVIDER_TEXT_JSON_RETRIES', '12'), ('PROVIDER_TEXT_JSON_SUPPORTED', 'yes')])
def test_invalid_policy_rejected_without_echoing_config_value(name, value):
    with pytest.raises(ValueError) as failure: ProviderPolicy.load('text', {name: value})
    assert name in str(failure.value) and value not in str(failure.value).split('：')[-1]


def test_capability_description_has_no_network_probe_or_credentials(tmp_path):
    env = {'OPENAI_API_KEY': 'SYNTHETIC-SECRET', 'OPENAI_BASE_URL': 'https://private.invalid/v1',
           'LLM_DEFAULT_MODEL': 'synthetic', 'BGE_M3_PATH': str(tmp_path)}
    result = capabilities(env)
    assert result['text']['configured'] and not result['text']['verified']
    assert result['vision']['missing'] == ['VL_MODEL']
    assert not result['embedding']['configured']  # 空目录不是已就绪权重
    assert 'MCP_DASHSCOPE_BASE_URL' not in str(result['text'])
    assert 'SYNTHETIC-SECRET' not in str(result) and 'private.invalid' not in str(result)


@pytest.mark.parametrize('exception,expected', [
    (lambda r: openai.APITimeoutError(request=r), ('upstream_timeout', True)),
    (lambda r: openai.APIConnectionError(request=r), ('upstream_connection_failed', True)),
    *[(lambda r, status=status: openai.APIStatusError('私有供应商正文', response=httpx.Response(status, request=r), body={}), expected)
      for status, expected in [(429, ('provider_rate_limited', True)), (503, ('provider_unavailable', True)),
                               (401, ('provider_authentication_failed', False)), (403, ('provider_authentication_failed', False)),
                               (404, ('provider_model_not_found', False)), (400, ('provider_invalid_request', False))]],
    (lambda r: ValueError('格式错误'), ('provider_invalid_response', False)),
    (lambda r: RuntimeError('未知故障'), ('provider_unknown_error', False)),
])
def test_real_installed_sdk_errors_are_not_all_retryable(exception, expected):
    assert classify(exception(httpx.Request('POST', 'https://example.invalid'))) == expected


def test_invalid_json_retries_are_bounded_and_final_payload_is_preserved():
    values = iter(['not-json', '{"voltage":24}'])
    result = invoke_json(lambda: SimpleNamespace(content=next(values)), ProviderPolicy('text', json_retries=1))
    assert result.content == '{"voltage":24}'


@pytest.mark.parametrize('bad', ['null', '[]', '{"x":NaN}', '```json\n{}\n```', ''])
def test_json_mode_rejects_non_objects_and_nonstandard_json(bad):
    calls = []
    def invoke(): calls.append(1); return SimpleNamespace(content=bad)
    with pytest.raises(ValueError): invoke_json(invoke, ProviderPolicy('text', json_retries=1))
    assert len(calls) == 2


def test_authentication_error_is_not_retried_as_format_error():
    calls = []
    def invoke():
        calls.append(1)
        raise openai.AuthenticationError('私有正文', response=httpx.Response(401, request=httpx.Request('POST', 'https://example.invalid')), body={})
    with pytest.raises(openai.AuthenticationError): invoke_json(invoke, ProviderPolicy('text', json_retries=2))
    assert len(calls) == 1


def test_unsupported_json_is_rejected_before_call():
    with pytest.raises(ValueError):
        invoke_json(lambda: pytest.fail('未声明能力不能付费探测'), ProviderPolicy('vision', json_supported=False))


@pytest.mark.parametrize('status,expected_requests', [(429, 2), (503, 2), (401, 1), (404, 1)])
def test_installed_sdk_honors_bounded_retry_and_nonretryable_status(status, expected_requests):
    """MockTransport只替换网络传输，SDK本身真实构造并执行响应/重试协议。"""
    requests = []
    def respond(request):
        requests.append(request)
        return httpx.Response(status, json={'error': {'message': '合成供应商错误', 'type': 'test'}}, headers={'retry-after-ms': '1'})
    policy = ProviderPolicy('text', timeout=2, max_retries=1)
    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        with openai.OpenAI(api_key='synthetic-only', base_url='https://example.invalid/v1', http_client=http, **policy.sdk_options()) as sdk:
            with pytest.raises(openai.APIStatusError) as failure:
                sdk.chat.completions.create(model='synthetic', messages=[{'role': 'user', 'content': '合成输入'}])
    assert len(requests) == expected_requests
    assert classify(failure.value)[1] == (status in {429, 503})


def test_sdk_response_validation_failure_is_a_nonretryable_format_error():
    error = openai.APIResponseValidationError(response=httpx.Response(200, request=httpx.Request('POST', 'https://example.invalid')), body={})
    assert classify(error) == ('provider_invalid_response', False)
