"""Celery创建不主动连broker；Linux worker延迟ack，Mongo账本保证幂等。"""
import os
from celery import Celery


def create_celery():
    broker = os.getenv('REDIS_URL')
    app = Celery('knowledge_import', broker=broker or 'redis://127.0.0.1:6379/0')
    app.conf.update(task_acks_late=True, task_reject_on_worker_lost=True, worker_prefetch_multiplier=1,
                    broker_transport_options={'visibility_timeout': 120}, task_ignore_result=True,
                    task_serializer='json', accept_content=['json'], result_serializer='json',
                    task_default_queue=os.getenv('M2_QUEUE_NAME', 'knowledge-import'),
                    task_send_sent_event=False, worker_send_task_events=False)
    return app


celery_app = create_celery()


@celery_app.task(name='knowledge.import', acks_late=True, reject_on_worker_lost=True)
def import_job(job_id):
    from app.ingestion.runner import run_import
    run_import(job_id)


@celery_app.task(name='knowledge.worker_probe', acks_late=True)
def worker_probe(probe_id):
    """基础设施验证，单独写probe记录，绝不伪造业务导入成功。"""
    import platform
    import requests
    from pymongo import MongoClient
    from app.knowledge.models import content_hash
    from minio import Minio
    with MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000) as client:
        db = client[os.environ['M2_DB_NAME']]
        row = db.worker_probes.find_one({'probe_id': probe_id})
        if row is None or not db.name.startswith('m1_test_'):
            raise ValueError('基础设施探针必须使用显式独立测试账本')
        storage = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'], secret_key=os.environ['MINIO_SECRET_KEY'],
                        secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
        response = storage.get_object(row['bucket'], row['object_key'])
        try:
            digest = content_hash(response.read())
        finally:
            response.close()
            response.release_conn()
        with requests.Session() as http:
            http.trust_env = False
            health = http.get(os.environ['MODEL_HOST_URL'].rstrip('/') + '/health',
                              headers={'X-Model-Token': os.environ['MODEL_HOST_TOKEN']}, timeout=10)
            health.raise_for_status()
        db.worker_probes.update_one({'probe_id': probe_id}, {'$set': {
            'system': platform.system(), 'object_hash_ok': digest == row['sha256'], 'model_host_ok': health.json()['ready']}})
