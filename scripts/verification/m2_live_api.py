"""独立新API进程端到端验收，真实供应商调用显式执行，不属于默认pytest。"""
import argparse
from contextlib import contextmanager
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def wait_for(read, accepted, *, timeout=240):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        value = read()
        if accepted(value):
            return value
        time.sleep(.3)
    raise TimeoutError('独立验收等待超时')


@contextmanager
def api_process(env, tag):
    import requests
    with socket.socket() as server:
        server.bind(('127.0.0.1', 0))
        port = server.getsockname()[1]
    path = ROOT / 'docs/development/evidence' / ('M2-api-' + tag + '.txt')
    with path.open('wb') as log:
        process = subprocess.Popen([sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', str(port)],
            cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        base = 'http://127.0.0.1:' + str(port)
        with requests.Session() as http:
            http.trust_env = False
            try:
                def ready():
                    if process.poll() is not None:
                        raise RuntimeError('独立API进程提前退出，见本机日志')
                    try:
                        return http.get(base + '/api/v1/health', timeout=1).status_code == 200
                    except requests.RequestException:
                        return False
                wait_for(ready, bool, timeout=45)
                yield http, base
            finally:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if not args.database.startswith('m1_test_') or args.report.exists():
        parser.error('必须独立m1_test_库及不存在的新报告路径')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    from pymongo import MongoClient
    from app.identity.service import IdentityService, MongoIdentityStore
    from app.ingestion.dispatcher import Dispatcher
    from app.ingestion.jobs import JobRepository
    from app.knowledge.models import content_hash
    from scripts.verification.worker_environment import worker_environment
    report = {'database': args.database, 'passed': False, 'paid_answer_attempts': 0, 'checks': {}, 'stage': 'setup'}
    started = time.monotonic()
    try:
        with MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000) as mongo, worker_environment(args.database) as worker:
            db = mongo[args.database]
            username, password = uuid4().hex, secrets.token_urlsafe(24)
            IdentityService(MongoIdentityStore(db)).add_user(username, password, role='maintainer', kb_ids=['isolated-k'])
            env = dict(worker['host_env'])
            for key in ('M2_KNOWLEDGE_OWNER_ID', 'M2_OBJECT_BUCKET', 'M2_OBJECT_PREFIX', 'M2_MILVUS_COLLECTION'):
                env[key] = worker['container_env'][key]
            env.update(API_COOKIE_SECURE='false', API_ALLOWED_ORIGINS='http://localhost:8000')
            with api_process(env, worker['tag']) as (http, base):
                def check(response, code):
                    if response.status_code != code:
                        raise AssertionError('HTTP状态不符：' + str(response.status_code))
                    return response.json()
                report['stage'] = 'login'
                login = check(http.post(base + '/api/v1/auth/login', headers={'Origin': 'http://localhost:8000'},
                    json={'username': username, 'password': password}, timeout=10), 200)
                headers = {'Origin': 'http://localhost:8000', 'X-CSRF-Token': login['csrf_token']}
                report['checks']['login'] = True
                ids = []
                for model in ('隔离设备AX24', '隔离设备AX48'):
                    ids.append(check(http.post(base + '/api/v1/products', headers=headers,
                        json={'kb_id': 'isolated-k', 'model': model}, timeout=10), 201)['product_id'])
                report['stage'] = 'upload'
                raw = '# 隔离设备AX24技术手册\n\n## 电源参数\n\nAX24设备输入电压为24V直流，额定电流为2A。接线前必须断电。\n'.encode()
                uploaded = check(http.post(base + '/api/v1/documents', headers=headers,
                    data={'kb_id': 'isolated-k', 'client_request_id': 'm2-live-one', 'product_ids': json.dumps([ids[0]]), 'purpose': 'technical'},
                    files={'file': ('manual.md', raw, 'text/markdown')}, timeout=15), 202)
                report.update({key: uploaded[key] for key in ('job_id', 'document_id', 'revision_id')})
                report['stage'] = 'linux_import'
                Dispatcher(JobRepository(db), worker['send']).dispatch()
                job = wait_for(lambda: http.get(base + '/api/v1/import-jobs/' + uploaded['job_id'], timeout=10).json(),
                    lambda value: value['state'] in {'failed', 'completed'})
                if job['state'] != 'completed':
                    report['job_error'] = job.get('error')
                    raise AssertionError('真实导入未完成')
                report['checks']['linux_import_published'] = True
                report['checks']['original_hash'] = content_hash(http.get(base + '/api/v1/assets/' + uploaded['original_asset_id'], timeout=10).content) == content_hash(raw)
                cid = check(http.post(base + '/api/v1/conversations', headers=headers, json={'kb_id': 'isolated-k'}, timeout=10), 201)['conversation_id']
                data = {'question': '请查询这台设备的输入电压与额定电流，并说明接线注意事项。', 'kb_id': 'isolated-k', 'client_request_id': 'live-query'}
                run = check(http.post(base + '/api/v1/conversations/' + cid + '/runs', headers=headers, json=data, timeout=10), 202)
                rid = run['run_id']
                report['run_id'], report['conversation_id'] = rid, cid
                report['stage'] = 'clarification'
                path = base + '/api/v1/runs/' + rid
                waiting = wait_for(lambda: http.get(path, timeout=10).json(), lambda value: value['state'] != 'pending')
                waiting = wait_for(lambda: http.get(path, timeout=10).json(), lambda value: value['state'] in {'awaiting_input', 'failed'})
                assert waiting['state'] == 'awaiting_input' and len(waiting['candidates']) == 2
                check(http.post(path + '/confirm-product', headers=headers,
                    json={'expected_version': waiting['version'], 'product_ids': [ids[0]]}, timeout=10), 200)
                report['checks']['clarification_confirm'] = True
                report['stage'] = 'answer'
                report['paid_answer_attempts'] += 1
                final = wait_for(lambda: http.get(path, timeout=10).json(),
                    lambda value: value['state'] in {'completed', 'failed', 'interrupted', 'cancelled'}, timeout=240)
                if final['state'] != 'completed':
                    report['query_error'] = final.get('error')
                    raise AssertionError('真实问答未成功')
                report['checks']['grounded_answer'] = '24' in final['answer'] and '2' in final['answer'] and bool(final['citations'])
                report['answer_sha256'], report['answer_chars'] = content_hash(final['answer'].encode()), len(final['answer'])
                report['stage'] = 'citation_replay'
                citation = final['citations'][0]
                recalled = check(http.get(path + '/citations/' + citation['citation_id'], timeout=10), 200)
                report['checks']['citation_revision_source'] = (recalled['revision_id'] == uploaded['revision_id'] and bool(recalled['source_refs']) and '24V' in recalled['text'])
                messages = wait_for(lambda: http.get(base + '/api/v1/conversations/' + cid + '/messages', timeout=10).json()['items'], lambda items: len(items) == 2)
                report['checks']['message_snapshot'] = (messages[0]['product_snapshot']['product_ids'] == [] and messages[1]['text'] == final['answer'] and messages[1]['citations'] == final['citations'])
                replay = http.get(path + '/events', timeout=20)
                assert replay.status_code == 200
                events = [json.loads(line[6:]) for line in replay.text.splitlines() if line.startswith('data: ')]
                report['checks']['single_terminal'] = [e['type'] for e in events if e['type'] in {'run.completed', 'run.failed', 'run.cancelled', 'run.interrupted'}] == ['run.completed']
                report['checks']['delta_snapshot_equal'] = ''.join(e['payload']['text'] for e in events if e['type'] == 'answer.delta') == final['answer']
                duplicate = check(http.post(base + '/api/v1/conversations/' + cid + '/runs', headers=headers, json=data, timeout=10), 202)
                report['checks']['idempotent_run'] = duplicate['run_id'] == rid and db.messages.count_documents({'run_id': rid}) == 2
                report['checks']['event_order'] = all(a['seq'] < b['seq'] for a, b in zip(events, events[1:]))
                report['event_types'] = [e['type'] for e in events]
                report['stage'] = 'complete'
                report['passed'] = all(report['checks'].values())
    except Exception as exc:
        report['exception_type'] = type(exc).__name__
    report['elapsed_seconds'] = round(time.monotonic() - started, 3)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': report['passed'], 'stage': report['stage'], 'checks': report['checks'],
                      'elapsed_seconds': report['elapsed_seconds'], 'paid_answer_attempts': report['paid_answer_attempts']}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
