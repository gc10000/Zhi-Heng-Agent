"""仅访问明确配置的宿主模型桥接，不把Windows模型路径传入容器。"""
import os
import requests


class HostReranker:
    """容器通过同一受控宿主计算原模型分数，绝不回退下载本机模型。"""
    def __call__(self, pairs):
        from app.infrastructure.providers.policy import ProviderPolicy, policies_enabled
        import math
        import time
        base, token = os.getenv('MODEL_HOST_URL'), os.getenv('MODEL_HOST_TOKEN')
        if not base or not token:
            raise ValueError('缺少MODEL_HOST_URL或MODEL_HOST_TOKEN')
        # 先校验完整输入再请求，单对超限不能留下已经计算的前半批。
        batches, batch, chars = [], [], 0
        for pair in pairs:
            if (not isinstance(pair, (list, tuple)) or len(pair) != 2
                    or not all(isinstance(value, str) for value in pair)):
                raise ValueError('重排输入必须为问题和原文文本对')
            size = sum(map(len, pair))
            if size > 256000:
                raise ValueError('单个重排文本对超过宿主协议上限，拒绝截断')
            if batch and (len(batch) == 64 or chars + size > 256000):
                batches.append(batch)
                batch, chars = [], 0
            batch.append(list(pair))
            chars += size
        if batch:
            batches.append(batch)
        timeout = ProviderPolicy.load('rerank').timeout if policies_enabled() else 300
        deadline, scores = time.monotonic() + timeout, []
        with requests.Session() as http:
            http.trust_env = False
            for batch in batches:
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise TimeoutError('模型宿主重排整体预算耗尽')
                response = http.post(base.rstrip('/') + '/rerank', json={'pairs': batch},
                                     headers={'X-Model-Token': token}, timeout=remaining, allow_redirects=False)
                response.raise_for_status()
                value = response.json()
                values = value.get('scores') if isinstance(value, dict) else None
                if (not isinstance(values, list) or len(values) != len(batch)
                        or any(type(s) not in (int, float) or not math.isfinite(s) for s in values)):
                    raise ValueError('模型宿主重排返回非法分数')
                scores.extend(values)
        return scores


class HostEmbedder:
    def __init__(self, *, input_type='document'):
        if input_type not in {'query','document'}:raise ValueError('嵌入类型无效')
        self.input_type=input_type

    def __call__(self, texts):
        from app.infrastructure.providers.policy import ProviderPolicy, ProviderFailure, policies_enabled, classify
        base, token = os.getenv('MODEL_HOST_URL'), os.getenv('MODEL_HOST_TOKEN')
        if not base or not token:
            raise ValueError('请配置MODEL_HOST_URL和MODEL_HOST_TOKEN，用于worker访问宿主已有嵌入模型。')
        policy = ProviderPolicy.load('embedding') if policies_enabled() else None
        for attempt in range((policy.max_retries if policy else 0) + 1):
            try:
                with requests.Session() as http:
                    http.trust_env = False
                    result = http.post(base.rstrip('/') + '/embeddings', json={'texts': texts} | ({'input_type':self.input_type} if self.input_type!='document' else {}),
                                       headers={'X-Model-Token': token}, timeout=policy.timeout if policy else 300)
                    result.raise_for_status()
                    values = result.json()
                    if policy:
                        import math
                        if (not isinstance(values, dict) or not isinstance(values.get('dense'), list)
                            or not isinstance(values.get('sparse'), list) or len(values['dense']) != len(texts)
                            or len(values['sparse']) != len(texts)):
                            raise ProviderFailure('provider_invalid_response')
                        for dense, sparse in zip(values['dense'], values['sparse']):
                            if (not dense or not all(math.isfinite(float(x)) for x in dense)
                                or not sparse or any(int(k) < 0 or not math.isfinite(float(v)) or float(v) <= 0 for k, v in sparse.items())):
                                raise ProviderFailure('provider_invalid_response')
                    return values
            except Exception as exc:
                if not policy: raise
                code, retryable = classify(exc)
                if not retryable or attempt == policy.max_retries:
                    raise ProviderFailure(code, retryable) from None
                import time
                time.sleep(min(.1 * 2 ** attempt, .5))
