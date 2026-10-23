"""真实Mongo/Milvus发布边界，故障仅注入控制流，不破坏已有数据。"""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest
from tests.integration.test_v2_index import v2_setup,real_embedder

pytestmark=pytest.mark.integration


def make_revision(repo,index,document_id,key,embedder):
    from app.knowledge.models import Chunk,SourceRef,content_hash
    raw=b'isolated-original'
    r=repo.create_revision(document_id,key,original_sha256=content_hash(raw),object_key='m1-test/'+key)
    attempt=repo.claim_attempt(r.revision_id,expected_attempt=0)
    chunk=Chunk(chunk_uid=str(uuid4()),document_id=document_id,revision_id=r.revision_id,section_id='s',ordinal=0,text='设备通过网络连接控制器',
                source_refs=(SourceRef(document_id=document_id,revision_id=r.revision_id,kind='pdf',page=1),))
    index.write_revision(repo,r.revision_id,[chunk],attempt=attempt,embedder=embedder)
    return r,attempt,chunk


def test_publish_failure_reconcile_concurrency_and_rollback(v2_setup,real_embedder):
    from app.knowledge.publishing import RevisionPublisher
    from app.knowledge.repository import ConflictError
    repo,index=v2_setup;d=repo.register_document('doc',name='发布隔离测试')
    publisher=RevisionPublisher(repo,index,read_original=lambda r:b'isolated-original')
    r1,a1,c1=make_revision(repo,index,d.document_id,'old',real_embedder)
    with pytest.raises(ConflictError):publisher.publish(r1.revision_id,expected_active=None)
    publisher.validate(r1.revision_id,attempt=a1)
    publisher.publish(r1.revision_id,expected_active=None)
    assert repo.get_active_revisions()==[{'document_id':d.document_id,'active_revision_id':r1.revision_id}]
    r2,a2,c2=make_revision(repo,index,d.document_id,'new',real_embedder)
    bad=RevisionPublisher(repo,index,read_original=lambda r:b'corrupted')
    with pytest.raises(ValueError):bad.validate(r2.revision_id,attempt=a2)
    assert repo.get_document(d.document_id)['active_revision_id']==r1.revision_id
    publisher.validate(r2.revision_id,attempt=a2)
    def crash():raise RuntimeError('合成指针后故障')
    with pytest.raises(RuntimeError):publisher.publish(r2.revision_id,expected_active=r1.revision_id,after_pointer=crash)
    assert repo.get_document(d.document_id)['active_revision_id']==r2.revision_id
    assert repo.get_revision(r2.revision_id)['status']=='validated'
    publisher.reconcile(d.document_id)
    assert repo.get_revision(r2.revision_id)['status']=='published'
    publisher.publish(r1.revision_id,expected_active=r2.revision_id)
    assert repo.get_document(d.document_id)['active_revision_id']==r1.revision_id
    r3,a3,_=make_revision(repo,index,d.document_id,'third',real_embedder)
    publisher.validate(r3.revision_id,attempt=a3)
    def publish(rid):
        try:publisher.publish(rid,expected_active=r1.revision_id);return True
        except ConflictError:return False
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(publish,[r2.revision_id,r3.revision_id]))
    assert sum(results)==1
    # 老来源/新版来源都仍可精确按修订读取，不重解析。
    assert index.revision_rows(repo,r1.revision_id)[0]['chunk_uid']==c1.chunk_uid
    assert index.revision_rows(repo,r2.revision_id)[0]['chunk_uid']==c2.chunk_uid


def test_validator_rejects_index_tamper_and_stale_attempt(v2_setup,real_embedder):
    from app.knowledge.publishing import RevisionPublisher
    from app.knowledge.repository import ConflictError
    repo,index=v2_setup;d=repo.register_document('doc',name='验证边界')
    r,a,c=make_revision(repo,index,d.document_id,'r',real_embedder)
    publisher=RevisionPublisher(repo,index,read_original=lambda r:b'isolated-original')
    with pytest.raises(ConflictError):publisher.validate(r.revision_id,attempt=a-1)
    rows=index.revision_rows(repo,r.revision_id,vectors=True)
    rows[0]['metadata']['source_refs'][0]['page']=7
    index.client.upsert(collection_name=index.collection,data=rows);index.client.flush(index.collection)
    with pytest.raises(ValueError):publisher.validate(r.revision_id,attempt=a)
    assert repo.get_document(d.document_id)['active_revision_id'] is None


def test_interrupted_index_cannot_change_reserved_payload(v2_setup):
    from app.knowledge.models import Chunk
    from app.knowledge.repository import ConflictError
    repo,index=v2_setup;d=repo.register_document('reserved',name='中断恢复')
    r=repo.create_revision(d.document_id,'r',original_sha256='a'*64,object_key='m1-test/reserved')
    attempt=repo.claim_attempt(r.revision_id,expected_attempt=0)
    c=Chunk(chunk_uid=str(uuid4()),document_id=d.document_id,revision_id=r.revision_id,section_id='s',ordinal=0,text='原始切片')
    def interrupted(*a):raise RuntimeError('合成编码中断')
    with pytest.raises(RuntimeError):index.write_revision(repo,r.revision_id,[c],attempt=attempt,embedder=interrupted)
    with pytest.raises(ConflictError):
        index.write_revision(repo,r.revision_id,[c.model_copy(update={'text':'改变载荷'})],attempt=attempt,embedder=interrupted)
