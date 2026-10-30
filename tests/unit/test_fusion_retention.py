"""合成检索载荷；没有产品答案或题号特判。"""
from copy import deepcopy

import pytest

from app.retrieval.fusion_retention import retain_branch_heads


def hit(uid, score=0.25, **overrides):
    entity = dict(document_id='doc', revision_id='rev', chunk_uid=uid,
                  text='合成证据 ' + uid, ordinal=1,
                  metadata=dict(product_ids=['product'], source_refs=[])) | overrides
    return dict(entity=entity, distance=score)


def retain(weighted, dense, sparse, limit=3):
    return retain_branch_heads(weighted, dense, sparse, limit=limit,
                               revision_ids=['rev'], product_ids=['product'])


def ids(rows):
    return [r['entity']['chunk_uid'] for r in rows]


def test_branch_head_outside_weighted_enters_without_inventing_weighted_score():
    rows = retain([hit('a'), hit('b'), hit('c')], [hit('a', 2)], [hit('s', 7)])
    assert ids(rows) == ['a', 's', 'b']
    assert rows[1]['distance'] == 7
    assert not any(s['stage'] == 'weighted_fusion' for s in rows[1]['retrieval_trace'])
    assert any(s['stage'] == 'learned_sparse' and s['score'] == 7 for s in rows[1]['retrieval_trace'])


def test_shared_heads_deduplicate_and_fill_in_original_weighted_order():
    rows = retain([hit('b'), hit('a'), hit('c')], [hit('a')], [hit('a')])
    assert ids(rows) == ['a', 'b', 'c']


@pytest.mark.parametrize('branch', ['dense', 'sparse', 'weighted'])
def test_rejects_conflicting_payload_even_in_unselected_tail(branch):
    args = dict(weighted=[hit('a')], dense=[hit('a')], sparse=[hit('b')])
    args[branch].append(hit('a', text='同身份的不同正文'))
    with pytest.raises(ValueError, match='身份'):
        retain(**args)


@pytest.mark.parametrize('override', [dict(revision_id='other'), dict(metadata=dict(product_ids=['other'])), dict(metadata={})])
def test_rejects_scope_escape(override):
    with pytest.raises(ValueError, match='授权'):
        retain([hit('a')], [hit('a')], [hit('b', **override)])


@pytest.mark.parametrize('limit', [0, -1, True, 1.5])
def test_rejects_invalid_budget(limit):
    with pytest.raises(ValueError, match='预算'):
        retain([], [], [], limit=limit)


def test_budget_cannot_silently_drop_distinct_heads():
    with pytest.raises(ValueError, match='预算'):
        retain([hit('a')], [hit('a')], [hit('b')], limit=1)


def test_empty_and_single_branch_do_not_fabricate_evidence():
    assert retain([], [], []) == []
    assert ids(retain([], [], [hit('s')])) == ['s']


def test_input_immutable_and_weighted_scores_and_ranks_retained():
    args = ([hit('b', -0.5), hit('a', 0.8)], [hit('a')], [hit('b')])
    saved = deepcopy(args)
    rows = retain(*args)
    assert args == saved
    assert ids(rows) == ['a', 'b']
    assert rows[0]['distance'] == 0.8
    stage = next(s for s in rows[0]['retrieval_trace'] if s['stage'] == 'weighted_fusion')
    assert (stage['rank'], stage['score']) == (2, 0.8)


def test_source_identity_cannot_escape_through_metadata():
    with pytest.raises(ValueError, match='来源'):
        retain([], [], [hit('a', metadata=dict(product_ids=['product'], source_refs=[
            dict(document_id='doc', revision_id='other', page=3)]))])


def test_retention_keeps_existing_comparison_fairness_and_total_budget():
    from app.retrieval.adapters import from_index_hits, score_record
    from app.retrieval.selection import select_candidates
    import json
    rows = []
    for product in ['left', 'right']:
        def make(uid):
            return hit(uid, document_id=product, revision_id=product,
                       metadata=dict(product_ids=[product], source_refs=[]))
        scope = retain_branch_heads([make(product+str(i)) for i in range(20)],
                                    [make(product+'0')], [make(product+'s')], limit=20,
                                    revision_ids=[product], product_ids=[product])
        for rank, h in enumerate(scope, 1):
            h['retrieval_trace'].append(score_record('candidate_pool', rank, None, 'rank_only',
                json.dumps(dict(scope=[product], query=0))))
        rows.extend(scope)
    selected = select_candidates(from_index_hits(rows), 20)
    assert len(selected) == 20
    assert all(sum(h.revision_id == p for h in selected) == 10 for p in ['left', 'right'])
    assert {'lefts', 'rights'} <= {h.chunk_uid for h in selected}
