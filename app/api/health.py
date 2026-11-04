"""有界只读健康探针；不加载模型、不请求付费供应商、不返回配置值。"""
import os
import sys

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

router = APIRouter(tags=['服务'])


def generation_enabled():
    value = os.getenv('M7_GENERATION_ENABLED', 'true').lower()
    if value not in {'true', 'false'}:
        raise ValueError('M7_GENERATION_ENABLED必须为true或false')
    return value == 'true'


def dependency_checks(resources, settings):
    """每次重新只读检查，禁止创建桶、集合或权重单例。"""
    def mongo():
        from pymongo import timeout
        with timeout(2):
            resources['db'].client.admin.command('ping')
        return {'status': 'ok'}

    def minio():
        names = ('MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY')
        if not settings.object_bucket or any(not os.getenv(k) for k in names):
            return {'status': 'configuration_missing'}
        from minio import Minio
        import urllib3
        pool = urllib3.PoolManager(timeout=urllib3.Timeout(connect=2, read=2), retries=0)
        client = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'],
                       secret_key=os.environ['MINIO_SECRET_KEY'],
                       secure=os.getenv('MINIO_SECURE', '').lower() == 'true', http_client=pool)
        try:
            return {'status': 'ok' if client.bucket_exists(settings.object_bucket) else 'not_provisioned'}
        finally:
            pool.clear()

    def milvus():
        if not os.getenv('MILVUS_URL') or not settings.milvus_collection:
            return {'status': 'configuration_missing'}
        from pymilvus import MilvusClient
        client = MilvusClient(uri=os.environ['MILVUS_URL'], timeout=2)
        try:
            return {'status': 'ok' if client.has_collection(settings.milvus_collection, timeout=2) else 'not_provisioned'}
        finally:
            client.close()

    def redis():
        if not os.getenv('REDIS_URL'):
            return {'status': 'configuration_missing'}
        from redis import Redis
        with Redis.from_url(os.environ['REDIS_URL'], socket_connect_timeout=2, socket_timeout=2) as client:
            return {'status': 'ok' if client.ping() else 'unavailable'}

    def models():
        if not generation_enabled():
            return {'status': 'disabled', 'required': False}
        if not all(os.getenv(k) for k in ('OPENAI_API_KEY', 'OPENAI_BASE_URL', 'TEXT_MODEL')):
            return {'status': 'configuration_missing'}
        if os.getenv('MODEL_HOST_URL') and os.getenv('MODEL_HOST_TOKEN'):
            import requests
            with requests.Session() as http:
                http.trust_env = False
                response = http.get(os.environ['MODEL_HOST_URL'].rstrip('/') + '/health/ready',
                                    headers={'X-Model-Token': os.environ['MODEL_HOST_TOKEN']}, timeout=2, allow_redirects=False)
                return {'status': 'ok' if response.status_code == 200 else 'not_loaded',
                        'provider': 'configuration_only_not_verified'}
        embedding = sys.modules.get('app.lm.embedding_utils')
        reranker = sys.modules.get('app.lm.reranker_utils')
        loaded = getattr(embedding, '_bge_m3_ef', None) is not None and getattr(reranker, '_reranker_model', None) is not None
        return {'status': 'ok' if loaded else 'not_loaded', 'provider': 'configuration_only_not_verified'}

    return {'mongo': mongo, 'minio': minio, 'milvus': milvus, 'redis': redis, 'models': models,
            'tools': lambda: {'status': 'configured' if os.getenv('MCP_DASHSCOPE_BASE_URL') else 'disabled',
                             'required': False}}


@router.get('/health/live')
def live():
    return {'live': True}


@router.get('/health/ready')
def ready(request: Request):
    state = request.app.state
    if not getattr(state, 'ready', False):
        return JSONResponse({'ready': False, 'checks': {'startup': {'status': 'starting', 'required': True}}}, status_code=503)
    checks = state.resources.get('readiness_checks')
    if checks is None:
        checks = dependency_checks(state.resources, state.settings)
    results = {}
    for name, check in checks.items():
        try:
            results[name] = {'required': True} | check()
        except Exception:
            results[name] = {'status': 'unavailable', 'required': True}
    good = all(not row['required'] or row['status'] == 'ok' for row in results.values())
    return JSONResponse({'ready': good, 'checks': results}, status_code=200 if good else 503)
