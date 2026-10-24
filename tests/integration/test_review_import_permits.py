"""独立目标验证过期许可接管；保留现场，不清许可制造通过。"""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4
import pytest
from app.ingestion.runner import (ImportRunner, FencedDocuments, claim_import_permit,
    renew_import_permit, release_import_permit)
from app.api.errors import APIError
from app.knowledge.repository import ConflictError
from app.runs.events import utcnow, aware

pytestmark = pytest.mark.integration


@pytest.fixture
def permit_context(mongo_db, tmp_path):
    from minio import Minio
    from pymilvus import MilvusClient
    from app.identity.models import Principal
    from app.knowledge.gateway import KnowledgeGateway
    from app.knowledge.originals import OriginalStore
    from app.knowledge.upload import UploadService
    from app.knowledge.index import V2Index
    from app.ingestion.parsers.markdown import MarkdownParser
    from app.ingestion.parsers.router import ParserRouter
    storage = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'],
        secret_key=os.environ['MINIO_SECRET_KEY'], secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
    milvus = MilvusClient(uri=os.environ['MILVUS_URL'])
    index = V2Index(milvus, 'm1_test_' + uuid4().hex + '_v2', dense_dim=2)
    originals = OriginalStore(storage, bucket=os.environ['MINIO_BUCKET_NAME'], prefix='m2-test/' + mongo_db.name + '/' + uuid4().hex + '/')
    g = KnowledgeGateway(mongo_db, originals, owner_id=uuid4().hex, index_factory=lambda: index)
    user = Principal(user_id=uuid4().hex, username='permit-test', role='maintainer', kb_ids=('k',))
    def upload(key, did=None):
        return UploadService(g).upload(user, kb_id='k', client_request_id=key, document_id=did, name='manual.md',
            media_type='text/markdown', data=('# 手册\n\n设备参数 ' + key).encode(), product_ids=[])
    runner = ImportRunner(g.jobs, g, router=ParserRouter({'md': MarkdownParser()}),
        embedder=lambda texts: {'dense': [[1., 0.] for _ in texts], 'sparse': [{1: 1.} for _ in texts]},
        summary=SimpleNamespace(), model='no-images', prompt_version='1', work_dir=tmp_path)
    yield g, runner, upload
    milvus.close()


def permit(row):
    return {'job_id': row['job_id'], 'attempt': row['attempt'], 'token': row['lease_token']}


def test_completed_old_job_expired_permit_allows_new_revision_once(permit_context):
    g, runner, upload = permit_context
    first = upload('old')
    old = g.jobs.claim(first['job_id'], lease_seconds=15)
    runner.execute(old)
    g.jobs.save(old['job_id'], old['attempt'], old['lease_token'], {'state': 'completed'})
    repo = g.repo('k')
    assert repo.get_document(first['document_id'])['import_permit'] == permit(old)
    second = upload('new', first['document_id'])
    # 正常完成后未执行finally，等待真实许可自然过期，不清字段。
    time.sleep(max(0, (aware(old['lease_until']) - utcnow()).total_seconds()) + .05)
    new = g.jobs.claim(second['job_id'])
    assert runner.execute(new)['revision_id'] == second['revision_id']
    g.jobs.save(new['job_id'], new['attempt'], new['lease_token'], {'state': 'completed'})
    assert g.jobs.claim(new['job_id']) is None
    document = repo.get_document(first['document_id'])
    assert document['active_revision_id'] == second['revision_id'] and document['active_generation'] == 2
    assert document['import_permit'] == permit(new)
    assert renew_import_permit(g.db, old, utcnow() + timedelta(seconds=600)).matched_count == 0
    assert release_import_permit(g.db, old).matched_count == 0
    assert repo.get_document(first['document_id'])['import_permit'] == permit(new)
    late = FencedDocuments(repo.documents, permit(old))
    assert late.update_one(repo.scope | {'document_id': first['document_id'], 'active_revision_id': second['revision_id']},
        {'$set': {'active_revision_id': first['revision_id']}}).matched_count == 0


@pytest.mark.parametrize('case', ['valid_other', 'higher_same_attempt', 'expired_competition'])
def test_permit_claim_is_atomic_and_protects_newer_attempt(permit_context, case):
    g, runner, upload = permit_context
    first = upload('first')
    old = g.jobs.claim(first['job_id'], lease_seconds=60 if case == 'valid_other' else 1)
    repo = g.repo('k')
    # 在已领取许可后的首个外部阶段暂停，使用现有execute入口。
    class Paused(Exception):
        pass
    def pause():
        raise Paused()
    g.index_factory = lambda: SimpleNamespace(ensure_collection=pause)
    with pytest.raises(Paused):
        runner.execute(old)
    if case == 'higher_same_attempt':
        time.sleep(1.05)
        newer = g.jobs.claim(first['job_id'])
        with pytest.raises(Paused):
            runner.execute(newer)
        with pytest.raises(APIError) as lost:
            runner.execute(old)
        assert lost.value.code == 'job_lease_lost'
        with pytest.raises(ConflictError):
            claim_import_permit(repo, old)
        assert renew_import_permit(g.db, old, utcnow() + timedelta(seconds=600)).matched_count == 0
        assert release_import_permit(g.db, old).matched_count == 0
        assert repo.get_document(first['document_id'])['import_permit'] == permit(newer)
        return
    rows = [g.jobs.claim(upload(str(i), first['document_id'])['job_id']) for i in range(4)]
    if case == 'valid_other':
        with pytest.raises(ConflictError):
            runner.execute(rows[0])
        assert repo.get_document(first['document_id'])['import_permit'] == permit(old)
        return
    time.sleep(1.05)
    def compete(row):
        try:
            runner.execute(row)
        except Paused:
            return row
        except ConflictError:
            return None
    with ThreadPoolExecutor(max_workers=4) as pool:
        winners = [r for r in pool.map(compete, rows) if r]
    assert len(winners) == 1
    assert repo.get_document(first['document_id'])['import_permit'] == permit(winners[0])

