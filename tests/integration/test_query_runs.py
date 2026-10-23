"""真实Mongo运行接线；模型端口注入，供应商验证另行记录。"""
import pytest
from app.runs.events import EventLedger
from app.runs.commands import RunCommands
from tests.integration.test_run_claim import run_context, request

pytestmark = pytest.mark.integration


@pytest.fixture
def query_context(run_context):
    from types import SimpleNamespace
    from app.knowledge.gateway import KnowledgeGateway
    from app.runs.query_runner import QueryRunner
    from app.knowledge.api import ProductInput
    user, cid, conv, repo, service = run_context
    g = KnowledgeGateway(repo.db, None, owner_id='organization')
    product = g.add_product(user, 'k', ProductInput(kb_id='k', model='AX-24'))
    conv.conversations.update_one({'conversation_id': cid}, {'$set': {'product_ids': [product['product_id']]}})
    knowledge = g.repo('k')
    doc = knowledge.register_document('one', name='参数手册', product_ids=[product['product_id']])
    rev = knowledge.create_revision(doc.document_id, 'one', original_sha256='a'*64, object_key='isolated/one.md')
    knowledge.documents.update_one({'document_id': doc.document_id}, {'$set': {'active_revision_id': rev.revision_id}})
    entity = {'chunk_uid': 'chunk-one', 'text': '设备电源输入为24V。', 'document_id': doc.document_id,
              'revision_id': rev.revision_id, 'metadata': {'heading_path': ['电源'], 'asset_ids': [],
              'source_refs': [{'document_id': doc.document_id, 'revision_id': rev.revision_id, 'kind': 'markdown', 'line_start': 2}]}}
    class Index:
        def search(self, scoped, text, **kwargs):
            assert scoped.kb_id == 'k' and scoped.owner_id == 'organization'
            assert kwargs['product_ids'] == [product['product_id']]
            assert kwargs['revision_snapshot'] == [{'document_id': doc.document_id, 'active_revision_id': rev.revision_id}]
            return [{'entity': entity}]
    g.index_factory = Index
    class Model:
        def stream(self, prompt):
            assert '24V' in prompt
            for text in ['电源输入', '为24V。']:
                yield SimpleNamespace(content=text)
    commands = RunCommands(repo, EventLedger(repo))
    runner = QueryRunner(repo, commands, lambda: g, ranker=lambda question, docs: docs, llm_factory=Model)
    yield user, cid, conv, repo, service, g, runner, entity, product
    runner.close()


def test_success_persists_exact_answer_citations_and_single_terminal(query_context):
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    rid = service.create(user, cid, request())['run_id']
    runner.execute(rid)
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'completed' and row['answer'] == '电源输入为24V。'
    events = runner.events.read(user, rid)
    assert [e['type'] for e in events if e['type'].startswith('run.')] == ['run.started', 'run.completed']
    assert ''.join(e['payload']['text'] for e in events if e['type'] == 'answer.delta') == row['answer']
    assert row['citations'][0]['text'] == entity['text']
    assert row['citations'][0]['source_refs'][0]['line_start'] == 2
    messages = conv.history(user, cid)['items']
    assert len(messages) == 2 and messages[1]['text'] == row['answer']
    assert messages[1]['citations'] == row['citations']
    assert messages[1]['product_snapshot'] == row['product_snapshot']
    assert conv.get(user, cid)['active_run_id'] is None


def test_generation_failure_keeps_partial_and_stage_without_success_message(query_context):
    from types import SimpleNamespace
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    class Broken:
        def stream(self, prompt):
            yield SimpleNamespace(content='部分回答')
            raise TimeoutError('synthetic-private-url-or-token')
    runner.llm_factory = Broken
    rid = service.create(user, cid, request())['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'failed' and row['answer'] == '部分回答'
    assert row['error'] == {'code': 'query_execution_failed', 'stage': 'answer'}
    assert conv.messages.count_documents({'run_id': rid, 'role': 'assistant'}) == 0
    assert 'synthetic-private' not in str(runner.events.read(user, rid))


def test_cancel_during_generation_never_saves_success(query_context):
    from types import SimpleNamespace
    from app.runs.commands import VersionInput
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    rid = service.create(user, cid, request())['run_id']
    class Cancelled:
        def stream(self, prompt):
            runner.commands.cancel(user, rid, VersionInput(expected_version=repo.get(user, rid)['version']))
            yield SimpleNamespace(content='迟到答案')
    runner.llm_factory = Cancelled
    runner.execute(rid)
    assert repo.get(user, rid)['state'] == 'cancelled'
    assert conv.messages.count_documents({'run_id': rid, 'role': 'assistant'}) == 0
    assert not any(e['type'] == 'run.completed' for e in runner.events.read(user, rid))


def test_wait_confirm_then_new_execution_resumes_with_frozen_user_message(query_context):
    from app.knowledge.api import ProductInput
    from app.runs.commands import ConfirmInput
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    g.add_product(user, 'k', ProductInput(kb_id='k', model='AX-48'))
    conv.conversations.update_one({'conversation_id': cid}, {'$set': {'product_ids': []}})
    rid = service.create(user, cid, request())['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'awaiting_input' and len(row['candidates']) == 2
    runner.commands.confirm(user, rid, ConfirmInput(expected_version=row['version'], product_ids=[product['product_id']]))
    runner.execute(rid)
    assert repo.get(user, rid)['state'] == 'completed'
    messages = conv.history(user, cid)['items']
    assert messages[0]['product_snapshot']['product_ids'] == []
    assert messages[1]['product_snapshot']['product_ids'] == [product['product_id']]


def test_unknown_product_fails_before_retrieval(query_context):
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    data = request().model_copy(update={'product_ids': ['other-kb-product']})
    rid = service.create(user, cid, data)['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'failed' and row['error']['stage'] == 'product'
    assert row['citations'] == []


def test_generated_external_image_is_blocked_in_deltas_and_snapshot(query_context):
    from types import SimpleNamespace
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    class Model:
        def stream(self, prompt):
            for text in ['说明![拓扑', '](https://untrusted.invalid/private.png)', '。']:
                yield SimpleNamespace(content=text)
    runner.llm_factory = Model
    rid = service.create(user, cid, request())['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'completed'
    assert 'https://untrusted.invalid' not in row['answer']
    assert 'https://untrusted.invalid' not in str(runner.events.read(user, rid))
    assert 'https://untrusted.invalid' not in conv.history(user, cid)['items'][-1]['text']


def test_concurrent_conversations_never_mix_answers_or_events(query_context):
    from concurrent.futures import ThreadPoolExecutor
    from types import SimpleNamespace
    from app.conversations.models import ConversationInput
    from app.runs.models import RunInput
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    second = conv.create(user, ConversationInput(kb_id='k', product_ids=[product['product_id']]))['conversation_id']
    class Model:
        def stream(self, prompt):
            text = '甲会话独立' if '甲独有问题' in prompt else '乙会话独立'
            yield SimpleNamespace(content=text)
    runner.llm_factory = Model
    ids = [service.create(user, c, RunInput(question=q, client_request_id='parallel', kb_id='k'))['run_id']
           for c, q in [(cid, '甲独有问题'), (second, '乙独有问题')]]
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(runner.execute, ids))
    for rid, expected, forbidden in [(ids[0], '甲会话独立', '乙会话独立'), (ids[1], '乙会话独立', '甲会话独立')]:
        assert repo.get(user, rid)['answer'] == expected
        assert forbidden not in str(runner.events.read(user, rid))


def test_revoked_permission_stops_output_and_records_failure(query_context):
    from types import SimpleNamespace
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    repo.db.users.insert_one(user.model_dump(mode='json') | {'enabled': True})
    runner.identity_store = SimpleNamespace(users=repo.db.users)
    class Model:
        def stream(self, prompt):
            yield SimpleNamespace(content='尚未刷出的部分')
            repo.db.users.update_one({'user_id': user.user_id}, {'$set': {'kb_ids': []}})
            yield SimpleNamespace(content='撤权后禁止输出')
    runner.llm_factory = Model
    rid = service.create(user, cid, request())['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'failed'
    assert row['error']['code'] == 'authorization_revoked'
    assert '撤权后禁止输出' not in str(runner.events.read(user, rid))
    assert conv.messages.count_documents({'run_id': rid, 'role': 'assistant'}) == 0


def test_no_selected_evidence_returns_explicit_answer_without_model(query_context):
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    entity['text'] = '超长证据' * 4000
    runner.llm_factory = lambda: pytest.fail('所有证据超预算时不能调用模型')
    rid = service.create(user, cid, request())['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'completed' and row['citations'] == []
    assert '没有找到可用证据' in row['answer']


def test_orphaned_run_does_not_block_other_run_recovery(run_context):
    from app.conversations.models import ConversationInput
    from app.runs.commands import VersionInput
    user, cid, conv, repo, service = run_context
    orphan = service.create(user, cid, request())['run_id']
    conv.conversations.update_one({'conversation_id': cid}, {'$set': {'owner_id': 'synthetic-other-owner'}})
    second = conv.create(user, ConversationInput(kb_id='k'))['conversation_id']
    rid = service.create(user, second, request('second'))['run_id']
    commands = RunCommands(repo, EventLedger(repo))
    commands.cancel(user, rid, VersionInput(expected_version=0))
    assert commands.recover() == [rid]
    assert repo.get(user, rid)['state'] == 'cancelled'
    # 不接管异常归属、不删除现场，记录明确人工核对原因。
    saved = repo.runs.find_one({'run_id': orphan})
    assert saved['recovery_issue']['code'] == 'conversation_scope_mismatch'


def test_completed_snapshot_repairs_missing_assistant_after_process_restart(run_context):
    user, cid, conv, repo, service = run_context
    rid = service.create(user, cid, request())['run_id']
    commands = RunCommands(repo, EventLedger(repo))
    token = commands.start(user, rid)
    saved = {'text': '设备参数为24V', 'product_snapshot': {'product_ids': ['p'], 'version': 0},
             'citations': [{'citation_id': 'c', 'text': '24V'}]}
    commands.finish(user, rid, token, 'completed', {'answer': saved['text']},
                    fields={'answer': saved['text'], 'citations': saved['citations'], 'completion_snapshot': saved})
    # 模拟完成CAS后消息未投递，恢复扫描应依据已存快照补足，不能重跑模型。
    conv.messages.delete_one({'run_id': rid, 'role': 'assistant'})
    rebuilt = RunCommands(repo, EventLedger(repo))
    rebuilt.recover()
    rebuilt.recover()
    messages = conv.history(user, cid)['items']
    assert [m['role'] for m in messages] == ['user', 'assistant']
    assert messages[1]['text'] == saved['text']
    assert messages[1]['citations'] == saved['citations']
    assert messages[1]['product_snapshot'] == saved['product_snapshot']
