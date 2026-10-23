"""真实Mongo事件账本与HTTP重放，故障仅注入测试端口。"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import json
import pytest
from app.api.errors import APIError
from app.runs.events import EventLedger, utcnow
from tests.integration.test_run_claim import run_context, request

pytestmark = pytest.mark.integration


def test_concurrent_seq_and_one_terminal(run_context):
    user, cid, conv, repo, service = run_context
    rid = service.create(user, cid, request())['run_id']
    ledger = EventLedger(repo)
    with ThreadPoolExecutor(max_workers=5) as pool:
        list(pool.map(lambda i: ledger.emit(user, rid, 'stage.changed', {'index': i}), range(10)))
    events = ledger.read(user, rid)
    assert len(events) == 10 and [e['seq'] for e in events] == sorted({e['seq'] for e in events})
    ledger.emit(user, rid, 'run.completed', {'answer': 'ok'}, state='completed', fields={'answer': 'ok'})
    with pytest.raises(APIError) as ended:
        ledger.emit(user, rid, 'run.failed', {'code': 'late'}, state='failed')
    assert ended.value.code == 'run_finished'
    assert conv.get(user, cid)['active_run_id'] is None
    assert repo.get(user, rid)['state'] == 'completed'
    assert ledger.events.count_documents({'run_id': rid, 'type': {'$in': ['run.completed', 'run.failed']}}) == 1
    assert len(ledger.read(user, rid, 5)) == 6


def test_terminal_saved_before_event_failure_rebuild_repairs(run_context, monkeypatch):
    user, cid, conv, repo, service = run_context
    rid = service.create(user, cid, request())['run_id']
    ledger = EventLedger(repo)
    with monkeypatch.context() as patch:
        def fail(*args, **kwargs):
            raise OSError('synthetic event storage unavailable')
        patch.setattr(ledger.events, 'update_one', fail)
        with pytest.raises(OSError):
            ledger.emit(user, rid, 'run.failed', {'code': 'upstream_failed'}, state='failed')
    saved = repo.get(user, rid)
    assert saved['state'] == 'failed' and len(saved['outbox']) == 1
    rebuilt = EventLedger(repo)
    assert rebuilt.read(user, rid)[0]['type'] == 'run.failed'
    rebuilt.flush(rid)
    assert rebuilt.events.count_documents({'run_id': rid}) == 1
    assert repo.get(user, rid)['outbox'] == []


def test_run_write_failure_does_not_emit_success(run_context, monkeypatch):
    user, cid, conv, repo, service = run_context
    rid = service.create(user, cid, request())['run_id']
    ledger = EventLedger(repo)
    with monkeypatch.context() as patch:
        def fail(*args, **kwargs):
            raise OSError('synthetic run unavailable')
        patch.setattr(repo.runs, 'update_one', fail)
        with pytest.raises(OSError):
            ledger.emit(user, rid, 'run.completed', {}, state='completed')
    assert repo.get(user, rid)['state'] == 'pending'
    assert ledger.events.count_documents({'run_id': rid}) == 0
    assert conv.get(user, cid)['active_run_id'] == rid


def test_expired_cursor_requires_snapshot(run_context):
    user, cid, conv, repo, service = run_context
    rid = service.create(user, cid, request())['run_id']
    ledger = EventLedger(repo)
    ledger.emit(user, rid, 'answer.delta', {'text': 'saved'})
    later = EventLedger(repo, clock=lambda: utcnow() + timedelta(hours=25))
    with pytest.raises(APIError) as expired:
        later.read(user, rid)
    assert expired.value.status == 410
    with pytest.raises(APIError) as latest_expired:
        later.read(user, rid, 1)
    assert latest_expired.value.status == 410
    assert repo.get(user, rid)['answer'] == 'saved'
    with pytest.raises(APIError) as invalid:
        ledger.read(user, rid, 100)
    assert invalid.value.status == 422


def test_each_event_has_its_own_24_hour_window(run_context):
    user, cid, conv, repo, service = run_context
    rid = service.create(user, cid, request())['run_id']
    started = utcnow()
    ledger = EventLedger(repo, clock=lambda: started)
    ledger.emit(user, rid, 'stage.changed', {'stage': 'first'})
    ledger.clock = lambda: started + timedelta(hours=23)
    ledger.emit(user, rid, 'stage.changed', {'stage': 'second'})
    # 25小时后第一条过期，第二条仍可作为有效游标；无需等待Mongo TTL清理。
    ledger.clock = lambda: started + timedelta(hours=25)
    assert ledger.read(user, rid, 2) == []
    with pytest.raises(APIError) as expired:
        ledger.read(user, rid, 1)
    assert expired.value.status == 410
    saved = ledger.events.find_one({'run_id': rid, 'seq': 2})
    from app.runs.events import aware
    assert aware(saved['expires_at']) == (started + timedelta(hours=47)).replace(microsecond=started.microsecond // 1000 * 1000)


def test_http_sse_replay_header_and_terminal_snapshot(m2_client):
    client, headers, resources = m2_client
    cid = client.post('/api/v1/conversations', headers=headers, json={'kb_id': 'k'}).json()['conversation_id']
    rid = client.post('/api/v1/conversations/' + cid + '/runs', headers=headers, json=request().model_dump()).json()['run_id']
    user = resources['identity'].authenticate(client.cookies.get('support_session'))
    ledger = resources['events']
    ledger.emit(user, rid, 'run.started', {'conversation_id': cid})
    ledger.emit(user, rid, 'answer.delta', {'text': '答案'})
    ledger.emit(user, rid, 'run.completed', {}, state='completed')
    response = client.get('/api/v1/runs/' + rid + '/events', headers={'Last-Event-ID': '1'})
    assert response.status_code == 200
    assert response.headers['x-accel-buffering'] == 'no'
    payloads = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith('data: ')]
    assert [e['seq'] for e in payloads] == [2, 3]
    assert payloads[0]['payload']['text'] == '答案'
    assert client.get('/api/v1/runs/' + rid).json()['answer'] == '答案'
    assert client.get('/api/v1/runs/' + rid + '/events?after_seq=3').text == ''
    assert client.get('/api/v1/runs/' + rid + '/events', headers={'Last-Event-ID': 'bad'}).status_code == 422
    assert client.get('/api/v1/runs/unknown/events').status_code == 404
    resources['events'].clock = lambda: utcnow() + timedelta(hours=25)
    assert client.get('/api/v1/runs/' + rid + '/events').status_code == 410


def test_cursor_allows_sequence_gaps_and_outbox_replay_is_idempotent(run_context, monkeypatch):
    user, cid, conv, repo, service = run_context
    rid = service.create(user, cid, request())['run_id']
    ledger = EventLedger(repo)
    ledger.emit(user, rid, 'stage.changed', {'stage': 'one'})
    # 仅合成独立测试账本预留间隙，不要求事件序号相邻。
    repo.runs.update_one({'run_id': rid}, {'$inc': {'seq': 4}})
    with monkeypatch.context() as patch:
        original = repo.runs.update_one
        def fail_ack(query, update, *args, **kwargs):
            if '$pull' in update:
                raise OSError('synthetic ack failure')
            return original(query, update, *args, **kwargs)
        patch.setattr(repo.runs, 'update_one', fail_ack)
        with pytest.raises(OSError):
            ledger.emit(user, rid, 'stage.changed', {'stage': 'six'})
    assert len(repo.get(user, rid)['outbox']) == 1
    assert [e['seq'] for e in EventLedger(repo).read(user, rid, 1)] == [6]
    assert ledger.events.count_documents({'run_id': rid}) == 2
    assert repo.get(user, rid)['outbox'] == []
