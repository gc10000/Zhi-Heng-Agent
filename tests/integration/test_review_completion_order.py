"""完成CAS与消息物化窗口：真实Mongo、多实例和实际生成上下文。"""
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest
from tests.integration.test_query_runs import query_context
from tests.integration.test_run_claim import run_context, request
from app.conversations.repository import ConversationRepository
from app.runs.repository import RunRepository
from app.runs.service import RunService
from app.runs.commands import RunCommands
from app.runs.events import EventLedger

pytestmark = pytest.mark.integration


def rebuild(repo):
    repository = RunRepository(repo.db, ConversationRepository(repo.db))
    return repository, RunCommands(repository, EventLedger(repository))


def complete_without_message(user, rid, repo, monkeypatch):
    commands = RunCommands(repo, EventLedger(repo))
    token = commands.start(user, rid)
    saved = {'text': '上一轮正确答案：设备电源为24V。', 'product_snapshot': repo.get(user, rid)['product_snapshot'], 'citations': []}
    original = repo.conversations.append_message
    with monkeypatch.context() as patch:
        def fail(*args, **kwargs):
            if kwargs.get('role') == 'assistant':
                raise OSError('synthetic assistant storage failure')
            return original(*args, **kwargs)
        patch.setattr(repo.conversations, 'append_message', fail)
        try:
            commands.finish(user, rid, token, 'completed', {'answer': saved['text']},
                fields={'answer': saved['text'], 'completion_snapshot': saved})
        except OSError:
            pass
    assert repo.get(user, rid)['state'] == 'completed'
    assert repo.conversations.messages.count_documents({'run_id': rid, 'role': 'assistant'}) == 0
    return saved


def test_completed_cas_then_next_create_repairs_order_and_actual_context(query_context, monkeypatch):
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    first = service.create(user, cid, request('one', '第一轮电源问题'))['run_id']
    saved = complete_without_message(user, first, repo, monkeypatch)
    rebuilt, commands = rebuild(repo)
    second = RunService(rebuilt).create(user, cid, request('two', '第二轮请继续'))['run_id']
    # 在周期恢复扫描前，下一轮必须已经能读到上一轮答案。
    assert [m['role'] for m in conv.history(user, cid)['items']] == ['user', 'assistant', 'user']
    contexts = []
    class Model:
        def stream(self, prompt, **options):
            contexts.append(str(prompt))
            assert saved['text'] in str(prompt)
            yield SimpleNamespace(content='第二轮正确回答。')
    runner.repo, runner.commands, runner.events = rebuilt, commands, commands.events
    runner.llm_factory = Model
    runner.execute(second)
    commands.recover()
    assert rebuilt.get(user, second)['state'] == 'completed' and len(contexts) == 1
    messages = conv.history(user, cid)['items']
    assert [(m['run_id'], m['role']) for m in messages] == [(first, 'user'), (first, 'assistant'), (second, 'user'), (second, 'assistant')]
    assert messages[1]['text'] == saved['text']
    assert contexts[0].index('第一轮电源问题') < contexts[0].index(saved['text']) < contexts[0].index('第二轮请继续')


def test_failed_compensation_blocks_new_message_then_concurrent_rebuild_is_idempotent(run_context, monkeypatch):
    user, cid, conv, repo, service = run_context
    first = service.create(user, cid, request())['run_id']
    complete_without_message(user, first, repo, monkeypatch)
    rebuilt, commands = rebuild(repo)
    with monkeypatch.context() as patch:
        patch.setattr(rebuilt.conversations, 'append_message', lambda *a, **kw: (_ for _ in ()).throw(OSError('synthetic write failure')))
        with pytest.raises(OSError):
            RunService(rebuilt).create(user, cid, request('two'))
    assert conv.get(user, cid)['active_run_id'] == first
    assert conv.messages.count_documents({'conversation_id': cid}) == 1
    def recover_or_create(i):
        independent, recovery = rebuild(repo)
        if i % 2:
            recovery.recover()
        return RunService(independent).create(user, cid, request('two'))['run_id']
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(recover_or_create, range(16)))
    assert len(set(ids)) == 1
    second = ids[0]
    for _ in range(2):
        commands.recover()
        rebuilt.release(rebuilt.get(user, first))
    assert conv.get(user, cid)['active_run_id'] == second
    assert [m['role'] for m in conv.history(user, cid)['items']] == ['user', 'assistant', 'user']
    token = commands.start(user, second)
    commands.finish(user, second, token, 'completed', {}, fields={'completion_snapshot': {
        'text': '第二轮', 'product_snapshot': rebuilt.get(user, second)['product_snapshot'], 'citations': []}})
    commands.recover()
    seen, cursor = [], 0
    while True:
        page = conv.history(user, cid, after=cursor, limit=1)
        seen.extend(page['items'])
        if not page['next_cursor']:
            break
        cursor = int(page['next_cursor'])
    assert [m['role'] for m in seen] == ['user', 'assistant', 'user', 'assistant']
    assert len({m['message_id'] for m in seen}) == 4
    assert [m['ordinal'] for m in seen] == sorted({m['ordinal'] for m in seen})
