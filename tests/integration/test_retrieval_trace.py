"""真实独立Milvus/Mongo验证追踪，注入合成向量且不调用模型。"""
import os
from uuid import uuid4
import pytest
from app.knowledge.models import Chunk, SourceRef
from app.knowledge.index import V2Index
from app.knowledge.repository import KnowledgeRepository

pytestmark = pytest.mark.integration


def test_real_milvus_trace_preserves_baseline_selection_and_scope(mongo_db):
    from pymilvus import MilvusClient
    repo = KnowledgeRepository(mongo_db, kb_id='trace-kb', owner_id='trace-owner')
    client = MilvusClient(uri=os.environ['MILVUS_URL'])
    index = V2Index(client, 'm1_test_m4_trace_' + uuid4().hex, dense_dim=2)
    try:
        index.ensure_collection()
        document = repo.register_document('source', name='合成来源')
        revision = repo.create_revision(document.document_id, 'r1', original_sha256='a'*64, object_key='m4-test/trace/source')
        attempt = repo.claim_attempt(revision.revision_id, expected_attempt=0)
        chunks = [Chunk(chunk_uid=str(uuid4()), document_id=document.document_id, revision_id=revision.revision_id,
            section_id='section', ordinal=i, text=f'合成参数{i}', product_ids=('AX',),
            source_refs=(SourceRef(document_id=document.document_id, revision_id=revision.revision_id, kind='pdf', page=i+1),))
            for i in range(2)]
        index.write_revision(repo, revision.revision_id, chunks, attempt=attempt,
            embedder=lambda texts: {'dense': [[1., 0.], [.8, .2]], 'sparse': [{1: .7}, {1: .5}]})
        arguments = {'embedder': lambda texts: {'dense': [[1., 0.]], 'sparse': [{1: .7}]},
            'revision_snapshot': [{'document_id': document.document_id, 'active_revision_id': revision.revision_id}],
            'product_ids': ('AX',), 'limit': 2}
        original = index.search(repo, '合成问题', trace=False, **arguments)
        traced = index.search(repo, '合成问题', **arguments)
        assert [(h['entity'], h['distance']) for h in traced] == [(h['entity'], h['distance']) for h in original]
        for hit in traced:
            assert [s['stage'] for s in hit['retrieval_trace']] == ['dense', 'learned_sparse', 'weighted_fusion']
            assert hit['retrieval_trace'][-1]['score'] == hit['distance']
            assert all(s['rank'] >= 1 for s in hit['retrieval_trace'])
        arguments['product_ids'] = ('other-product',)
        assert not index.search(repo, '合成问题', **arguments)
    finally:
        client.close()
