"""隔离Linux worker/宿主桥接测试环境；仅停止自己创建的进程与容器。"""
from contextlib import contextmanager
from pathlib import Path
import os
import secrets
import socket
import subprocess
import sys
import time
from uuid import uuid4
import requests

ROOT = Path(__file__).resolve().parents[2]


@contextmanager
def worker_environment(database):
    if not database.startswith('m1_test_'):
        raise ValueError('worker验证必须使用显式独立测试库')
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        port = listener.getsockname()[1]
    tag = uuid4().hex
    evidence = ROOT / 'docs/development/evidence'
    evidence.mkdir(exist_ok=True)
    env = dict(os.environ)
    env.update(M2_DB_NAME=database, M2_QUEUE_NAME='m2-test-' + tag, MODEL_HOST_TOKEN=secrets.token_urlsafe(32),
               MODEL_HOST_URL='http://127.0.0.1:' + str(port), REDIS_URL=os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/0'),
               HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', LOG_CONSOLE_ENABLE='False', LOG_FILE_ENABLE='False')
    host_log = (evidence / ('M2-model-host-' + tag + '.txt')).open('wb')
    host = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.infrastructure.model_host:app', '--host', '0.0.0.0', '--port', str(port)],
                            cwd=ROOT, env=env, stdout=host_log, stderr=subprocess.STDOUT,
                            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
    name = 'm2-test-worker-' + tag
    started = False
    try:
        with requests.Session() as http:
            http.trust_env = False
            for _ in range(60):
                if host.poll() is not None:
                    raise RuntimeError('隔离宿主模型桥接启动失败，见本机证据日志')
                try:
                    if http.get(env['MODEL_HOST_URL'] + '/health', headers={'X-Model-Token': env['MODEL_HOST_TOKEN']}, timeout=1).status_code == 200:
                        break
                except requests.RequestException:
                    pass
                time.sleep(.5)
            else:
                raise RuntimeError('隔离模型桥接健康检查超时')
        container_env = env | {'MONGO_URL': 'mongodb://mongo:27017', 'MINIO_ENDPOINT': 'minio:9000',
            'MILVUS_URL': 'http://milvus:19530', 'REDIS_URL': 'redis://redis:6379/0',
            'MODEL_HOST_URL': 'http://host.docker.internal:' + str(port),
            'M2_KNOWLEDGE_OWNER_ID': 'm2-test-owner-' + tag, 'M2_OBJECT_BUCKET': os.environ['MINIO_BUCKET_NAME'],
            'M2_OBJECT_PREFIX': 'm2-test/' + database + '/' + tag + '/', 'M2_MILVUS_COLLECTION': 'm1_test_' + tag + '_v2'}
        names = ['MONGO_URL', 'M2_DB_NAME', 'MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY', 'MINIO_SECURE',
                 'MILVUS_URL', 'REDIS_URL', 'MODEL_HOST_URL', 'MODEL_HOST_TOKEN', 'M2_QUEUE_NAME', 'M2_KNOWLEDGE_OWNER_ID',
                 'M2_OBJECT_BUCKET', 'M2_OBJECT_PREFIX', 'M2_MILVUS_COLLECTION',
                 'OPENAI_API_KEY', 'OPENAI_BASE_URL', 'VL_MODEL', 'MINERU_API_TOKEN', 'MINERU_BASE_URL',
                 'LLM_PROVIDER', 'LLM_ENABLE_THINKING', 'JOB_LEASE_SECONDS', 'JOB_HEARTBEAT_SECONDS']
        command = ['docker', 'run', '-d', '--name', name, '--network', 'product-knowledge-rag_default',
                   '--add-host', 'host.docker.internal:host-gateway']
        for key in names:
            if key in container_env:
                command += ['--env', key]
        command += ['product-knowledge-worker:m2', 'celery', '-A', 'app.infrastructure.queue.celery_app:celery_app',
                    'worker', '--loglevel=WARNING', '--concurrency=1', '-Q', env['M2_QUEUE_NAME']]
        result = subprocess.run(command, cwd=ROOT, env=container_env, capture_output=True)
        if result.returncode:
            raise RuntimeError('隔离Linux worker启动失败，退出码=' + str(result.returncode))
        started = True
        from celery import Celery
        queue = Celery('m2-test-dispatch', broker=env['REDIS_URL'])
        yield {'name': name, 'tag': tag, 'host_env': env, 'container_env': container_env, 'queue': queue,
               'send': lambda jid: queue.send_task('knowledge.import', args=[jid], queue=env['M2_QUEUE_NAME'])}
    finally:
        if started:
            logs = subprocess.run(['docker', 'logs', name], capture_output=True)
            (evidence / ('M2-worker-' + tag + '.txt')).write_bytes(logs.stdout + logs.stderr)
            subprocess.run(['docker', 'stop', '--time', '10', name], capture_output=True)
        host.terminate()
        try:
            host.wait(timeout=15)
        except subprocess.TimeoutExpired:
            host.kill()
            host.wait()
        host_log.close()
