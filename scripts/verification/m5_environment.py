"""M5独立账本演示，既有供应商产物只读复制并注明来源，不重导入知识。"""
import argparse
from hashlib import sha256
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


def digest(rows):
    from bson.json_util import dumps
    return sha256(dumps(rows, sort_keys=True).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source-config', type=Path, required=True)
    parser.add_argument('--source-flow', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--port', type=int, default=5175)
    args = parser.parse_args()
    if args.config.exists() or not args.config.resolve().is_relative_to(ROOT / 'output'):
        parser.error('账号配置必须为output下全新路径，不上传')
    import socket
    with socket.socket() as guard:
        guard.bind(('127.0.0.1', args.port))
    frontend_url = 'http://127.0.0.1:' + str(args.port)
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    from pymongo import MongoClient
    from app.identity.service import IdentityService, MongoIdentityStore
    from scripts.verification.m2_live_api import api_process, wait_for
    source = json.loads(args.source_config.read_text('utf-8'))
    flow = json.loads(args.source_flow.read_text('utf-8'))
    if not source['database'].startswith('m1_test_') or not flow['passed']:
        raise ValueError('仅允许已通过的隔离真实产物')
    tag = uuid4().hex
    config = {'database': 'm1_test_m5_live_' + tag, 'username': 'm5-' + tag,
              'password': secrets.token_urlsafe(24), 'kb_id': source['kb_id'],
              'source_database': source['database'], 'source_config_sha256': sha256(args.source_config.read_bytes()).hexdigest(),
              'source_flow_sha256': sha256(args.source_flow.read_bytes()).hexdigest(),
              'source_runs': flow['runs'], 'product_ids': source['product_ids']}
    with MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000) as mongo:
        src, target = mongo[source['database']], mongo[config['database']]
        if target.list_collection_names():
            raise ValueError('目标账本必须为空的新随机测试库')
        runs = list(src.runs.find({'run_id': {'$in': flow['runs']}}).sort('created_at', 1))
        if len(runs) != len(flow['runs']) or any(r['state'] != 'completed' for r in runs):
            raise ValueError('原真实运行不完整')
        cid = runs[0]['conversation_id']
        config.update(conversation_id=cid, initial_run_id=flow['runs'][-1])
        selections = {'runs': {'run_id': {'$in': flow['runs']}}, 'conversations': {'conversation_id': cid},
                      'messages': {'conversation_id': cid}}
        selections.update({name: {} for name in ('knowledge_documents','knowledge_revisions','knowledge_original_assets',
            'knowledge_assets','knowledge_products','knowledge_product_kbs')})
        if not src.knowledge_products.count_documents({}) or not src.knowledge_product_kbs.count_documents({}):
            raise ValueError('原隔离产品目录/知识范围映射不完整')
        frozen = {}
        for name, query in selections.items():
            rows = list(src[name].find(query))
            frozen[name] = {'query': query, 'sha256': digest(rows), 'count': len(rows)}
            if rows:
                target[name].insert_many(rows)
        identity = IdentityService(MongoIdentityStore(target))
        identity.add_user(config['username'], config['password'], role='viewer', kb_ids=[config['kb_id']])
        target.users.update_one({'username': config['username']}, {'$set': {'user_id': runs[0]['owner_id']}})
        env = dict(os.environ)
        env.update(M2_DB_NAME=config['database'], API_COOKIE_SECURE='false', API_ALLOWED_ORIGINS=frontend_url)
        for key in ('M2_KNOWLEDGE_OWNER_ID','M2_OBJECT_BUCKET','M2_OBJECT_PREFIX','M2_MILVUS_COLLECTION'):
            env[key] = source[key]
        # 只搜索原隔离集合，不建立worker或执行任何导入/发布。
        config['source_scope'] = {key: source[key] for key in ('M2_KNOWLEDGE_OWNER_ID','M2_OBJECT_BUCKET','M2_OBJECT_PREFIX','M2_MILVUS_COLLECTION')}
        config['source_snapshots'] = frozen
        with api_process(env, 'm5-' + tag) as (http, base):
            env['API_PROXY_TARGET'] = base
            with args.config.with_suffix('.vite.log').open('xb') as log:
                vite = subprocess.Popen([shutil.which('pnpm'), '-C', 'frontend', 'dev', '--port', str(args.port), '--strictPort'],
                    cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                    creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
                try:
                    import requests
                    def ready():
                        if vite.poll() is not None:
                            raise RuntimeError('Vite启动失败，检查本机日志')
                        try:
                            response = http.post(frontend_url + '/api/v1/auth/login',
                                headers={'Origin': frontend_url}, json={'username': config['username'], 'password': config['password']}, timeout=1)
                            return response.status_code == 200
                        except requests.ConnectionError:
                            return False
                    wait_for(ready, bool, timeout=45)
                    config['base_url'] = base
                    config['frontend_url'] = frontend_url
                    args.config.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
                    print(json.dumps({'ready': True, 'database': config['database']}), flush=True)
                    until = time.monotonic() + 7200
                    while not args.config.with_suffix('.stop').exists() and time.monotonic() < until:
                        time.sleep(1)
                finally:
                    subprocess.run(['taskkill', '/PID', str(vite.pid), '/T', '/F'], capture_output=True)
        assert all(digest(list(src[name].find(item['query']))) == item['sha256'] for name, item in frozen.items())
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
