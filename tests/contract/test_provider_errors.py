"""使用已安装 SDK 的真实异常类型，不访问供应商。"""
import httpx
import openai
import pytest
from app.ingestion.runner import classify_error


def sdk_error(kind):
    request = httpx.Request('POST', 'https://provider.invalid/chat')
    if kind == 'timeout':
        return openai.APITimeoutError(request=request)
    if kind == 'connection':
        return openai.APIConnectionError(request=request)
    classes = {429: openai.RateLimitError, 500: openai.InternalServerError,
               503: openai.InternalServerError, 401: openai.AuthenticationError,
               403: openai.PermissionDeniedError, 400: openai.BadRequestError}
    return classes[kind]('synthetic-private-error', response=httpx.Response(kind, request=request), body=None)


@pytest.mark.parametrize('kind,expected', [
    ('timeout', ('upstream_timeout', True)),
    ('connection', ('upstream_connection_failed', True)),
    (429, ('provider_rate_limited', True)),
    (500, ('provider_unavailable', True)),
    (503, ('provider_unavailable', True)),
    (401, ('provider_authentication_failed', False)),
    (403, ('provider_authentication_failed', False)),
    (400, ('invalid_document_or_configuration', False)),
])
def test_actual_sdk_error_classification(kind, expected):
    assert classify_error(sdk_error(kind)) == expected


def test_invalid_format_stays_non_retryable():
    assert classify_error(ValueError('invalid format')) == ('invalid_document_or_configuration', False)
