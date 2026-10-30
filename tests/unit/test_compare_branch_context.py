"""比较渠道首证保留的合成边界；低分不等于不真实，保留不等于正确。"""
from copy import deepcopy
import json

import pytest

from app.retrieval.models import QueryPlan, RetrievalHit, StageScore
from app.retrieval.selection import select_context
from app.retrieval.compare_context import select_compare_branch_context


def choose(ranked, *, candidates, plan, limit=10):
    return select_compare_branch_context(ranked, candidates=candidates, plan=plan, limit=limit)


def plan(scopes=(('a',), ('b',)), queries=('原问题',), **overrides):
    return QueryPlan(original_query='合成比较问题', search_queries=queries,
                     product_ids=tuple(dict.fromkeys(p for s in scopes for p in s)),
                     revision_ids=('ra', 'rb', 'rab'), route='compare',
                     scope_groups=scopes, **overrides)


def hit(uid, product, *, heads=(), scope=None, query=0, branch_rank=2, products=None):
    scope = scope or (product,)
    stages = [StageScore(stage=channel, rank=1 if channel in heads else branch_rank,
                        score=0.2, score_kind='inner_product',
                        query_id=f'product:{scope[0]}/query:{query}/original')
              for channel in ('dense', 'learned_sparse')]
    stages.append(StageScore(stage='candidate_pool', rank=2, score_kind='rank_only',
        query_id=json.dumps(dict(scope=sorted(scope), query=query), sort_keys=True)))
    return RetrievalHit(document_id='d'+product, revision_id='r'+product, chunk_uid=uid,
        ordinal=1, text='合成原件 ' + uid,
        metadata=dict(product_ids=products or [product], source_refs=[
            dict(document_id='d'+product, revision_id='r'+product, kind='pdf', page=2)]),
        stages=stages)


def ranked(*rows):
    # 为合成分路的非首条证据分配互异名次；rank1和故意缺测原样保留。
    for position, h in enumerate(rows, 2):
        for stage in h.stages:
            if stage.stage in {'dense', 'learned_sparse'} and stage.rank == 2:
                stage.rank = position
    return [h.model_copy(deep=True, update=dict(stages=[*deepcopy(h.stages),
        StageScore(stage='rerank', rank=i, score=1 / (i+1), score_kind='model_relevance')]))
        for i, h in enumerate(rows, 1)]


def selected(rows):
    return rows.selected if hasattr(rows, 'selected') else rows


def ids(rows):
    return [h.chunk_uid for h in selected(rows)]


def test_low_rank_branch_head_survives_both_sides_without_increasing_budget():
    candidates=[hit('a0','a'),hit('b0','b')]+[hit('a'+str(i),'a') for i in range(1,8)]+[
        hit('sparse-low','b',heads=('learned_sparse',))]
    rows=ranked(*candidates);before=deepcopy(rows)
    choice=choose(rows,candidates=candidates,plan=plan(),limit=4)
    assert ids(choice)==['a0','b0','sparse-low','a1']
    assert rows==before and len(selected(choice))==4
    assert selected(choice)[2].stages[-1].rank==10


def test_canonical_scope_query_channel_order_then_original_rerank_fill():
    p=plan(scopes=(('b',),('a',)),queries=('q0','q1'))
    candidates=[hit('b0','b'),hit('a0','a'),hit('b-s','b',heads=('learned_sparse',)),
                hit('a-q1','a',heads=('dense',),query=1),
                hit('a-s','a',heads=('learned_sparse',)),hit('a-d','a',heads=('dense',))]
    choice=choose(ranked(*candidates),candidates=candidates,plan=p,limit=6)
    assert ids(choice)==['b0','a0','a-d','a-s','a-q1','b-s']


def test_shared_head_multiple_channels_and_scopes_occupies_one_slot():
    shared=hit('shared','ab',products=['a','b'],scope=('a',),heads=('dense','learned_sparse'))
    other=hit('shared','ab',products=['a','b'],scope=('b',),heads=('dense','learned_sparse'))
    shared.stages+=other.stages
    candidates=[shared,hit('fill','a')];rows=ranked(*candidates)
    choice=choose(rows,candidates=candidates,plan=plan(),limit=2)
    assert ids(choice)==['shared','fill']
    assert selected(choice)[0].stages==rows[0].stages
    assert hasattr(choice,'protected') and len(choice.protected)==1


def test_missing_head_never_promotes_rank2_or_reads_outside_rerank_pool():
    candidates=[hit('a0','a'),hit('b0','b'),hit('not-ranked','a',heads=('dense',))]
    choice=choose(ranked(*candidates)[:2],candidates=candidates,plan=plan())
    assert ids(choice)==['a0','b0']
    assert hasattr(choice,'missing_heads')
    assert any(r['reason']=='head_not_reranked' and r['chunk_uid']=='not-ranked'
               for r in choice.missing_heads)


def test_empty_scope_and_branch_do_not_fabricate_evidence():
    candidates=[hit('a0','a')]
    choice=choose(ranked(*candidates),candidates=candidates,plan=plan())
    assert ids(choice)==['a0']
    assert hasattr(choice,'missing_heads') and len(choice.missing_heads)==4


def test_protected_over_budget_fails_without_silently_dropping_head():
    candidates=[hit('a0','a'),hit('b0','b'),hit('low','a',heads=('dense',))]
    with pytest.raises(ValueError,match='预算'):
        choose(ranked(*candidates),candidates=candidates,plan=plan(),limit=2)


@pytest.mark.parametrize('field',['revision','product','source','pool_scope','pool_query','branch_query','pool_missing','branch_missing_pool','unconfirmed','conflict','rerank_text','rerank_trace','rerank_rank','multiple_heads','rank_missing'])
def test_invalid_identity_or_tracking_fails_closed(field):
    p=plan();candidates=[hit('a0','a'),hit('b0','b')]
    if field=='revision':candidates[0].revision_id='foreign'
    elif field=='product':candidates[0].metadata['product_ids']=['foreign']
    elif field=='source':candidates[0].metadata['source_refs'][0]['revision_id']='rb'
    elif field=='pool_scope':candidates[0].stages[-1].query_id=json.dumps(dict(scope=['b'],query=0))
    elif field=='pool_query':candidates[0].stages[-1].query_id=json.dumps(dict(scope=['a'],query=2))
    elif field=='branch_query':candidates[0].stages[0].query_id='product:a/query:2/original'
    elif field=='pool_missing':candidates[0].stages=candidates[0].stages[:-1]
    elif field=='branch_missing_pool':candidates[0].stages[0].query_id='product:b/query:0/original'
    elif field=='unconfirmed':p.unconfirmed_tokens=('unknown-device',)
    elif field=='conflict':candidates.append(candidates[0].model_copy(deep=True,update={'text':'冲突正文'}))
    elif field=='multiple_heads':
        candidates[0].stages[0].rank=1;candidates.append(hit('other-head','a',heads=('dense',)))
    elif field=='rank_missing':candidates[0].stages[0].rank=None
    rows=ranked(*candidates)
    if field=='rerank_text':rows[0].text='改变输入'
    elif field=='rerank_trace':rows[0].stages[0].rank=1
    elif field=='rerank_rank':rows[0].stages[-1].rank=2
    with pytest.raises(ValueError):choose(rows,candidates=candidates,plan=p)


@pytest.mark.parametrize('route',['answer','series','clarify','insufficient','general'])
def test_noncompare_completely_preserves_old_scope_first_output(route):
    candidates=[hit('a0','a'),hit('b0','b')];rows=ranked(*candidates)
    p=plan();p.route=route
    choice=choose(rows,candidates=candidates,plan=p,limit=1)
    assert selected(choice)==select_context(rows,limit=1,scope_groups=(),mode='scope_first_v1')


def test_single_scope_compare_preserves_old_output():
    candidates=[hit('a0','a'),hit('a1','a',heads=('dense',))];rows=ranked(*candidates)
    assert ids(choose(rows,candidates=candidates,plan=plan(scopes=(('a',),)),limit=1))==['a0']


@pytest.mark.parametrize('budget',[0,-1,True,1.2])
def test_invalid_budget_rejected(budget):
    with pytest.raises(ValueError):choose([],candidates=[],plan=plan(),limit=budget)
