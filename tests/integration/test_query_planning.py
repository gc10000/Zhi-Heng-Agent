"""真实Mongo验证主体路由；检索与模型注入，不调用供应商。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from app.knowledge.api import ProductInput
from tests.integration.test_query_runs import query_context
from tests.integration.test_run_claim import request, run_context

pytestmark = pytest.mark.integration


@pytest.fixture
def planning_context(query_context):
    user, cid, conv, repo, service, g, runner, first, a = query_context
    b = g.add_product(user, 'k', ProductInput(kb_id='k', model='AX-48', aliases=['乙型电源']))
    scoped = g.repo('k')
    doc = scoped.register_document('second', name='48V合成手册', product_ids=[b['product_id']])
    rev = scoped.create_revision(doc.document_id, 'r2', original_sha256='b'*64, object_key='m4-test/planner/second')
    scoped.documents.update_one({'document_id': doc.document_id}, {'$set': {'active_revision_id': rev.revision_id}})
    second = deepcopy(first) | {'chunk_uid': 'chunk-second', 'document_id': doc.document_id,
        'revision_id': rev.revision_id, 'text': '设备输入为48V。'}
    second['metadata']['product_ids']=[b['product_id']]
    for ref in second['metadata']['source_refs']:
        ref.update(document_id=doc.document_id, revision_id=rev.revision_id)
    calls = []
    class Index:
        def search(self, scoped, text, **kwargs):
            ids = kwargs['product_ids']; calls.append(tuple(ids))
            return [{'entity': row} for pid, row in [(a['product_id'], first), (b['product_id'], second)] if not ids or pid in ids]
    g.index_factory = Index
    runner.embedder = lambda texts: {'dense': [[1., 0.] for _ in texts], 'sparse': [{1: .5} for _ in texts]}
    class Model:
        def stream(self, prompt, **options): yield SimpleNamespace(content='根据当前资料给出设备供电说明。')
    runner.llm_factory = Model
    return query_context, a, b, calls


def test_explicit_model_switch_overrides_old_selection_without_rewriting_messages(planning_context):
    ctx, a, b, calls = planning_context
    user, cid, conv, repo, service, g, runner, *_ = ctx
    rid = service.create(user, cid, request(question='改看AX-48，它的供电是多少？'))['run_id']
    original = conv.history(user, cid)['items'][0]
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'completed' and row['product_snapshot']['product_ids'] == [b['product_id']]
    assert calls == [(b['product_id'],)]
    assert conv.history(user, cid)['items'][0] == original


def test_near_model_never_answers_using_old_selected_product(planning_context):
    ctx, a, b, calls = planning_context
    user, cid, conv, repo, service, g, runner, *_ = ctx
    rid = service.create(user, cid, request(question='AX-42输入电压是多少？'))['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'awaiting_input' and calls == []
    assert {c['product_id'] for c in row['candidates']} == {a['product_id'], b['product_id']}
    assert conv.messages.count_documents({'run_id': rid, 'role': 'assistant'}) == 0


def test_comparison_retrieves_each_confirmed_product_in_its_own_scope(planning_context):
    ctx, a, b, calls = planning_context
    user, cid, conv, repo, service, g, runner, *_ = ctx
    rid = service.create(user, cid, request(question='比较AX-24和AX-48的供电要求。'))['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'completed'
    assert set(calls) == {(a['product_id'],), (b['product_id'],)}
    assert row.get('query_plan', {}).get('route') == 'compare'
    assert len({c['document_id'] for c in row['citations']}) == 2


def test_followup_without_explicit_input_uses_last_confirmed_snapshot(planning_context):
    ctx, a, b, calls = planning_context
    user, cid, conv, repo, service, g, runner, *_ = ctx
    previous = {'product_ids': [b['product_id']], 'version': 0}
    conv.append_message(user, cid, run_id='previous', role='user', text='我现在使用AX-48', product_snapshot=previous)
    conv.append_message(user, cid, run_id='previous', role='assistant', text='已确认设备。', product_snapshot=previous)
    rid = service.create(user, cid, request(question='它的供电是多少？'))['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'completed' and row['product_snapshot']['product_ids'] == [b['product_id']]
    assert calls == [(b['product_id'],)]


def test_near_model_confirmation_resumes_once_and_preserves_input_snapshot(planning_context):
    from app.runs.commands import ConfirmInput
    ctx, a, b, calls = planning_context
    user, cid, conv, repo, service, g, runner, *_ = ctx
    rid = service.create(user, cid, request(question='AX-42供电'))['run_id']; runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'awaiting_input'
    original = conv.history(user, cid)['items'][0]
    runner.commands.confirm(user, rid, ConfirmInput(expected_version=row['version'], product_ids=[b['product_id']]))
    runner.execute(rid); runner.execute(rid)
    assert repo.get(user, rid)['state'] == 'completed' and calls == [(b['product_id'],)]
    assert conv.history(user, cid)['items'][0] == original
    assert conv.messages.count_documents({'run_id': rid, 'role': 'assistant'}) == 1


def test_general_question_clears_inherited_device_for_next_pronoun(planning_context):
    ctx, a, b, calls = planning_context
    user, cid, conv, repo, service, g, runner, *_ = ctx
    first = service.create(user, cid, request(question='不限定型号，通用问题：供电注意事项'))['run_id']
    runner.execute(first)
    assert repo.get(user, first)['state'] == 'completed' and repo.get(user, first)['product_snapshot']['product_ids'] == []
    second = service.create(user, cid, request(key='second', question='它具体如何供电'))['run_id']
    runner.execute(second)
    assert repo.get(user, second)['state'] == 'awaiting_input' and calls == [()]
