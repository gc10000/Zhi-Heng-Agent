"""来源装配仅消费完整冻结池，不猜资料缺失或静默截断必要原文。"""
from copy import deepcopy
import importlib

import pytest

from app.knowledge.models import content_hash
from app.knowledge.repository import fingerprint


def row(uid, pid, ordinal, heading, text):
    did, rid = 'd-' + pid, 'r-' + pid
    return dict(chunk_uid=uid, owner_id='o', kb_id='k', document_id=did,
        revision_id=rid, ordinal=ordinal, text=text, content_sha256=content_hash(text.encode()),
        metadata=dict(product_ids=[pid], heading_path=heading, content_kind='text',
            source_refs=[dict(document_id=did, revision_id=rid, kind='pdf', page=None)]))


@pytest.fixture
def sources():
    pool = [row('pa', 'p', 0, ['1 产品简介'], '产品甲的介绍和完整限制。'),
        row('qa', 'q', 0, ['1.1 概述'], '产品乙的介绍和完整限制。'),
        row('pc', 'p', 1, ['2 连接'], '设备甲连接描述。'),
        row('qc', 'q', 1, ['2 连接'], '设备乙连接描述。'),
        row('cover', 'p', 2, ['版权'], '纯版权内容。')]
    scope = dict(owner_id='o', kb_id='k', revisions={'d-p': 'r-p', 'd-q': 'r-q'},
        product_ids=['p', 'q'])
    return pool, dict(product_ids=['p', 'q'], scope=scope,
        frozen_payloads={r['chunk_uid']: fingerprint(r) for r in pool},
        required_chunk_uids=['pc', 'qc'], max_docs=4, max_chars=6000)


def assemble(selected, pool, **kwargs):
    try:
        module = importlib.import_module('app.answering.comparison_context')
    except ModuleNotFoundError:
        pytest.fail('缺少通用冻结来源装配单元')
    return module.assemble_comparison_context(selected, pool, **kwargs)


def test_introductions_replace_optional_source_within_budget(sources):
    pool, kw = sources
    result = assemble(pool[2:], pool, **kw)
    assert result.status == 'complete'
    assert {r['chunk_uid'] for r in result.documents} == {'pa', 'qa', 'pc', 'qc'}
    assert result.dropped == [dict(chunk_uid='cover', reason='optional_source_budget')]
    assert {x['product_id'] for x in result.dependencies} == {'p', 'q'}


def test_required_sources_cannot_overflow_or_truncate(sources):
    pool, kw = sources
    for overrides in [dict(max_docs=3), dict(max_chars=5)]:
        result = assemble(pool[2:], pool, **(kw | overrides))
        assert result.status == 'required_source_budget_exceeded'
        assert result.documents == []


def test_no_implicit_permission_to_drop_selected_evidence(sources):
    pool, kw = sources
    kw.pop('required_chunk_uids')
    result = assemble(pool[2:], pool, **kw)
    assert result.status == 'required_source_budget_exceeded'
    assert result.documents == []


def test_full_section_includes_child_condition_and_preserves_unknown_page(sources):
    pool, kw = sources
    extra = row('condition', 'p', 1, ['1 产品简介', '限制'], '仅在条件A成立时支持；不证明已连通。')
    pool.append(extra)
    kw['frozen_payloads'][extra['chunk_uid']] = fingerprint(extra)
    result = assemble(pool[2:4], pool, **(kw | dict(max_docs=5)))
    assert result.status == 'complete'
    assert next(r for r in result.documents if r['chunk_uid'] == 'condition') == extra
    assert all(r['metadata']['source_refs'][0]['page'] is None for r in result.documents)


@pytest.mark.parametrize('field', ['text', 'metadata', 'ordinal', 'document_id', 'revision_id',
    'owner_id', 'kb_id', 'content_sha256'])
def test_payload_or_scope_drift_is_rejected(sources, field):
    pool, kw = sources
    changed = deepcopy(pool)
    changed[0][field] = {} if field == 'metadata' else 99 if field == 'ordinal' else '漂移'
    with pytest.raises(ValueError):
        assemble(changed[2:], changed, **kw)


def test_incomplete_frozen_pool_is_not_treated_as_unique_introduction(sources):
    pool, kw = sources
    with pytest.raises(ValueError, match='完整'):
        assemble(pool[2:], pool[1:], **kw)


def test_frozen_missing_intro_is_explicit_and_does_not_publish_partial_answer(sources):
    pool, kw = sources
    pool = [r for r in pool if r['chunk_uid'] != 'pa']
    kw['frozen_payloads'].pop('pa')
    result = assemble(pool[1:], pool, **kw)
    assert result.status == 'missing_required_source'
    assert result.documents == []
    assert result.issues == [dict(product_id='p', code='introduction_not_in_frozen_pool')]


@pytest.mark.parametrize('shared', [False, True])
def test_multiple_or_shared_introductions_are_ambiguous(sources, shared):
    pool, kw = sources
    extra = row('other', 'p', 4, ['3 产品概述'], '另一段介绍，不允许猜选。')
    if shared:
        extra['metadata']['product_ids'] = ['p', 'q']
    pool.append(extra)
    kw['frozen_payloads']['other'] = fingerprint(extra)
    result = assemble(pool[2:4], pool, **kw)
    assert result.status == 'ambiguous'
    assert result.documents == []


def test_order_is_stable_and_inputs_not_mutated(sources):
    pool, kw = sources
    original = deepcopy(pool)
    first = assemble(pool[2:], pool, **kw)
    second = assemble(pool[2:], list(reversed(pool)), **kw)
    assert first == second
    assert pool == original
    assert len(first.identity_sha256) == 64
    first.documents[0]['text'] = '结果的可变副本'
    assert pool == original


def test_duplicate_selected_source_or_pool_member_is_rejected(sources):
    pool, kw = sources
    for selected, source_pool in [(pool[2:] + [pool[2]], pool), (pool[2:], pool + [pool[0]])]:
        with pytest.raises(ValueError, match='重复'):
            assemble(selected, source_pool, **kw)


def test_selected_source_is_rebound_not_only_uid_checked(sources):
    pool, kw = sources
    selected = deepcopy(pool[2:])
    selected[0]['text'] = '相同uid不同正文'
    with pytest.raises(ValueError):
        assemble(selected, pool, **kw)


def test_required_set_is_bound_and_identity_tracks_input_budget(sources):
    pool, kw = sources
    with pytest.raises(ValueError):
        assemble(pool[2:], pool, **(kw | dict(required_chunk_uids=['not-in-input'])))
    a = assemble(pool[2:], pool, **kw)
    b = assemble(pool[2:], pool, **(kw | dict(max_chars=6001)))
    assert a.identity_sha256 != b.identity_sha256


@pytest.mark.parametrize('heading', [['仅标题提到概述但不是目录'], ['产品简介示例'], ['9 产品概述附录']])
def test_title_substrings_do_not_create_an_introduction(sources, heading):
    pool, kw = sources
    pool[0]['metadata']['heading_path'] = heading
    kw['frozen_payloads']['pa'] = fingerprint(pool[0])
    result = assemble(pool[2:], pool, **kw)
    assert result.status == 'missing_required_source'
