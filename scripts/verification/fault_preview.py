"""只对显式随机预览项目停启worker/MinIO；故障和恢复记录不接触旧容器。"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def run(env_file, runtime_env, browser_file, output):
    from scripts.operations.connections import environment, connections, namespace
    from scripts.verification.load_support import login
    environment(env_file)
    scope = namespace()
    project = os.environ['M7_PROJECT_NAME']
    if not re.fullmatch(r'zh-m7-[a-f0-9]{6}', project) or os.environ['M7_GENERATION_ENABLED'] != 'false':
        raise ValueError('只能故障演练已禁生成的随机预览项目')
    from dotenv import dotenv_values
    runtime = dotenv_values(runtime_env)
    if any(runtime.get(k) != os.environ.get(k) for k in ('M7_PROJECT_NAME', 'M2_DB_NAME', 'M2_OBJECT_BUCKET', 'M2_MILVUS_COLLECTION')):
        raise ValueError('host/runtime命名空间不符')
    browser = json.loads(Path(browser_file).read_text(encoding='utf-8'))
    assert browser['synthetic'] is True
    base = browser['base_url']
    out = Path(output)
    out.mkdir(parents=True, exist_ok=False)
    command = ['docker', 'compose', '--env-file', str(Path(runtime_env).resolve()), '-f', 'compose.delivery.yaml', '-p', project]
    def compose(*args):
        response = subprocess.run(command + list(args), text=True, capture_output=True, timeout=120)
        # docker命令只含文件/服务名，输出不打印环境。
        with (out / 'commands.log').open('a', encoding='utf-8') as stream:
            stream.write(' '.join(args) + '\n' + response.stdout + response.stderr + '\nexit=' + str(response.returncode) + '\n')
        response.check_returncode()
        return response.stdout
    session = login(base, browser['username'], browser['password'])
    result = dict(real_model_calls=0, local_inference=0)
    try:
        compose('stop', 'worker')
        key = 'm7-worker-stop-' + uuid4().hex
        created = session.post(base + '/api/v1/documents', data={'kb_id': 'preview-kb', 'client_request_id': key},
            files={'file': ('worker-synthetic.md', b'# Engineering fault fixture\nNo model authority.\n', 'text/markdown')}, timeout=20)
        assert created.status_code == 202, created.status_code
        jid = created.json()['job_id']
        # dispatcher每5秒派发，worker保持停止；真实Mongo任务应仍为pending。
        with connections() as (mongo, objects, vectors):
            jobs = mongo[scope.database].import_jobs
            deadline = time.monotonic() + 20
            while time.monotonic() < deadline:
                row = jobs.find_one({'job_id': jid})
                if not row['dispatch_pending']:
                    break
                time.sleep(.25)
            assert row['state'] == 'pending' and row['attempt'] == 0 and row['dispatch_pending'] is False
            compose('start', 'worker')
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                row = jobs.find_one({'job_id': jid})
                if row['state'] in {'failed', 'completed'}:
                    break
                time.sleep(.25)
            # 无MODEL_HOST配置明确失败；Markdown解析缓存已保存，未执行embedding/视觉/文本调用。
            assert row['state'] == 'failed' and row['attempt'] == 1 and row['error']['code'] == 'invalid_document_or_configuration', {k: row[k] for k in ('state', 'attempt', 'error')}
            assert 'parsed' in row['checkpoints'] and 'indexed' not in row['checkpoints']
            code = "from app.infrastructure.queue.celery_app import celery_app; celery_app.send_task('knowledge.import',args=['" + jid + "'])"
            compose('exec', '-T', 'worker', 'python', '-c', code)
            time.sleep(2)
            after = jobs.find_one({'job_id': jid})
            assert after['attempt'] == 1 and after['state'] == 'failed' and after['version'] == row['version']
            result['worker'] = dict(job_id=jid, queued_while_stopped=True, failed_without_model=True,
                                    attempt=1, duplicate_delivery_no_second_attempt=True, parsed_checkpoint=True)
        compose('stop', 'minio')
        failed = session.get(base + '/health/ready', timeout=20)
        live = session.get(base + '/health/live', timeout=10)
        assert failed.status_code == 503 and live.status_code == 200
        assert failed.json()['checks']['minio']['status'] == 'unavailable'
        compose('start', 'minio')
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            recovered = session.get(base + '/health/ready', timeout=20)
            if recovered.status_code == 200:
                break
            time.sleep(.5)
        assert recovered.status_code == 200
        result['storage'] = dict(minio_unavailable_ready=503, live=200, recovered=200)
        result['passed'] = True
        (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
    finally:
        compose('start', 'worker', 'minio')
        session.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('env-file', 'runtime-env', 'browser-file', 'output'):
        p.add_argument('--' + name, required=True)
    args = p.parse_args()
    print(json.dumps(run(args.env_file, args.runtime_env, args.browser_file, args.output), ensure_ascii=False))
