"""满池下范围与增强均有重排机会；不跨分支比较原始分数。"""
from copy import deepcopy
from collections import Counter
import time
import pytest
from app.retrieval.models import QueryPlan
from app.retrieval.search import retrieve, RetrievalPolicy
from app.retrieval.graph import run_retrieval_graph
from app.retrieval.adapters import from_index_hits
from app.retrieval.rerank import rank_hits


def row(uid, product='a', score=1.):
    return dict(entity=dict(document_id='doc-'+product, revision_id='rev-'+product,
        chunk_uid=uid, text='原始正文'+uid, metadata=dict(product_ids=[product],
        source_refs=[dict(kind='pdf', page=2)], asset_ids=[])), distance=score)


def plan(scopes=(('a',),), queries=('原问题',)):
    return QueryPlan(original_query='AX无法启动；同时指示灯不亮', product_ids=tuple(p for s in scopes for p in s),
        route='compare' if len(scopes)>1 else 'answer', scope_groups=scopes, search_queries=queries)


def search(p, operation):
    class Index:
        def search(self, repo, text, **kw):
            return operation(text, kw['product_ids'])
    return retrieve(Index(), None, p, embedder=None, revision_snapshot=[], policy=RetrievalPolicy())


def ranked(raw, limit=20):
    candidates=from_index_hits(raw); before=deepcopy(candidates)
    seen=[]
    def rank(q, docs):
        seen.extend(docs)
        return [d | dict(score=.8) for d in reversed(docs)]
    result=rank_hits('原问题', candidates, ranker=rank,
        policy=RetrievalPolicy(rerank_limit=limit, context_limit=min(10,limit)))
    assert candidates==before, '选择与重排不能修改候选正文、来源或原始分数'
    assert len(seen)==len({(d['document_id'],d['revision_id'],d['chunk_uid']) for d in seen})<=limit
    assert {h.identity for h in result}=={(d['document_id'],d['revision_id'],d['chunk_uid']) for d in seen}
    return seen


@pytest.mark.parametrize('scopes',[(('a',),('b',)),(('b',),('a',))])
def test_two_full_scopes_have_equal_opportunities_regardless_of_input_order(scopes):
    raw=search(plan(scopes), lambda q,ids:[row(str(i),ids[0],score=1e9 if ids==['a'] else -1e9) for i in range(20)])
    seen=ranked(raw)
    assert Counter(d['metadata']['product_ids'][0] for d in seen)=={'a':10,'b':10}
    assert [d['metadata']['product_ids'][0] for d in seen[:2]]==['a','b']


@pytest.mark.parametrize('enabled',[('hyde',),('decomposition',),('hyde','decomposition')])
@pytest.mark.parametrize('duplicates',[False,True])
def test_unique_enhancement_survives_full_local_pool_and_duplicate_prefixes(enabled,duplicates):
    def operation(q, ids):
        local=[row('local-'+str(i)) for i in range(20)]
        if '检索假设：' in q:return (local[:19] if duplicates else [])+[row('hyde-only',score=-1000.)]
        if '现象：' in q:return (local[:19] if duplicates else [])+[row('decomposition-only',score=-1e9)]
        return local
    p=plan();branches=run_retrieval_graph(p,lambda p:search(p,operation),
        policy={name+'_enabled':True for name in enabled},hyde=lambda *a:'只作查询的假设')
    raw=deepcopy(branches.hits);seen=ranked(raw)
    assert branches.merge_count==1
    assert {b['name'] for b in branches.branches if b['status']=='completed'}=={'local',*enabled}
    assert {name+'-only' for name in enabled}<={d['chunk_uid'] for d in seen}
    assert branches.hits==raw


def test_multiple_queries_are_not_starved_by_first_query_full_pool():
    seen=ranked(search(plan(queries=('first','second','third')),
        lambda q,ids:[row(q+'-'+str(i)) for i in range(20)]))
    counts=Counter(d['chunk_uid'].split('-')[0] for d in seen)
    assert counts=={'first':7,'second':7,'third':6}


def test_shared_identity_in_several_queries_only_consumes_one_slot():
    seen=ranked(search(plan(queries=('first','second')),
        lambda q,ids:[row('same')]*19+[row(q+'-only')]))
    assert {d['chunk_uid'] for d in seen}=={'same','first-only','second-only'}
    common=next(d for d in seen if d['chunk_uid']=='same')
    assert len({s['query_id'] for s in common['retrieval_trace'] if s['stage']=='candidate_pool'})==2


def test_empty_scope_redistributes_slots_and_single_scope_preserves_backend_rank():
    seen=ranked(search(plan((('a',),('b',))),
        lambda q,ids:[] if ids==['a'] else [row(str(i),'b') for i in range(20)]))
    assert [d['chunk_uid'] for d in seen]==[str(i) for i in range(20)]


def test_limit_smaller_than_nonempty_scopes_rejects_before_ranking():
    raw=search(plan((('a',),('b',))),lambda q,ids:[row('c',ids[0])])
    with pytest.raises(ValueError,match='范围'):
        ranked(raw,limit=1)


@pytest.mark.parametrize('fault',['timeout','failed'])
def test_optional_fault_keeps_full_local_pool_without_late_evidence(fault):
    def hyde(*a):
        if fault=='failed':raise TimeoutError('合成供应商故障')
        time.sleep(.08);return '晚到假设'
    p=plan();result=run_retrieval_graph(p,lambda p:search(p,lambda q,ids:[row(str(i)) for i in range(20)]),
        policy=dict(hyde_enabled=True,timeout_seconds=.02),hyde=hyde)
    seen=ranked(result.hits);snapshot=deepcopy(result)
    time.sleep(.1)
    assert len(seen)==20 and result==snapshot
    assert next(b for b in result.branches if b['name']=='hyde')['status']==fault


def test_legacy_unpartitioned_candidates_keep_order_and_empty_skips_ranker():
    assert [d['chunk_uid'] for d in ranked([row(str(i)) for i in range(30)])]==[str(i) for i in range(20)]
    assert rank_hits('q',[],ranker=lambda *a:pytest.fail('空池不得重排'),policy={})==[]
