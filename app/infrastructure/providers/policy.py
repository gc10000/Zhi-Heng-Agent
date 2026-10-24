"""按能力声明配置，与付费能力验证分离。"""
from dataclasses import dataclass
import json
import math
import os
from pathlib import Path


NAMES = ('text', 'vision', 'embedding', 'rerank')


class ProviderFailure(ValueError):
    """只携带安全错误码，原供应商正文不进入公开message。"""
    def __init__(self, code, retryable=False):
        self.code, self.retryable = code, retryable
        super().__init__('供应商调用失败：' + code)


def boolean(env, name, default):
    value = env.get(name, str(default)).lower()
    if value not in {'true', 'false'}:
        raise ValueError(name + '：请在根目录.env填写布尔值true或false；影响对应能力')
    return value == 'true'


def policies_enabled(environ=None):
    return boolean(os.environ if environ is None else environ, 'PROVIDER_POLICIES_ENABLED', False)


@dataclass(frozen=True)
class ProviderPolicy:
    capability: str
    timeout: float = 60
    max_retries: int = 2
    json_retries: int = 1
    json_supported: bool = True

    @classmethod
    def load(cls, capability, environ=None):
        if capability not in NAMES:
            raise ValueError('供应商能力仅支持text、vision、embedding、rerank')
        env = os.environ if environ is None else environ
        prefix = 'PROVIDER_' + capability.upper() + '_'
        local = capability in {'embedding', 'rerank'}
        values = {}
        for suffix, field, default, converter in [('TIMEOUT_SECONDS', 'timeout', 300 if local else 120 if capability == 'vision' else 60, float),
                ('MAX_RETRIES', 'max_retries', 0 if local else 2, int), ('JSON_RETRIES', 'json_retries', 0 if local else 1, int)]:
            name = prefix + suffix
            try:
                value = converter(env.get(name, str(default)))
                if not math.isfinite(value) or (not 0 < value <= 3600 if field == 'timeout' else not 0 <= value <= 3):
                    raise ValueError()
            except (TypeError, ValueError, OverflowError):
                raise ValueError(name + '：请在根目录.env填写有效范围内的有限数值；影响对应能力') from None
            values[field] = value
        supported = boolean(env, prefix + 'JSON_SUPPORTED', capability == 'text')
        if local and (supported or values['json_retries']):
            raise ValueError(prefix + 'JSON_SUPPORTED/JSON_RETRIES：本机嵌入及重排不生成JSON文本')
        return cls(capability, json_supported=supported, **values)

    def sdk_options(self):
        return {'timeout': self.timeout, 'max_retries': self.max_retries}


def capabilities(environ=None):
    env = os.environ if environ is None else environ
    required = {'text': ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'LLM_DEFAULT_MODEL'),
                'vision': ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'VL_MODEL'),
                'embedding': ('BGE_M3_PATH',), 'rerank': ('BGE_RERANKER_LARGE',)}
    result = {}
    for capability, names in required.items():
        missing = [name for name in names if not env.get(name, '').strip()]
        local = capability in {'embedding', 'rerank'}
        if local and not missing:
            directory = Path(env[names[0]])
            if not directory.is_dir() or not any(directory.glob('*.safetensors')) and not any(directory.glob('*.bin')):
                missing.append(names[0])
        try:
            policy = ProviderPolicy.load(capability, env)
            state = {'timeout_seconds': policy.timeout, 'max_retries': policy.max_retries,
                     'json_supported_declared': policy.json_supported, 'json_retries': policy.json_retries}
        except ValueError:
            state = {'policy_valid': False}
        result[capability] = {'configured': not missing and state.get('policy_valid', True), 'missing': missing,
            'verified': False, 'configuration_only': True, 'backend': 'local' if local else 'openai_compatible', **state}
    return result


def classify(exc):
    import httpx
    import requests
    from openai import APITimeoutError, APIConnectionError, APIResponseValidationError
    if isinstance(exc, ProviderFailure): return exc.code, exc.retryable
    if isinstance(exc, (TimeoutError, APITimeoutError, httpx.TimeoutException, requests.Timeout)):
        return 'upstream_timeout', True
    if isinstance(exc, (ConnectionError, APIConnectionError, httpx.NetworkError, requests.ConnectionError)):
        return 'upstream_connection_failed', True
    status = getattr(exc, 'status_code', None) or getattr(getattr(exc, 'response', None), 'status_code', None)
    if status == 429: return 'provider_rate_limited', True
    if status in {401, 403}: return 'provider_authentication_failed', False
    if status == 404 or getattr(exc, 'code', None) in {'model_not_found', 'invalid_model'}:
        return 'provider_model_not_found', False
    if isinstance(status, int) and 500 <= status <= 599: return 'provider_unavailable', True
    if isinstance(status, int) and 400 <= status <= 499: return 'provider_invalid_request', False
    if isinstance(exc, (ValueError, TypeError, AttributeError, APIResponseValidationError)): return 'provider_invalid_response', False
    return 'provider_unknown_error', False


def invoke_json(operation, policy):
    if not policy.json_supported:
        raise ProviderFailure('provider_capability_unsupported')
    def invalid_constant(value): raise ValueError('不允许非有限JSON数字')
    for attempt in range(policy.json_retries + 1):
        # 调用异常不属于格式错误；SDK负责网络重试，鉴权/模型等不再套一层JSON重试。
        response = operation()
        try:
            content = response.content
            if not isinstance(content, str): raise ValueError('供应商正文必须为字符串')
            parsed = json.loads(content, parse_constant=invalid_constant)
            if not isinstance(parsed, dict): raise ValueError('JSON对象响应必须是对象')
            return response
        except (ValueError, TypeError, AttributeError):
            if attempt == policy.json_retries:
                raise ProviderFailure('provider_invalid_response') from None
