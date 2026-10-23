"""仅访问明确配置的宿主模型桥接，不把Windows模型路径传入容器。"""
import os
import requests


class HostEmbedder:
    def __call__(self, texts):
        base, token = os.getenv('MODEL_HOST_URL'), os.getenv('MODEL_HOST_TOKEN')
        if not base or not token:
            raise ValueError('请配置MODEL_HOST_URL和MODEL_HOST_TOKEN，用于worker访问宿主已有嵌入模型。')
        with requests.Session() as http:
            http.trust_env = False
            result = http.post(base.rstrip('/') + '/embeddings', json={'texts': texts},
                               headers={'X-Model-Token': token}, timeout=300)
            result.raise_for_status()
            return result.json()
