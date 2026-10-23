"""真实Mongo任务租约，旧attempt和非法跨系统路径不可执行。"""
from datetime import timedelta
from uuid import uuid4
import pytest
from app.api.errors import APIError
from app.ingestion.jobs import JobRepository
from app.runs.events import utcnow

pytestmark = pytest.mark.integration


def seed(mongo_db):
    jobs = JobRepository(mongo_db)
    jid = uuid4().hex
    jobs.jobs.insert_one({'job_id': jid, 'revision_id': uuid4().hex, 'owner_id': 'test', 'kb_id': 'k',
        'knowledge_owner_id': 'org', 'state': 'pending', 'attempt': 0, 'version': 0, 'dispatch_pending': True,
        'object_key': 'm2-test/' + jid, 'format': 'md', 'stage': 'uploaded'})
    return jobs, jid


def test_only_one_claim_and_old_attempt_cannot_write(mongo_db):
    jobs, jid = seed(mongo_db)
    # 当前账本只有pending；领取需持久attempt/token，而非内存任务锁。
    assert hasattr(jobs, 'claim'), '任务账本缺少持久条件领取协议'
    from concurrent.futures import ThreadPoolExecutor
    now = utcnow()
    with ThreadPoolExecutor(max_workers=6) as pool:
        rows = list(pool.map(lambda _: jobs.claim(jid, lease_seconds=60, now=now), range(6)))
    claimed = [r for r in rows if r]
    assert len(claimed) == 1
    old = claimed[0]
    latest = jobs.claim(jid, lease_seconds=60, now=now + timedelta(seconds=61))
    assert latest['attempt'] == old['attempt'] + 1 and latest['lease_token'] != old['lease_token']
    with pytest.raises(APIError):
        jobs.save(jid, old['attempt'], old['lease_token'], {'stage': 'late'}, now=now + timedelta(seconds=62))
    jobs.save(jid, latest['attempt'], latest['lease_token'], {'stage': 'parsed'}, now=now + timedelta(seconds=62))
    assert jobs.jobs.find_one({'job_id': jid})['stage'] == 'parsed'


def test_dispatch_after_send_failure_can_retry_and_only_passes_job_id(mongo_db):
    from app.ingestion.dispatcher import Dispatcher
    jobs, jid = seed(mongo_db)
    seen = []
    def fail(value):
        seen.append(value)
        raise ConnectionError('synthetic broker failure')
    with pytest.raises(ConnectionError):
        Dispatcher(jobs, fail).dispatch()
    assert jobs.jobs.find_one({'job_id': jid})['dispatch_pending']
    Dispatcher(jobs, lambda value: seen.append(value)).dispatch()
    assert seen == [jid, jid]
    assert not jobs.jobs.find_one({'job_id': jid})['dispatch_pending']


def test_redis_atomic_provider_budget_shared_across_instances(mongo_db):
    import os
    from redis import Redis
    from concurrent.futures import ThreadPoolExecutor
    from app.infrastructure.rate_limits import RedisRateStore
    redis = Redis.from_url(os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0'))
    redis.ping()
    stores = [RedisRateStore(redis, prefix='m2-test:' + mongo_db.name + ':') for _ in range(2)]
    key = uuid4().hex
    with ThreadPoolExecutor(max_workers=8) as pool:
        values = list(pool.map(lambda i: stores[i % 2].reserve(key, 100, 2), range(16)))
    assert sorted(values) == [100 + i * 2 for i in range(16)]


@pytest.mark.parametrize('key', ['C:\\manual.pdf', '/tmp/manual.pdf', '../manual', 'https://private/key', 'a//b'])
def test_worker_messages_reject_local_paths(key):
    from app.ingestion.dispatcher import validate_key
    with pytest.raises(ValueError):
        validate_key(key)


def test_real_linux_celery_reads_object_and_reaches_model_host(mongo_db):
    import os
    import time
    from io import BytesIO
    from minio import Minio
    from app.knowledge.models import content_hash
    from scripts.verification.worker_environment import worker_environment
    data, probe = b'isolated-worker-probe', uuid4().hex
    key, bucket = 'm2-test/' + mongo_db.name + '/' + probe, os.environ['MINIO_BUCKET_NAME']
    storage = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'], secret_key=os.environ['MINIO_SECRET_KEY'],
                    secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
    storage.put_object(bucket, key, BytesIO(data), len(data))
    mongo_db.worker_probes.insert_one({'probe_id': probe, 'bucket': bucket, 'object_key': key, 'sha256': content_hash(data)})
    with worker_environment(mongo_db.name) as env:
        env['queue'].send_task('knowledge.worker_probe', args=[probe], queue=env['host_env']['M2_QUEUE_NAME'])
        for _ in range(90):
            row = mongo_db.worker_probes.find_one({'probe_id': probe})
            if row.get('system'):
                break
            time.sleep(1)
        assert row.get('system') == 'Linux'
        assert row['object_hash_ok'] and row['model_host_ok']
