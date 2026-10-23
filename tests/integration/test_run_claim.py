"""真实独立Mongo竞争/崩溃窗口；不杀服务，不改原课程集合。"""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from app.api.errors import APIError
from app.identity.models import Principal
from app.conversations.models import ConversationInput
from app.conversations.repository import ConversationRepository
from app.runs.models import RunInput
from app.runs.repository import RunRepository
from app.runs.service import RunService

pytestmark = pytest.mark.integration


@pytest.fixture
def run_context(mongo_db):
    # 恢复扫描针对整个账本，每用例独立后缀库，避免前例现场参与下一例的时钟推进。
    db = mongo_db.client[mongo_db.name + '_' + uuid4().hex[:8]]
    conv = ConversationRepository(db)
    repo = RunRepository(db, conv)
    user = Principal(user_id=uuid4().hex, username='run-test', role='viewer', kb_ids=('k',))
    cid = conv.create(user, ConversationInput(kb_id='k', product_ids=['p']))['conversation_id']
    return user, cid, conv, repo, RunService(repo)


def request(key='one', question='参数'):
    return RunInput(client_request_id=key, question=question, kb_id='k')


def test_parallel_same_request_one_run_one_message(run_context):
    user, cid, conv, repo, service = run_context
    with ThreadPoolExecutor(max_workers=8) as pool:
        rows = list(pool.map(lambda _: service.create(user, cid, request()), range(16)))
    assert len({r['run_id'] for r in rows}) == 1
    assert rows[0]['run_id'] != rows[0]['message_id'] != cid
    assert conv.messages.count_documents({'conversation_id': cid}) == 1
    assert conv.get(user, cid)['active_run_id'] == rows[0]['run_id']
    assert repo.runs.count_documents({'conversation_id': cid}) == 1
    assert rows[0]['product_snapshot']['product_ids'] == ['p']
    with pytest.raises(APIError) as conflict:
        service.create(user, cid, request(question='changed'))
    assert conflict.value.code == 'idempotency_conflict'


def test_different_request_busy_and_other_conversation_independent(run_context):
    user, cid, conv, repo, service = run_context
    def attempt(i):
        try:
            return service.create(user, cid, request(str(i)))
        except APIError as exc:
            assert exc.status == 409
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(attempt, range(8)))
    assert sum(r is not None for r in results) == 1
    assert conv.messages.count_documents({'conversation_id': cid}) == 1
    second = conv.create(user, ConversationInput(kb_id='k'))['conversation_id']
    assert service.create(user, second, request())['state'] == 'pending'
    other = user.model_copy(update={'user_id': uuid4().hex})
    with pytest.raises(APIError) as denied:
        repo.get(other, next(r for r in results if r)['run_id'])
    assert denied.value.status == 404


@pytest.mark.parametrize('window', ['prepared', 'occupied', 'message_failure'])
def test_rebuild_after_claim_window_repairs_exactly_one_message(run_context, monkeypatch, window):
    user, cid, conv, repo, service = run_context
    row = repo.prepare(user, cid, request())
    if window == 'occupied':
        conv.conversations.update_one({'conversation_id': cid}, {'$set': {'active_run_id': row['run_id']}})
    elif window == 'message_failure':
        original = conv.append_message
        with monkeypatch.context() as patch:
            patch.setattr(conv, 'append_message', lambda *a, **k: (_ for _ in ()).throw(OSError('synthetic persistence failure')))
            with pytest.raises(OSError):
                repo.reconcile(user, row['run_id'])
        assert conv.append_message == original
    # 新服务/仓储实例，从Mongo读准备记录，不借助旧进程内状态。
    rebuilt = RunService(RunRepository(repo.db, ConversationRepository(repo.db)))
    result = rebuilt.create(user, cid, request())
    assert result['run_id'] == row['run_id']
    assert conv.messages.count_documents({'run_id': row['run_id']}) == 1
    assert rebuilt.create(user, cid, request()) == result


def test_http_run_idempotency_ownership_and_failure_propagation(m2_client, monkeypatch):
    client, headers, resources = m2_client
    cid = client.post('/api/v1/conversations', headers=headers, json={'kb_id': 'k'}).json()['conversation_id']
    url = '/api/v1/conversations/' + cid + '/runs'
    payload = request().model_dump()
    assert client.post(url, json=payload).status_code == 403
    first = client.post(url, headers=headers, json=payload)
    assert first.status_code == 202
    rid = first.json()['run_id']
    assert client.post(url, headers=headers, json=payload).json()['run_id'] == rid
    assert client.post(url, headers=headers, json=request('new').model_dump()).status_code == 409
    assert client.get('/api/v1/runs/' + rid).json()['state'] == 'pending'
    assert client.get('/api/v1/runs/missing').status_code == 404
    cid2 = client.post('/api/v1/conversations', headers=headers, json={'kb_id': 'k'}).json()['conversation_id']
    with monkeypatch.context() as patch:
        def failure(*args, **kwargs):
            raise OSError('synthetic-private-error')
        patch.setattr(resources['conversations'], 'append_message', failure)
        failed = client.post('/api/v1/conversations/' + cid2 + '/runs', headers=headers, json=payload)
        assert failed.status_code == 500 and 'synthetic-private-error' not in failed.text
    # HTTP失败不伪装成功；相同请求可从既存账本补足，而非新增运行。
    retried = client.post('/api/v1/conversations/' + cid2 + '/runs', headers=headers, json=payload)
    assert retried.status_code == 202
    assert resources['runs'].runs.count_documents({'conversation_id': cid2}) == 1
