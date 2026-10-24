"""真实Mongo执行入口验证各阶段数量；Milvus隔离范围另用合成向量复验。"""
from copy import deepcopy
import pytest
from tests.integration.test_run_claim import run_context, request
from tests.integration.test_query_runs import query_context

pytestmark = pytest.mark.integration


def test_stage_limits_reach_actual_ranker_and_answer_context(query_context):
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    runner.retrieval_policy = dict(dense_limit=8, sparse_limit=4, fusion_limit=6,
        rerank_limit=2, context_limit=1, fusion='rrf')
    calls = []
    class Index:
        def search(self, *args, **kwargs):
            calls.append(kwargs)
            return [{'entity': deepcopy(entity) | {'chunk_uid': f'chunk-{i}'}} for i in range(6)]
    g.index_factory = Index
    rank_inputs = []
    runner.ranker = lambda q, docs: rank_inputs.append(docs) or docs
    rid = service.create(user, cid, request())['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'completed'
    assert len(rank_inputs[0]) == 2, '融合池不能全部传入受限重排'
    assert len(row['citations']) == 1, '实际上下文须使用独立数量上限'
    assert calls[0]['policy']['dense_limit'] == 8
    assert calls[0]['policy']['sparse_limit'] == 4
    assert calls[0]['limit'] == 6
    assert sum(t['selected'] for t in row['retrieval_trace']) == 1
    assert row['retrieval_policy']['fusion'] == 'rrf'


def test_context_larger_than_legacy_ten_is_not_silently_truncated(query_context):
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    runner.retrieval_policy = dict(dense_limit=20, sparse_limit=20, fusion_limit=16,
        rerank_limit=15, context_limit=12, fusion='weighted')
    class Index:
        def search(self, *args, **kwargs):
            return [{'entity': deepcopy(entity) | {'chunk_uid': f'chunk-{i}'}} for i in range(16)]
    g.index_factory = Index
    # 使用正式重排函数，注入本机模型端口，不加载真实权重。
    from app.runs import query_runner
    from app.lm import reranker_utils
    from types import SimpleNamespace
    from unittest.mock import patch
    with patch.object(reranker_utils, 'get_reranker_model', return_value=SimpleNamespace(
        compute_score=lambda pairs, **kw: [.9 for _ in pairs])):
        runner.ranker = query_runner.rerank
        rid = service.create(user, cid, request())['run_id']; runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'completed'
    assert len(row['citations']) == 12, '配置接通后不能被旧重排硬截为10条'


@pytest.mark.parametrize('fusion', ['weighted', 'rrf', 'dense', 'learned_sparse'])
def test_real_milvus_never_crosses_owner_kb_revision_or_product(mongo_db, fusion):
    import os
    from uuid import uuid4
    from pymilvus import MilvusClient
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.index import V2Index
    from app.knowledge.models import Chunk
    from app.retrieval.search import RetrievalPolicy
    client = MilvusClient(uri=os.environ['MILVUS_URL'])
    index = V2Index(client, 'm1_test_m4_scope_' + uuid4().hex, dense_dim=2)
    try:
        index.ensure_collection()
        current = None
        for i, (owner, kb, product) in enumerate([('mine','kb','p'), ('other','kb','p'),
            ('mine','other','p'), ('mine','kb','other'), ('mine','kb','p')]):
            repo = KnowledgeRepository(mongo_db, owner_id=owner, kb_id=kb)
            doc = repo.register_document(f'synthetic-{i}', name='合成隔离资料')
            rev = repo.create_revision(doc.document_id, 'v1', original_sha256='a'*64, object_key='m4-test/scopes/source')
            attempt = repo.claim_attempt(rev.revision_id, expected_attempt=0)
            chunks = [Chunk(chunk_uid=uuid4().hex, document_id=doc.document_id, revision_id=rev.revision_id,
                section_id='s', ordinal=0, text=f'隔离参数{i}', product_ids=(product,))]
            index.write_revision(repo, rev.revision_id, chunks, attempt=attempt,
                embedder=lambda texts: dict(dense=[[1., 0.]], sparse=[{1: .5}]))
            if i == 0: current = (repo, rev.revision_id, chunks[0].chunk_uid)
        repo, rid, uid = current
        policy = RetrievalPolicy(fusion=fusion, dense_limit=8, sparse_limit=6,
            fusion_limit=4, rerank_limit=3, context_limit=2)
        args = dict(embedder=lambda texts: dict(dense=[[1., 0.]], sparse=[{1: .5}]),
            revision_snapshot=[dict(active_revision_id=rid)], product_ids=['p'], policy=policy)
        hits = index.search(repo, '参数', **args)
        assert [h['entity']['chunk_uid'] for h in hits] == [uid]
        assert all(h['entity']['revision_id'] == rid for h in hits)
        args['product_ids'] = ['absent']
        assert index.search(repo, '参数', **args) == []
    finally:
        client.close()
