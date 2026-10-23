"""standalone Mongo的真实并发幂等/CAS及隔离测试。"""
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4
import pytest

pytestmark = pytest.mark.integration


@pytest.fixture
def repo(mongo_db):
    from app.knowledge.repository import KnowledgeRepository
    return KnowledgeRepository(mongo_db, kb_id=str(uuid4()), owner_id='test-owner')


def test_registration_and_revision_are_idempotent_under_concurrency(repo):
    with ThreadPoolExecutor(max_workers=4) as pool:
        docs=list(pool.map(lambda _: repo.register_document('req', name='相同手册'), range(8)))
    assert len({d.document_id for d in docs}) == 1
    d=docs[0]
    with ThreadPoolExecutor(max_workers=4) as pool:
        revisions=list(pool.map(lambda _: repo.create_revision(d.document_id,'rev',original_sha256='a'*64,object_key='test/source'),range(8)))
    assert len({r.revision_id for r in revisions}) == 1
    assert repo.revisions.count_documents({'document_id':d.document_id}) == 1


def test_same_filename_different_requests_and_ownership_do_not_collide(repo):
    from app.knowledge.repository import KnowledgeRepository, ScopeError
    a=repo.register_document('a',name='同名')
    b=repo.register_document('b',name='同名')
    assert a.document_id != b.document_id
    other=KnowledgeRepository(repo.db,kb_id=repo.kb_id,owner_id='other')
    with pytest.raises(ScopeError):
        other.create_revision(a.document_id,'x',original_sha256='b'*64,object_key='o')
    assert other.get_active_revisions() == []


def test_reusing_key_with_different_payload_is_conflict(repo):
    from app.knowledge.repository import ConflictError
    d=repo.register_document('r',name='原名')
    with pytest.raises(ConflictError):
        repo.register_document('r',name='不同')
    repo.create_revision(d.document_id,'x',original_sha256='a'*64,object_key='o')
    with pytest.raises(ConflictError):
        repo.create_revision(d.document_id,'x',original_sha256='b'*64,object_key='o')


def test_stale_attempt_cannot_write_stage(repo):
    from app.knowledge.repository import ConflictError
    d=repo.register_document('r',name='n')
    r=repo.create_revision(d.document_id,'rev',original_sha256='a'*64,object_key='o')
    assert repo.claim_attempt(r.revision_id,expected_attempt=0)==1
    assert repo.claim_attempt(r.revision_id,expected_attempt=1)==2
    with pytest.raises(ConflictError):
        repo.save_stage(r.revision_id,attempt=1,stage='parsed',manifest={'hash':'x'})
    repo.save_stage(r.revision_id,attempt=2,stage='parsed',manifest={'hash':'ok'})
    assert repo.get_revision(r.revision_id)['stages']['parsed']['hash']=='ok'


def test_missing_parent_creates_no_orphan_and_reconcile_reports_bad_pointer(repo):
    from app.knowledge.repository import ScopeError
    before=repo.revisions.count_documents({})
    with pytest.raises(ScopeError):
        repo.create_revision('missing','r',original_sha256='c'*64,object_key='o')
    assert repo.revisions.count_documents({})==before
    d=repo.register_document('r',name='n')
    repo.documents.update_one({'document_id':d.document_id},{'$set':{'active_revision_id':'missing'}})
    assert repo.reconcile()[0]['code']=='missing_active_revision'
