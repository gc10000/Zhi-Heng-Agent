"""候选在融合、旧入口兼容和重排后仍保留阶段分数及真实来源。"""
import copy
from types import SimpleNamespace
import pytest
from app.knowledge.index import V2Index


def entity(uid='chunk', revision='revision'):
    return {'chunk_uid': uid, 'chunk_id': uid, 'document_id': 'document', 'revision_id': revision,
        'ordinal': 1, 'text': '额定电压24V', 'content': '额定电压24V',
        'metadata': {'source_refs': [{'kind': 'pdf', 'page': 2}], 'asset_ids': ['image'],
                     'heading_path': ['参数'], 'product_ids': ['AX']}}


def test_formal_index_keeps_dense_sparse_and_weighted_scores_separate():
    data = entity()
    class Client:
        def hybrid_search(self, **kwargs):
            return [[{'entity': copy.deepcopy(data), 'distance': 1.4}]]
        def search(self, **kwargs):
            score = .8 if kwargs['anns_field'] == 'dense_vector' else 2.5
            return [[{'entity': copy.deepcopy(data), 'distance': score}]]
    repo = SimpleNamespace(owner_id='owner', kb_id='kb', get_revision=lambda rid: {'revision_id': rid})
    hits = V2Index(Client(), 'm1_test_provenance', dense_dim=2).search(repo, '电压',
        embedder=lambda text: {'dense': [[1., 0.]], 'sparse': [{1: .5}]},
        revision_snapshot=[{'document_id': 'document', 'active_revision_id': 'revision'}], limit=20)
    assert hits[0].get('retrieval_trace') == [
        {'stage': 'dense', 'rank': 1, 'score': .8, 'score_kind': 'inner_product', 'query_id': 'original'},
        {'stage': 'learned_sparse', 'rank': 1, 'score': 2.5, 'score_kind': 'inner_product', 'query_id': 'original'},
        {'stage': 'weighted_fusion', 'rank': 1, 'score': 1.4, 'score_kind': 'milvus_weighted_ip', 'query_id': 'original'}]
    assert hits[0]['entity']['metadata'] == data['metadata']


def test_legacy_rrf_never_merges_equal_old_ids_across_revisions():
    from app.query_process.agent.nodes.node_rrf import reciprocal_rank_fusion
    before, after = entity(revision='old'), entity(revision='new')
    result = reciprocal_rank_fusion([([before, after], 1.)], k=60)
    assert len(result) == 2
    assert {doc['revision_id'] for doc, _ in result} == {'old', 'new'}


def test_legacy_rerank_normalization_keeps_revision_and_image_sources():
    from app.query_process.agent.nodes.node_rerank import step_1_merge_docs
    source = entity()
    docs = step_1_merge_docs({'rrf_chunks': [source]})
    assert docs[0].get('revision_id') == 'revision'
    assert docs[0].get('metadata') == source['metadata']


def test_legacy_rerank_keeps_distinct_rrf_score_and_provenance(monkeypatch):
    from app.query_process.agent.nodes import node_rerank
    doc = entity() | {'source': 'local', 'rrf_score': 1/61, 'retrieval_trace': [
        {'stage': 'rrf', 'rank': 1, 'score': 1/61, 'score_kind': 'reciprocal_rank', 'query_id': 'original'}]}
    monkeypatch.setattr(node_rerank, 'get_reranker_model', lambda: SimpleNamespace(compute_score=lambda pairs: [.75]))
    result = node_rerank.step_2_rerank_docs({'original_query': '电压'}, [doc])
    assert result[0].get('revision_id') == 'revision'
    assert result[0].get('rrf_score') == 1/61
    assert result[0].get('retrieval_trace', [])[:1] == doc['retrieval_trace']
    assert result[0]['retrieval_trace'][-1]['stage'] == 'rerank'
    assert result[0]['retrieval_trace'][-1]['score'] == .75


def test_typed_candidates_deduplicate_same_identity_without_aliasing_sources():
    from app.retrieval.adapters import from_index_hits
    data = entity()
    hits = from_index_hits([{'entity': data}, {'entity': data}])
    assert len(hits) == 1
    hits[0].document()['metadata']['source_refs'][0]['page'] = 99
    assert data['metadata']['source_refs'][0]['page'] == 2
    assert hits[0].metadata['source_refs'][0]['page'] == 2


def test_typed_candidates_keep_equal_chunk_ids_in_distinct_revisions():
    from app.retrieval.adapters import from_index_hits
    hits = from_index_hits([{'entity': entity(revision='old')}, {'entity': entity(revision='new')}])
    assert len(hits) == 2


def test_conflicting_payload_for_one_identity_rejected():
    from app.retrieval.adapters import from_index_hits
    with pytest.raises(ValueError):
        from_index_hits([{'entity': entity()}, {'entity': entity() | {'text': '不同原文'}}])


@pytest.mark.parametrize('invalid', [float('nan'), float('inf'), -float('inf')])
def test_stage_score_rejects_non_finite_values(invalid):
    from app.retrieval.models import StageScore
    with pytest.raises(ValueError): StageScore(stage='dense', rank=1, score=invalid, score_kind='inner_product')


def test_context_selection_cannot_insert_image_from_unranked_hit():
    from app.retrieval.adapters import from_index_hits
    from app.retrieval.models import EvidencePack, QueryPlan
    first, excluded = from_index_hits([{'entity': entity()}, {'entity': entity(uid='excluded')}])
    with pytest.raises(ValueError):
        EvidencePack(plan=QueryPlan(original_query='电压'), candidates=[first, excluded], reranked=[first], selected=[excluded])


def test_legacy_rrf_keeps_both_input_traces_and_counts_duplicate_once():
    from app.query_process.agent.nodes.node_rrf import reciprocal_rank_fusion
    original = entity()
    result = reciprocal_rank_fusion([([original, original], 1.), ([original], 1.)], k=60)
    assert len(result) == 1 and result[0][1] == pytest.approx(2/61)
    assert [s['query_id'] for s in result[0][0]['retrieval_trace']] == ['rrf_input_0', 'rrf_input_1']
    assert 'retrieval_trace' not in original
