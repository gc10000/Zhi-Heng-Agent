"""创建独立预览环境文件，不读取.env或真实身份，不复用现有卷与账户。"""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import secrets
import socket


def free_port(preferred=0):
    with socket.socket() as sock:
        try:
            sock.bind(('127.0.0.1', preferred))
        except OSError:
            sock.bind(('127.0.0.1', 0))
        return sock.getsockname()[1]


def prepare(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    suffix = secrets.token_hex(3)
    database = 'm1_test_m4_dlv_' + suffix
    env_path = output / 'runtime.env'
    ports = {name: free_port(18080 if name == 'HTTP' else 0)
             for name in ('HTTP', 'MONGO', 'REDIS', 'MINIO', 'MILVUS')}
    assert len(set(ports.values())) == len(ports)
    values = dict(
        M7_PROJECT_NAME='zh-m7-' + suffix, M7_RUNTIME_ENV=env_path.as_posix(), M7_IMAGE_TAG='m7-r1',
        M2_DB_NAME=database, M2_KNOWLEDGE_OWNER_ID='preview-org-' + suffix,
        M2_OBJECT_BUCKET='zh-preview-' + suffix, M2_OBJECT_PREFIX='knowledge/',
        M2_MILVUS_COLLECTION=database + '_v2', M2_QUEUE_NAME='preview-import-' + suffix,
        M6_QUEUE_NAME='preview-evaluation-' + suffix,
        MONGO_URL='mongodb://mongo:27017', MINIO_ENDPOINT='minio:9000',
        MILVUS_URL='http://milvus:19530', REDIS_URL='redis://redis:6379/0',
        MINIO_ACCESS_KEY='preview' + suffix, MINIO_SECRET_KEY=secrets.token_urlsafe(32),
        MINIO_SECURE='false', API_ALLOWED_ORIGINS='http://127.0.0.1:' + str(ports['HTTP']),
        API_COOKIE_SECURE='false', M7_GENERATION_ENABLED='false',
        MODEL_HOST_URL='', MODEL_HOST_TOKEN='', OPENAI_API_KEY='', OPENAI_BASE_URL='',
        TEXT_MODEL='qwen3.8-flash', MINERU_API_TOKEN='', MCP_DASHSCOPE_BASE_URL='',
        M7_PREVIEW_USERNAME='preview_admin', M7_PREVIEW_PASSWORD=secrets.token_urlsafe(24),
        LOG_CONSOLE_ENABLE='False', LOG_FILE_ENABLE='False',
        M2_WORK_DIR='/var/lib/zhi-heng', PROVIDER_TEXT_MAX_RETRIES='0',
        M6_EVALUATION_CATALOG='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    values.update({'M7_' + key + '_PORT': str(port) for key, port in ports.items()})
    with env_path.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(key + '=' + value for key, value in values.items()) + '\n')
    os.chmod(env_path, 0o600)
    host_values = values | {'MONGO_URL': 'mongodb://127.0.0.1:' + str(ports['MONGO']),
        'MINIO_ENDPOINT': '127.0.0.1:' + str(ports['MINIO']),
        'MILVUS_URL': 'http://127.0.0.1:' + str(ports['MILVUS']),
        'REDIS_URL': 'redis://127.0.0.1:' + str(ports['REDIS']) + '/0'}
    host_path = output / 'host.env'
    with host_path.open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(key + '=' + value for key, value in host_values.items()) + '\n')
    os.chmod(host_path, 0o600)
    public = dict(project=values['M7_PROJECT_NAME'], database=database, env_file=env_path.as_posix(),
                  url=values['API_ALLOWED_ORIGINS'], ports=ports, real_generation_enabled=False)
    with (output / 'preview.json').open('x', encoding='utf-8') as stream:
        json.dump(public, stream, ensure_ascii=False, indent=2)
    return public


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='output/m7-preview-' + datetime.now(timezone.utc).strftime('%Y%m%d-%H%M%S'))
    print(json.dumps(prepare(parser.parse_args().output), ensure_ascii=False))
