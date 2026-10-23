"""真实BGE dense/learned sparse与隔离Milvus小样；不调用LLM。"""
from uuid import uuid4
import os
import pytest

pytestmark=pytest.mark.integration


@pytest.fixture(scope='module')
def real_embedder():
    os.environ.update(LOG_CONSOLE_ENABLE='False',LOG_FILE_ENABLE='False',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parents[2]/'.env')
    from app.lm.embedding_utils import generate_embeddings
    return generate_embeddings


@pytest.fixture
def v2_setup(mongo_db):
    from pymilvus import MilvusClient
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.index import V2Index
    repo=KnowledgeRepository(mongo_db,kb_id='kb-"quoted-'+uuid4().hex,owner_id='test-owner')
    client=MilvusClient(uri=os.environ['MILVUS_URL'])
    index=V2Index(client,'m1_test_'+uuid4().hex+'_v2');index.ensure_collection()
    yield repo,index
    client.close()


def test_real_dual_vector_index_scopes_and_idempotence(v2_setup,real_embedder):
    from app.knowledge.models import Chunk,SourceRef
    repo,index=v2_setup
    d=repo.register_document('doc',name='测试手册')
    r=repo.create_revision(d.document_id,'r',original_sha256='a'*64,object_key='m1-test/original')
    attempt=repo.claim_attempt(r.revision_id,expected_attempt=0)
    c=Chunk(chunk_uid=str(uuid4()),document_id=d.document_id,revision_id=r.revision_id,section_id='s',ordinal=300,text='LA2608通过3G/4G网络连接无线控制器，使用display wlan ap检查R/M状态。',
            source_refs=(SourceRef(document_id=d.document_id,revision_id=r.revision_id,kind='pdf',page=1),),product_ids=('product"quoted',))
    manifest=index.write_revision(repo,r.revision_id,[c],attempt=attempt,embedder=real_embedder)
    assert manifest['count']==1
    assert index.write_revision(repo,r.revision_id,[c],attempt=attempt,embedder=lambda *a:pytest.fail('重试不重算向量'))==manifest
    from app.knowledge.repository import ConflictError
    with pytest.raises(ConflictError):
        index.write_revision(repo,r.revision_id,[c.model_copy(update={'heading_path':('不同来源',)})],attempt=attempt,embedder=lambda *a:pytest.fail('冲突应先于编码'))
    assert index.search(repo,'无线网关如何连通控制器',embedder=lambda *a:pytest.fail('无活动版本不应编码'))==[]
    snapshot=[{'document_id':d.document_id,'active_revision_id':r.revision_id}]
    hits=index.search(repo,'LA2608连接无线控制器',embedder=real_embedder,revision_snapshot=snapshot,product_ids=('product"quoted',))
    assert hits and hits[0]['entity']['chunk_uid']==c.chunk_uid
    assert hits[0]['entity']['ordinal']==300
    assert hits[0]['entity']['metadata']['source_refs'][0]['page']==1
    assert not index.search(repo,'LA2608',embedder=real_embedder,revision_snapshot=snapshot,product_ids=('not-matching',))
    from app.knowledge.repository import KnowledgeRepository,ScopeError
    other=KnowledgeRepository(repo.db,kb_id=repo.kb_id,owner_id='other')
    with pytest.raises(ScopeError):index.search(other,'x',embedder=real_embedder,revision_snapshot=snapshot)
