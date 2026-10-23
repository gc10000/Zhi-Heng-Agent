"""真实独立Mongo状态机/命令恢复，不中止真实业务进程。"""
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
import pytest
from app.api.errors import APIError
from app.runs.commands import RunCommands, ConfirmInput, VersionInput
from app.runs.events import EventLedger, utcnow
from tests.integration.test_run_claim import run_context, request

pytestmark = pytest.mark.integration


def setup(run_context):
    user, cid, conv, repo, service = run_context
    rid = service.create(user, cid, request())['run_id']
    now = [utcnow()]
    ledger = EventLedger(repo, clock=lambda: now[0])
    commands = RunCommands(repo, ledger, clock=lambda: now[0])
    return user, rid, repo, commands, now


def test_wait_refresh_confirm_resume_and_original_message_unchanged(run_context):
    user, rid, repo, commands, now = setup(run_context)
    token = commands.start(user, rid)
    waiting = commands.wait_input(user, rid, token, candidates=[{'product_id': 'p1'}, {'product_id': 'p2'}], resume_point={'stage': 'retrieve'})
    # 超过执行租约仍应等待人工，不把awaiting_input作为卡死任务。
    now[0] += timedelta(minutes=5)
    rebuilt = RunCommands(repo, EventLedger(repo, clock=lambda: now[0]), clock=lambda: now[0])
    assert rebuilt.recover() == []
    assert repo.get(user, rid)['state'] == 'awaiting_input'
    with pytest.raises(APIError) as invalid:
        rebuilt.confirm(user, rid, ConfirmInput(expected_version=waiting['version'], product_ids=['forged']))
    assert invalid.value.status == 422
    other = user.model_copy(update={'user_id': 'other'})
    with pytest.raises(APIError) as denied:
        rebuilt.confirm(other, rid, ConfirmInput(expected_version=waiting['version'], product_ids=['p2']))
    assert denied.value.status == 404
    with pytest.raises(APIError) as stale:
        rebuilt.confirm(user, rid, ConfirmInput(expected_version=0, product_ids=['p2']))
    assert stale.value.status == 409
    result = rebuilt.confirm(user, rid, ConfirmInput(expected_version=waiting['version'], product_ids=['p2']))
    assert result['state'] == 'pending' and result['resume_point'] == {'stage': 'retrieve'}
    assert result['product_snapshot']['product_ids'] == ['p2']
    assert repo.conversations.history(user, result['conversation_id'])['items'][0]['product_snapshot']['product_ids'] == ['p']
    # 浏览器确认后重发原创建请求，仍返回同run，不能用更新后的选择覆盖原用户消息。
    from app.runs.service import RunService
    assert RunService(repo).create(user, result['conversation_id'], request())['run_id'] == rid
    new_token = rebuilt.start(user, rid)
    assert new_token != token
    with pytest.raises(APIError) as fenced:
        rebuilt.finish(user, rid, token, 'completed', {})
    assert fenced.value.code == 'lease_lost'
    rebuilt.finish(user, rid, new_token, 'completed', {}, fields={'answer': 'done'})
    with pytest.raises(APIError):
        rebuilt.confirm(user, rid, ConfirmInput(expected_version=waiting['version'], product_ids=['p1']))


def test_cancel_cooperative_idempotent_and_never_completed(run_context):
    user, rid, repo, commands, now = setup(run_context)
    token = commands.start(user, rid)
    version = repo.get(user, rid)['version']
    result = commands.cancel(user, rid, VersionInput(expected_version=version))
    assert result['state'] == 'cancel_requested'
    assert commands.cancel(user, rid, VersionInput(expected_version=version)) == result
    with pytest.raises(APIError):
        commands.finish(user, rid, token, 'completed', {})
    assert commands.boundary(user, rid, token) is False
    assert repo.get(user, rid)['state'] == 'cancelled'
    assert commands.cancel(user, rid, VersionInput(expected_version=version))['state'] == 'cancelled'


def test_cancel_intent_with_lost_worker_is_interrupted_not_acknowledged(run_context):
    user, rid, repo, commands, now = setup(run_context)
    commands.start(user, rid)
    commands.cancel(user, rid, VersionInput(expected_version=repo.get(user, rid)['version']))
    now[0] += timedelta(seconds=61)
    assert commands.recover() == [rid]
    assert repo.get(user, rid)['state'] == 'interrupted'


def test_expired_lease_interrupts_and_old_run_does_not_release_new(run_context):
    user, rid, repo, commands, now = setup(run_context)
    token = commands.start(user, rid)
    now[0] += timedelta(seconds=61)
    with pytest.raises(APIError):
        commands.finish(user, rid, token, 'completed', {})
    assert commands.recover() == [rid]
    row = repo.get(user, rid)
    assert row['state'] == 'interrupted'
    assert repo.conversations.get(user, row['conversation_id'])['active_run_id'] is None
    from app.runs.service import RunService
    next_run = RunService(repo).create(user, row['conversation_id'], request('next'))
    commands.recover()
    repo.release(row)
    assert repo.conversations.get(user, row['conversation_id'])['active_run_id'] == next_run['run_id']


@pytest.mark.parametrize('kind', ['pending_timeout', 'input_timeout', 'cancel_without_worker'])
def test_idle_timeouts_release_occupation(run_context, kind):
    user, rid, repo, commands, now = setup(run_context)
    if kind == 'input_timeout':
        token = commands.start(user, rid)
        commands.wait_input(user, rid, token, candidates=[{'product_id': 'p'}], resume_point={'stage': 'match'})
        now[0] += timedelta(days=2)
    elif kind == 'cancel_without_worker':
        commands.cancel(user, rid, VersionInput(expected_version=0))
    else:
        now[0] += timedelta(minutes=6)
    assert commands.recover() == [rid]
    assert repo.get(user, rid)['state'] == ('cancelled' if kind == 'cancel_without_worker' else 'interrupted')


def test_parallel_start_only_one_execution_token(run_context):
    user, rid, repo, commands, now = setup(run_context)
    def start(_):
        try:
            return commands.start(user, rid)
        except APIError as exc:
            assert exc.status == 409
            return None
    with ThreadPoolExecutor(max_workers=6) as pool:
        result = list(pool.map(start, range(6)))
    assert sum(v is not None for v in result) == 1


def test_recovery_cannot_interrupt_concurrently_renewed_lease(run_context, monkeypatch):
    user, rid, repo, commands, now = setup(run_context)
    token = commands.start(user, rid)
    now[0] += timedelta(seconds=61)
    original = commands.events.emit
    def renew_before_recovery(*args, **kwargs):
        # 用另一实例在扫描后CAS前续约；模拟短暂调度延迟，版本必须保护恢复扫描。
        repo.runs.update_one({'run_id': rid}, {'$set': {'execution_lease': now[0] + timedelta(seconds=60)}, '$inc': {'version': 1}})
        return original(*args, **kwargs)
    monkeypatch.setattr(commands.events, 'emit', renew_before_recovery)
    assert commands.recover() == []
    assert repo.get(user, rid)['state'] == 'running'


def test_http_confirm_and_cancel_use_owner_version_and_csrf(m2_client):
    client, headers, resources = m2_client
    cid = client.post('/api/v1/conversations', headers=headers, json={'kb_id': 'k'}).json()['conversation_id']
    rid = client.post('/api/v1/conversations/' + cid + '/runs', headers=headers, json=request().model_dump()).json()['run_id']
    user = resources['identity'].authenticate(client.cookies.get('support_session'))
    commands = resources['commands']
    token = commands.start(user, rid)
    waiting = commands.wait_input(user, rid, token, candidates=[{'product_id': 'p'}], resume_point={'stage': 'query'})
    base = '/api/v1/runs/' + rid
    payload = {'expected_version': waiting['version'], 'product_ids': ['p']}
    assert client.post(base + '/confirm-product', json=payload).status_code == 403
    assert client.get(base).json()['candidates'] == [{'product_id': 'p'}]
    result = client.post(base + '/confirm-product', headers=headers, json=payload)
    assert result.status_code == 200 and result.json()['state'] == 'pending'
    assert client.post(base + '/confirm-product', headers=headers, json=payload).status_code == 409
    version = result.json()['version']
    assert client.post(base + '/cancel', headers=headers, json={'expected_version': version}).status_code == 200
    assert client.post(base + '/cancel', headers=headers, json={'expected_version': version}).status_code == 200
    commands.recover()
    assert client.get(base).json()['state'] == 'cancelled'
