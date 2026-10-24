"""M3浏览器验收的独立真实环境；保留数据，仅终止本脚本创建的进程。"""
import argparse
import json
import os
from pathlib import Path
import secrets
import shutil
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True, help='本地忽略的临时账号文件，不上传')
    args = parser.parse_args()
    if args.config.exists() or 'evidence' not in args.config.parts:
        parser.error('账号文件必须是evidence内的新路径')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    from pymongo import MongoClient
    from app.identity.service import IdentityService, MongoIdentityStore
    from app.ingestion.dispatcher import Dispatcher
    from app.ingestion.jobs import JobRepository
    from scripts.verification.worker_environment import worker_environment
    from scripts.verification.m2_live_api import api_process, wait_for
    tag = uuid4().hex
    database = 'm1_test_m3_' + tag
    config = {'database': database, 'username': 'm3-' + tag, 'password': secrets.token_urlsafe(24), 'kb_id': 'm3-isolated'}
    with MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000) as mongo, worker_environment(database) as worker:
        db = mongo[database]
        identity = IdentityService(MongoIdentityStore(db))
        identity.add_user(config['username'], config['password'], role='maintainer', kb_ids=[config['kb_id']])
        config['viewer'] = 'viewer-' + tag
        identity.add_user(config['viewer'], config['password'], role='viewer', kb_ids=[config['kb_id']])
        env = dict(worker['host_env'])
        for key in ('M2_KNOWLEDGE_OWNER_ID', 'M2_OBJECT_BUCKET', 'M2_OBJECT_PREFIX', 'M2_MILVUS_COLLECTION'):
            env[key] = worker['container_env'][key]
            config[key] = env[key]
        env.update(API_COOKIE_SECURE='false', API_ALLOWED_ORIGINS='http://127.0.0.1:5173')
        with api_process(env, 'm3-' + tag) as (http, base):
            headers = {'Origin': 'http://127.0.0.1:5173'}
            response = http.post(base + '/api/v1/auth/login', headers=headers, json={'username': config['username'], 'password': config['password']}, timeout=10)
            response.raise_for_status()
            headers['X-CSRF-Token'] = response.json()['csrf_token']
            config['product_ids'] = []
            for name in ('隔离设备AX24', '隔离设备AX48'):
                response = http.post(base + '/api/v1/products', headers=headers, json={'kb_id': config['kb_id'], 'model': name}, timeout=10)
                response.raise_for_status()
                config['product_ids'].append(response.json()['product_id'])
            raw = '# 隔离设备AX24技术手册\n\n## 电源参数\n\nAX24设备输入电压为24V直流，额定电流为2A。接线前必须断电。\n'.encode()
            response = http.post(base + '/api/v1/documents', headers=headers, data={'kb_id': config['kb_id'],
                'client_request_id': 'm3-initial', 'product_ids': json.dumps(config['product_ids'][:1]), 'purpose': 'technical'},
                files={'file': ('m3-manual.md', raw, 'text/markdown')}, timeout=15)
            response.raise_for_status()
            config['uploaded'] = response.json()
            dispatcher = Dispatcher(JobRepository(db), worker['send'])
            dispatcher.dispatch()
            job = wait_for(lambda: http.get(base + '/api/v1/import-jobs/' + config['uploaded']['job_id'], timeout=10).json(),
                lambda row: row['state'] in {'completed', 'failed'}, timeout=300)
            if job['state'] != 'completed':
                raise RuntimeError('M3隔离小样导入失败；不输出私有异常，保留任务现场')
            env['API_PROXY_TARGET'] = base
            pnpm = shutil.which('pnpm')
            log_path = args.config.with_suffix('.vite.log')
            with log_path.open('wb') as log:
                vite = subprocess.Popen([pnpm, '-C', 'frontend', 'dev', '--port', '5173', '--strictPort'], cwd=ROOT, env=env,
                    stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                try:
                    # Vite尚未监听时的拒绝连接只是启动中，不能终止整个验收环境。
                    import requests
                    def vite_ready():
                        if vite.poll() is not None:
                            raise RuntimeError('Vite进程已退出，请查看本地vite.log')
                        try:
                            return http.get('http://127.0.0.1:5173', timeout=5).status_code == 200
                        except requests.ConnectionError:
                            return False
                    wait_for(vite_ready, bool, timeout=45)
                    config['base_url'] = base
                    args.config.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
                    print(json.dumps({'ready': True, 'database': database, 'config': str(args.config)}), flush=True)
                    stop = args.config.with_suffix('.stop')
                    until = time.monotonic() + 14400
                    while not stop.exists() and time.monotonic() < until:
                        dispatcher.dispatch()
                        time.sleep(1)
                finally:
                    # Windows pnpm进程树仅限本脚本启动的PID，避免遗留开发服务器。
                    subprocess.run(['taskkill', '/PID', str(vite.pid), '/T', '/F'], capture_output=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
