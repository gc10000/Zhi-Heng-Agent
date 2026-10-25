"""真实隔离Mongo，在占用CAS后、claimed写入前退出，不清除占用制造通过。"""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import timedelta
import pytest
from app.api.errors import APIError
from app.conversations.repository import ConversationRepository
from app.conversations.models import ConversationPatch
from app.runs.commands import RunCommands
from app.runs.events import EventLedger, utcnow
from app.runs.models import RunInput
from app.runs.repository import RunRepository
from app.runs.service import RunService
from app.support.models import SupportInput
from app.support.repository import SupportRepository

pytestmark = pytest.mark.integration


def setup(support_client):
    client, headers, resources, user, cid, rid, citation = support_client
    support = SupportRepository(resources['conversations'], resources['runs'])
    support.update(user, cid, SupportInput(expected_version=0, run_id=rid,
        values={'device': 'AX-24', 'symptom': '失败'}))
    prepared = resources['runs'].prepare(user, cid, RunInput(question='继续排查', kb_id='k', client_request_id='claim-window'))
    return resources, user, cid, support, prepared


def stop_after_occupation(resources, user, prepared, monkeypatch):
    runs = resources['runs']
    original = runs.runs.update_one
    def stop(query, update, *args, **kwargs):
        if query.get('claim_state') == 'preparing' and update.get('$set', {}).get('claim_state') == 'claimed':
            raise OSError('synthetic stop after occupation CAS')
        return original(query, update, *args, **kwargs)
    with monkeypatch.context() as patch:
        patch.setattr(runs.runs, 'update_one', stop)
        with pytest.raises(OSError, match='after occupation CAS'):
            runs.reconcile(user, prepared['run_id'])
    assert resources['conversations'].get(user, prepared['conversation_id'])['active_run_id'] == prepared['run_id']
    assert runs.get(user, prepared['run_id'])['claim_state'] == 'preparing'
    assert resources['db'].messages.count_documents({'run_id': prepared['run_id']}) == 0


def rebuild(resources, clock):
    repo = RunRepository(resources['db'], ConversationRepository(resources['db']))
    commands = RunCommands(repo, EventLedger(repo, clock=clock), pending_seconds=1, clock=clock)
    return repo, commands


@pytest.mark.parametrize('elapsed', [0, 3600])
def test_occupied_crash_then_correction_recovers_or_times_out(support_client, monkeypatch, elapsed):
    resources, user, cid, support, prepared = setup(support_client)
    stop_after_occupation(resources, user, prepared, monkeypatch)
    frozen = deepcopy(prepared['support_snapshot'])
    support.update(user, cid, SupportInput(expected_version=1, values={'device': 'AX-25'}))
    now = utcnow() + timedelta(seconds=elapsed)
    repo, commands = rebuild(resources, lambda: now)
    commands.recover()
    commands.recover()
    row = repo.get(user, prepared['run_id'])
    assert row['claim_state'] == 'claimed'
    assert row['support_snapshot'] == frozen
    assert repo.db.messages.count_documents({'run_id': row['run_id'], 'role': 'user'}) == 1
    if elapsed:
        assert row['state'] == 'interrupted'
        assert repo.conversations.get(user, cid)['active_run_id'] is None
        next_run = RunService(repo).create(user, cid, RunInput(question='新轮', kb_id='k', client_request_id='after-timeout'))
        assert repo.get(user, next_run['run_id'])['support_snapshot']['slots']['device']['value'] == 'AX-25'
        repo.release(prepared)
        assert repo.conversations.get(user, cid)['active_run_id'] == next_run['run_id']
    else:
        assert row['state'] == 'pending'
        assert repo.conversations.get(user, cid)['active_run_id'] == row['run_id']


def test_unoccupied_correction_is_zero_message_and_eventually_terminal(support_client):
    resources, user, cid, support, prepared = setup(support_client)
    support.update(user, cid, SupportInput(expected_version=1, values={'device': 'AX-25'}))
    with pytest.raises(APIError) as error:
        resources['runs'].reconcile(user, prepared['run_id'])
    assert error.value.code == 'support_context_changed'
    repo, commands = rebuild(resources, lambda: utcnow() + timedelta(hours=1))
    commands.recover()
    commands.recover()
    assert repo.get(user, prepared['run_id'])['state'] == 'interrupted'
    assert repo.db.messages.count_documents({'run_id': prepared['run_id']}) == 0
    assert repo.conversations.get(user, cid)['active_run_id'] is None
    assert RunService(repo).create(user, cid, RunInput(question='新轮', kb_id='k', client_request_id='fresh'))['state'] == 'pending'


def test_correction_racing_before_occupation_keeps_version_gate(support_client, monkeypatch):
    resources, user, cid, support, prepared = setup(support_client)
    collection = resources['conversations'].conversations
    original = collection.update_one
    corrected = []
    def correct_before_cas(query, update, *args, **kwargs):
        if update.get('$set', {}).get('active_run_id') == prepared['run_id'] and not corrected:
            corrected.append(True)
            support.update(user, cid, SupportInput(expected_version=1, values={'device': 'AX-25'}))
        return original(query, update, *args, **kwargs)
    monkeypatch.setattr(collection, 'update_one', correct_before_cas)
    with pytest.raises(APIError) as error:
        resources['runs'].reconcile(user, prepared['run_id'])
    assert error.value.code == 'support_context_changed'
    assert resources['db'].messages.count_documents({'run_id': prepared['run_id']}) == 0
    assert resources['conversations'].get(user, cid)['active_run_id'] is None


def test_parallel_recovery_of_occupied_old_snapshot_is_idempotent(support_client, monkeypatch):
    resources, user, cid, support, prepared = setup(support_client)
    stop_after_occupation(resources, user, prepared, monkeypatch)
    support.update(user, cid, SupportInput(expected_version=1, values={'device': 'AX-25'}))
    def recover(_):
        repo, commands = rebuild(resources, utcnow)
        try:
            return repo.reconcile(user, prepared['run_id'])
        except APIError as error:
            if error.code != 'support_context_changed':
                raise
            return repo.get(user, prepared['run_id'])
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(recover, range(8)))
    assert all(row['claim_state'] == 'claimed' for row in rows)
    assert resources['db'].messages.count_documents({'run_id': prepared['run_id'], 'role': 'user'}) == 1
    assert resources['conversations'].get(user, cid)['active_run_id'] == prepared['run_id']


def test_archived_occupied_preparing_run_is_terminated_without_blocking_scan(support_client, monkeypatch):
    resources, user, cid, support, prepared = setup(support_client)
    stop_after_occupation(resources, user, prepared, monkeypatch)
    archived = resources['conversations'].patch(user, cid, ConversationPatch(expected_version=0, archived=True))
    assert archived['archived'] is True

    repo, commands = rebuild(resources, lambda: utcnow() + timedelta(hours=1))
    direct = repo.reconcile(user, prepared['run_id'])
    assert direct['state'] == 'interrupted'
    # 归档后的占用不能再次进入同一 reconcile 递归；恢复扫描应收敛并释放自身占用。
    commands.recover()
    row = repo.get(user, prepared['run_id'])
    assert row['state'] == 'interrupted'
    assert repo.conversations.get(user, cid)['active_run_id'] is None
    assert repo.db.messages.count_documents({'run_id': prepared['run_id']}) == 0
    assert [event['type'] for event in commands.events.read(user, prepared['run_id'])] == ['run.interrupted']


def test_archived_worker_start_persists_replayable_terminal_event(support_client, monkeypatch):
    """worker先于恢复扫描启动时，归档终态必须仍走事件账本。"""
    resources, user, cid, support, prepared = setup(support_client)
    stop_after_occupation(resources, user, prepared, monkeypatch)
    resources['conversations'].patch(user, cid, ConversationPatch(expected_version=0, archived=True))

    repo, commands = rebuild(resources, utcnow)
    with pytest.raises(APIError) as error:
        commands.start(user, prepared['run_id'])
    assert error.value.code == 'state_conflict'
    row = repo.get(user, prepared['run_id'])
    assert row['state'] == 'interrupted'
    assert row['seq'] == 1
    assert row['outbox'] == []
    events = commands.events.read(user, prepared['run_id'])
    assert [event['type'] for event in events] == ['run.interrupted']
    assert events[0]['payload'] == {'reason': 'conversation_archived'}

    rebuilt = rebuild(resources, utcnow)[1]
    assert rebuilt.recover() == []
    assert rebuilt.events.read(user, prepared['run_id']) == events


def test_archived_run_does_not_stop_recovery_of_another_conversation(support_client, monkeypatch):
    resources, user, cid, support, prepared = setup(support_client)
    stop_after_occupation(resources, user, prepared, monkeypatch)
    resources['conversations'].patch(user, cid, ConversationPatch(expected_version=0, archived=True))

    from app.conversations.models import ConversationInput
    other_cid = resources['conversations'].create(user, ConversationInput(kb_id='k'))['conversation_id']
    other = resources['runs'].prepare(user, other_cid, RunInput(question='另一账本', kb_id='k', client_request_id='other-recovery'))
    repo, commands = rebuild(resources, lambda: utcnow() + timedelta(hours=1))
    recovered = commands.recover()

    assert prepared['run_id'] in recovered
    assert other['run_id'] in recovered
    assert repo.get(user, prepared['run_id'])['state'] == 'interrupted'
    assert repo.get(user, other['run_id'])['state'] == 'interrupted'
    assert repo.conversations.get(user, cid)['active_run_id'] is None
    assert repo.conversations.get(user, other_cid)['active_run_id'] is None


def test_archived_claimed_pending_run_is_terminal_and_recovery_is_idempotent(support_client):
    resources, user, cid, support, prepared = setup(support_client)
    claimed = resources['run_service'].create(user, cid,
        RunInput(question='已领取后归档', kb_id='k', client_request_id='claimed-archive'))
    assert claimed['state'] == 'pending'
    archived = resources['conversations'].patch(user, cid, ConversationPatch(expected_version=0, archived=True))
    assert archived['archived'] is True

    repo, commands = rebuild(resources, lambda: utcnow() + timedelta(hours=1))
    commands.recover()
    commands.recover()
    row = repo.get(user, claimed['run_id'])
    assert row['state'] == 'interrupted' and row['error']['code'] == 'conversation_archived'
    assert row['claim_state'] == 'rejected'
    assert repo.conversations.get(user, cid)['active_run_id'] is None
    assert repo.db.messages.count_documents({'run_id': claimed['run_id'], 'role': 'user'}) == 1
    assert [event['type'] for event in commands.events.read(user, claimed['run_id'])] == ['run.interrupted']
