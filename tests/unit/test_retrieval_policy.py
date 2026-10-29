"""离线验证策略门禁、实际Milvus请求与分数含义。"""
from types import SimpleNamespace
import pytest
from app.knowledge.index import V2Index
from app.retrieval.search import RetrievalPolicy


@pytest.mark.parametrize('override', [dict(context_limit=21), dict(rerank_limit=21),
    dict(dense_limit=0), dict(sparse_limit=-1), dict(dense_limit=True), dict(rrf_k=0),
    dict(fusion='bm25'), dict(dense_weight=0, sparse_weight=0), dict(sparse_weight=float('nan')),
    dict(fusion_limit=1001), dict(unrecognized=2), dict(fusion='dense', dense_limit=19)])
def test_invalid_policy_rejected(override):
    with pytest.raises(ValueError): RetrievalPolicy(**override)


def test_environment_load_and_safe_validation(monkeypatch):
    monkeypatch.setenv('RETRIEVAL_POLICY_JSON', '{"context_limit": 3}')
    assert RetrievalPolicy.load().context_limit == 3
    monkeypatch.setenv('RETRIEVAL_POLICY_JSON', 'private-invalid-value')
    with pytest.raises(ValueError, match='RETRIEVAL_POLICY_JSON') as error: RetrievalPolicy.load()
    assert 'private-invalid-value' not in str(error.value)


@pytest.mark.parametrize('fusion,stage,kind', [('weighted', 'weighted_fusion', 'milvus_weighted_ip'),
    ('rrf', 'rrf', 'reciprocal_rank'), ('dense', 'dense', 'inner_product'),
    ('learned_sparse', 'learned_sparse', 'inner_product')])
def test_each_branch_shares_scope_and_uses_independent_limits(fusion, stage, kind):
    calls = []
    entity = dict(chunk_uid='c', document_id='d', revision_id='r', text='正文', metadata={})
    class Client:
        def hybrid_search(self, **kw):
            calls.append(('hybrid', kw)); return [[dict(entity=entity, distance=.6)]]
        def search(self, **kw):
            calls.append(('search', kw)); return [[dict(entity=entity, distance=.8)]]
    repo = SimpleNamespace(owner_id='owner', kb_id='kb', get_revision=lambda rid: {})
    policy = RetrievalPolicy(dense_limit=8, sparse_limit=6, fusion_limit=4, rerank_limit=3, context_limit=2, fusion=fusion)
    hits = V2Index(Client(), 'm1_test_policy', dense_dim=2).search(repo, '问题',
        embedder=lambda texts: dict(dense=[[1., 0.]], sparse=[{1: .5}]),
        revision_snapshot=[dict(active_revision_id='r')], product_ids=['p'], policy=policy)
    assert hits[0]['retrieval_trace'][-1]['stage'] == stage
    assert hits[0]['retrieval_trace'][-1]['score_kind'] == kind
    filters = []
    for name, call in calls:
        if name == 'hybrid':
            assert [r.limit for r in call['reqs']] == [8, 6]
            assert call['limit'] == 4
            filters.extend(r.expr for r in call['reqs'])
        else:
            filters.append(call['filter'])
            assert call['limit'] == (4 if fusion in {'dense', 'learned_sparse'} else
                8 if call['anns_field'] == 'dense_vector' else 6)
    assert len(set(filters)) == 1
    assert all(value in filters[0] for value in ['owner', 'kb', '"r"', '"p"'])


def test_empty_snapshot_never_loads_model_or_calls_client():
    index = V2Index(object(), 'm1_test_empty')
    def forbidden(*args): pytest.fail('空修订不编码')
    assert index.search(object(), '问题', embedder=forbidden, revision_snapshot=[]) == []


@pytest.mark.parametrize('fusion',['weighted','rrf','dense','learned_sparse'])
@pytest.mark.parametrize('exclude',[False,True])
def test_explicit_summary_quarantine_is_scoped_before_search(fusion,exclude):
    calls=[]
    class Client:
        def hybrid_search(self,**kw): calls.extend(r.expr for r in kw['reqs']);return [[]]
        def search(self,**kw): calls.append(kw['filter']);return [[]]
    repo=SimpleNamespace(owner_id='owner',kb_id='kb',get_revision=lambda rid:{})
    policy=RetrievalPolicy(fusion=fusion,exclude_image_descriptions=exclude)
    V2Index(Client(),'m1_test_quarantine',dense_dim=2).search(repo,'合成问题',
        embedder=lambda _:dict(dense=[[1.,0.]],sparse=[{1:.5}]),
        revision_snapshot=[dict(active_revision_id='r')],product_ids=['p'],policy=policy)
    assert calls and len(set(calls))==1
    assert all(('metadata["content_kind"] != "image_description"' in f)==exclude for f in calls)
    assert all(all(s in f for s in ['owner','kb','"r"','"p"']) for f in calls)
