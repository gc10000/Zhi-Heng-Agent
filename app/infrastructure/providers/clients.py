"""真实调用适配；模块导入不创建客户端、不探测模型。"""
import time
from .policy import ProviderPolicy, ProviderFailure, classify, invoke_json, policies_enabled


class PolicyChatClient:
    def __init__(self, client, policy, *, json_mode=False):
        self.client, self.policy, self.json_mode = client, policy, json_mode

    def invoke(self, *args, **kwargs):
        try:
            operation = lambda: self.client.invoke(*args, **kwargs)
            if self.json_mode:
                return invoke_json(operation, self.policy)
            response = operation()
            if not isinstance(response.content, str) or not response.content.strip():
                raise ProviderFailure('provider_invalid_response')
            return response
        except Exception as exc:
            raise ProviderFailure(*classify(exc)) from None

    def stream(self, *args, **kwargs):
        if self.json_mode:
            # JSON须整体验证，不能把尚未验证片段伪装成有效结构化输出。
            raise ProviderFailure('provider_json_stream_unsupported')
        seen = False
        try:
            for chunk in self.client.stream(*args, **kwargs):
                if not isinstance(chunk.content, str): raise ProviderFailure('provider_invalid_response')
                seen = seen or bool(chunk.content.strip())
                yield chunk
            if not seen: raise ProviderFailure('provider_invalid_response')
        except Exception as exc:
            # 已输出部分时只传播安全错误，不能重新打开流造成重复正文/付费。
            raise ProviderFailure(*classify(exc)) from None


def local_call(capability, operation):
    if not policies_enabled(): return operation()
    if capability not in {'embedding', 'rerank'}:
        raise ValueError('本机调用仅接受嵌入或重排能力')
    policy = ProviderPolicy.load(capability)
    for attempt in range(policy.max_retries + 1):
        started = time.monotonic()
        try:
            result = operation()
        except Exception as exc:
            code, retryable = classify(exc)
            if not retryable or attempt == policy.max_retries:
                raise ProviderFailure(code, retryable) from None
            time.sleep(min(.1 * 2 ** attempt, .5))
            continue
        if time.monotonic() - started > policy.timeout:
            # 本机同步推理只能在返回边界发现超时，不能安全抢占CUDA线程。
            # 超时后不自动再推理，避免重复占用模型/显存。
            raise ProviderFailure('upstream_timeout', True)
        return result


def vision_call(data, context, model):
    import os
    from urllib.parse import urlparse
    from openai import OpenAI
    from app.ingestion.stages.images import VisionDescriber
    missing = [name for name in ('OPENAI_API_KEY', 'OPENAI_BASE_URL') if not os.getenv(name)]
    if not model: missing.append('VL_MODEL')
    if missing:
        raise ValueError('缺少' + '、'.join(missing) + '；填写根目录.env，用于图片摘要')
    provider = os.getenv('LLM_PROVIDER', 'auto')
    if provider not in {'auto', 'dashscope', 'openai_compatible'}:
        raise ValueError('LLM_PROVIDER：请在根目录.env填写支持的供应商类型')
    host = urlparse(os.environ['OPENAI_BASE_URL']).hostname or ''
    dashscope = provider == 'dashscope' or provider == 'auto' and (host == 'dashscope.aliyuncs.com' or host.endswith('.dashscope.aliyuncs.com'))
    options = {'extra_body': {'enable_thinking': os.getenv('LLM_ENABLE_THINKING', 'false').lower() == 'true'}} if dashscope else {}
    enabled = policies_enabled()
    policy = ProviderPolicy.load('vision') if enabled else None
    try:
        with OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=os.environ['OPENAI_BASE_URL'],
                    **(policy.sdk_options() if policy else {})) as client:
            result = VisionDescriber(client, model, '请用中文准确描述设备技术图示，保留端口、型号与连接关系。', request_options=options)(data, context)
        if enabled and (not isinstance(result, str) or not result.strip()):
            raise ProviderFailure('provider_invalid_response')
        return result
    except Exception as exc:
        if enabled: raise ProviderFailure(*classify(exc)) from None
        raise
