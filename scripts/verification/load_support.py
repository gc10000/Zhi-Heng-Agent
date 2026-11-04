"""隔离部署HTTP/权限/SSE会话演练。工程合成Run明确标注，绝不调用模型或创建质量job。"""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import os
from pathlib import Path
import secrets
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def login(base, username, password):
    import requests
    session = requests.Session()
    session.trust_env = False
    response = session.post(base + '/api/v1/auth/login', headers={'Origin': base},
                            json={'username': username, 'password': password}, timeout=15)
    assert response.status_code == 200, response.status_code
    session.headers.update({'Origin': base, 'X-CSRF-Token': response.json()['csrf_token']})
    return session


def fixtures(mongo, objects, scope):
    """只在显式关闭生成的随机合成空间写工程fixture，不触碰真实账本。"""
    from app.identity.service import IdentityService, MongoIdentityStore
    from app.conversations.repository import ConversationRepository
    from app.conversations.models import ConversationInput
    from app.runs.repository import RunRepository
    from app.runs.service import RunService
    from app.runs.models import RunInput
    from app.runs.events import EventLedger
    from app.runs.commands import RunCommands
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.originals import OriginalStore
    from app.knowledge.asset_api import original_asset
    from types import SimpleNamespace
    import fitz
    assert os.environ['M7_GENERATION_ENABLED'] == 'false'
    db = mongo[scope.database]
    identity = IdentityService(MongoIdentityStore(db))
    owner = os.environ['M2_KNOWLEDGE_OWNER_ID']
    kb = 'preview-kb'
    repo = KnowledgeRepository(db, owner_id=owner, kb_id=kb)
    pdf = fitz.open()
    pdf.new_page().insert_text((50, 50), 'Zhi-Heng self-authored engineering fixture. No model answer.')
    raw = pdf.tobytes()
    pdf.close()
    tag = secrets.token_hex(3)
    document = repo.register_document('m7-pdf-' + tag, name='工程合成原件.pdf', product_ids=[], purpose='technical')
    originals = OriginalStore(objects, bucket=scope.bucket, prefix=scope.prefix)
    sha = hashlib.sha256(raw).hexdigest()
    key = originals.key(document.document_id, sha)
    originals.put(key, raw, 'application/pdf')
    revision = repo.create_revision(document.document_id, 'm7-pdf-' + tag, original_sha256=sha, object_key=key)
    aid = original_asset(SimpleNamespace(db=db), repo.get_revision(revision.revision_id), media_type='application/pdf', name='工程合成原件.pdf')
    conversations = ConversationRepository(db)
    runs = RunRepository(db, conversations)
    events = EventLedger(runs)
    commands = RunCommands(runs, events)
    service = RunService(runs)
    result = []
    for number in range(4):
        name, password = 'engineering_' + tag + '_' + str(number), secrets.token_urlsafe(24)
        user = identity.add_user(name, password, role='admin', kb_ids=[kb])
        cid = conversations.create(user, ConversationInput(kb_id=kb, title='工程合成演示 · 非模型答案'))['conversation_id']
        run = service.create(user, cid, RunInput(kb_id=kb, question='工程合成流程演练（无模型生成）', client_request_id='fixture-' + tag))
        rid = run['run_id']
        token = commands.start(user, rid)
        text = '工程合成fixture，非模型回答。请核对自制资料原件，不作为质量或容量证明。[1]'
        citation = dict(citation_id='engineering-source', document_id=document.document_id, revision_id=revision.revision_id,
                        text='Zhi-Heng self-authored engineering fixture. No model answer.',
                        source_refs=[{'kind': 'pdf', 'page': 1}], asset_ids=[])
        events.emit(user, rid, 'answer.delta', {'text': text}, expected_token=token)
        commands.finish(user, rid, token, 'completed', {'answer': text}, fields={'answer': text,
            'citations': [citation], 'completion_snapshot': {'text': text, 'citations': [citation], 'product_snapshot': {'product_ids': []}}})
        result.append(dict(username=name, password=password, conversation_id=cid, run_id=rid))
    return result, aid


def exercise(base, session, item, aid):
    start = time.perf_counter()
    rid, cid = item['run_id'], item['conversation_id']
    for path in ('/me', '/documents?kb_id=preview-kb', '/products?kb_id=preview-kb', '/runs/' + rid):
        assert session.get(base + '/api/v1' + path, timeout=15).status_code == 200
    citation = session.get(base + '/api/v1/runs/' + rid + '/citations/engineering-source', timeout=15)
    assert citation.status_code == 200
    asset = session.get(base + '/api/v1/assets/' + aid, headers={'Range': 'bytes=0-4'}, timeout=15)
    assert asset.status_code == 206 and asset.content == b'%PDF-'
    url = base + '/api/v1/runs/' + rid + '/events'
    with session.get(url, stream=True, timeout=15) as stream:
        # Nginx消费并隐藏X-Accel-Buffering；通过公开内容头及逐事件读取核验。
        assert stream.status_code == 200 and 'text/event-stream' in stream.headers['Content-Type']
        assert 'no-transform' in stream.headers['Cache-Control']
        lines = stream.iter_lines(chunk_size=1)
        first = next(line.decode() for line in lines if line.startswith(b'id:'))
        seq = int(first[3:])
    # 关闭前端订阅再用持久游标恢复：只读事件，不产生第二次执行。
    replay = session.get(url, headers={'Last-Event-ID': str(seq)}, timeout=15)
    ids = [int(line[3:]) for line in replay.text.splitlines() if line.startswith('id:')]
    assert ids and min(ids) > seq and len(ids) == len(set(ids)) and 'run.completed' in replay.text
    rejected = session.post(base + '/api/v1/conversations/' + cid + '/runs', json={
        'question': '未授权的新生成必须拒绝', 'kb_id': 'preview-kb', 'client_request_id': secrets.token_hex(8)}, timeout=15)
    assert rejected.status_code == 503 and rejected.json()['error']['code'] == 'generation_disabled'
    return round((time.perf_counter() - start) * 1000, 2)


def live_stream_probe(db, session, base, item):
    from app.identity.service import IdentityService, MongoIdentityStore
    from app.conversations.repository import ConversationRepository
    from app.runs.repository import RunRepository
    from app.runs.service import RunService
    from app.runs.commands import RunCommands
    from app.runs.events import EventLedger
    from app.runs.models import RunInput
    identity = IdentityService(MongoIdentityStore(db))
    user = identity.principal(identity.store.user(item['username']))
    repo = RunRepository(db, ConversationRepository(db))
    events = EventLedger(repo)
    commands = RunCommands(repo, events)
    run = RunService(repo).create(user, item['conversation_id'], RunInput(kb_id='preview-kb',
        question='工程流缓冲探针，非模型生成', client_request_id=secrets.token_hex(8)))
    rid = run['run_id']
    token = commands.start(user, rid)
    started = time.perf_counter()
    try:
        with session.get(base + '/api/v1/runs/' + rid + '/events', stream=True, timeout=8) as stream:
            first = next(line for line in stream.iter_lines(chunk_size=1) if line.startswith(b'id:'))
            elapsed = round((time.perf_counter() - started) * 1000, 2)
            assert first and repo.get(user, rid)['state'] == 'running'
        # 在收到持久首事件后才产生终态，证明代理未等正文/运行结束再flush。
        commands.finish(user, rid, token, 'failed', {'code': 'synthetic_probe_end'}, fields={'error': {
            'code': 'synthetic_probe_end', 'stage': 'engineering', 'retryable': False}})
        return {'first_event_before_terminal': True, 'first_event_ms': elapsed}
    finally:
        if repo.get(user, rid)['state'] == 'running':
            commands.finish(user, rid, token, 'failed', {'code': 'synthetic_probe_end'})


def run(env_file, output, base):
    from scripts.operations.connections import environment, connections, namespace
    environment(env_file)
    scope = namespace()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    with connections() as (mongo, objects, vectors):
        members, aid = fixtures(mongo, objects, scope)
        sessions = [login(base, row['username'], row['password']) for row in members]
        counts = {name: mongo[scope.database][name].count_documents({}) for name in ('runs', 'experiments', 'evaluation_jobs')}
        results = {}
        for count in (1, 2, 4):
            with ThreadPoolExecutor(max_workers=count) as pool:
                timings = list(pool.map(lambda i: exercise(base, sessions[i], members[i], aid), range(count)))
            results[str(count)] = {'sessions': count, 'elapsed_ms_per_session': timings, 'max_ms': max(timings)}
        streaming = live_stream_probe(mongo[scope.database], sessions[0], base, members[0])
        counts['runs'] += 1  # 仅上面的明确标记工程探针Run，拒绝的新生成不能写Run。
        # 同KB另一个用户不能读私有Run/引用；KB授权资产仍可读，撤权后须拒绝。
        a, b = members[0], sessions[1]
        for path in ('/runs/' + a['run_id'], '/runs/' + a['run_id'] + '/citations/engineering-source'):
            assert b.get(base + '/api/v1' + path, timeout=15).status_code == 404
        assert sessions[0].post(base + '/api/v1/conversations', headers={'X-CSRF-Token': 'invalid'}, json={'kb_id': 'preview-kb'}, timeout=15).status_code == 403
        assert sessions[0].post(base + '/api/v1/conversations', headers={'Origin': 'https://untrusted.invalid'}, json={'kb_id': 'preview-kb'}, timeout=15).status_code == 403
        store = mongo[scope.database].users
        store.update_one({'username': members[1]['username']}, {'$set': {'kb_ids': []}})
        assert b.get(base + '/api/v1/assets/' + aid, timeout=15).status_code == 404
        store.update_one({'username': members[1]['username']}, {'$set': {'kb_ids': ['preview-kb']}})
        for value in ('..%2F..%2F.env', '%2Fetc%2Fpasswd', 'unknown'):
            assert sessions[0].get(base + '/api/v1/assets/' + value, timeout=15).status_code == 404
        for path in ('/.env', '/.git/config'):
            assert sessions[0].get(base + path, timeout=15).status_code in (403, 404)
        assert counts == {name: mongo[scope.database][name].count_documents({}) for name in counts}
        public = dict(passed=True, workload='HTTP存储/合成Run回放，非模型容量', concurrency=results,
                      pdf_range=True, sse_disconnect_resume=True, cross_user_run_citation_denied=True,
                      streaming=streaming,
                      revoked_kb_asset_denied=True, csrf_origin=True, path_traversal=True,
                      new_model_calls=0, new_inference=0, new_quality_jobs=0, real_generation='not_executed')
        (output / 'result.json').write_text(json.dumps(public, ensure_ascii=False, indent=2), encoding='utf-8')
        private = dict(base_url=base, **members[0], asset_id=aid, synthetic=True)
        path = output / 'browser.json'
        path.write_text(json.dumps(private, ensure_ascii=False, indent=2), encoding='utf-8')
        path.chmod(0o600)
        for session in sessions:
            session.close()
    return public


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--env-file', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--base-url', required=True)
    args = p.parse_args()
    print(json.dumps(run(args.env_file, args.output, args.base_url), ensure_ascii=False))
