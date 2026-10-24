"""仅访问明确配置的宿主模型桥接，不把Windows模型路径传入容器。"""
import os
import requests


class HostEmbedder:
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
                    result = http.post(base.rstrip('/') + '/embeddings', json={'texts': texts},
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
