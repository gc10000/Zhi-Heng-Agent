"""阶段检查点恢复验证：失败后不会重新请求已完成图片。"""
import pytest
from app.api.errors import APIError
from uuid import uuid4
from app.ingestion.stages.images import process_images
from app.ingestion.models import ParsedDocument, ParsedImage
from app.knowledge.models import SourceRef, content_hash

pytestmark = pytest.mark.integration


def test_retryable_image_error_is_not_collapsed_to_generic_quality_flag(tmp_path):
    from PIL import Image
    from types import SimpleNamespace
    from app.ingestion.stages.images import ImageSummaryService
    path = tmp_path / 'diagram.png'
    Image.new('RGB', (4, 4), 'red').save(path)
    ref = SourceRef(document_id='d', revision_id='r', kind='markdown', line_start=1)
    parsed = ParsedDocument(document_id='d', revision_id='r', original_sha256='a'*64, parser='test', parser_version='1',
        images=(ParsedImage(image_id='i', local_path=str(path), source_refs=(ref,)),))
    class RateLimited(Exception):
        status_code = 429
    def describe(*args):
        raise RateLimited('synthetic-private-provider-error')
    cache = SimpleNamespace(get=lambda key: None, claim=lambda *a: True, fail=lambda *a: None)
    summary = ImageSummaryService(cache, SimpleNamespace(acquire=lambda: None), describe)
    store = SimpleNamespace(put_image=lambda *a, **k: SimpleNamespace(asset_id='i'))
    # 持久任务要求错误向外层传播；默认M1宽松模式仍保留兼容。
    summary.strict_errors = True
    with pytest.raises(RateLimited):
        process_images(parsed, store, summary, model='fake', prompt_version='1')


def test_error_classification_preserves_http_status_and_timeout():
    from app.ingestion.runner import classify_error
    from app.ingestion.parsers.mineru import ProviderError, ProviderTimeout
    assert classify_error(ProviderError('redacted', status_code=429)) == ('provider_rate_limited', True)
    assert classify_error(ProviderError('redacted', status_code=401)) == ('provider_authentication_failed', False)
    assert classify_error(ProviderTimeout('redacted')) == ('upstream_timeout', True)
    assert classify_error(ValueError('redacted')) == ('invalid_document_or_configuration', False)


def test_expired_job_permit_cannot_change_active_pointer(mongo_db):
    from app.ingestion.runner import FencedDocuments
    from app.runs.events import utcnow
    from datetime import timedelta
    permit = {'job_id': uuid4().hex, 'attempt': 1, 'token': uuid4().hex}
    did = uuid4().hex
    mongo_db.knowledge_documents.insert_one({'document_id': did, 'active_revision_id': None,
        'import_permit': permit, 'import_lease_until': utcnow() - timedelta(seconds=1)})
    fenced = FencedDocuments(mongo_db.knowledge_documents, permit)
    result = fenced.update_one({'document_id': did, 'active_revision_id': None}, {'$set': {'active_revision_id': 'late'}})
    assert result.matched_count == 0
    assert mongo_db.knowledge_documents.find_one({'document_id': did})['active_revision_id'] is None


def test_embedding_batches_reuse_success_after_second_batch_failure(mongo_db):
    import os
    from types import SimpleNamespace
    from minio import Minio
    from app.ingestion.jobs import JobRepository
    from app.ingestion.checkpoints import Checkpoints, CheckpointEmbedder
    from app.knowledge.originals import OriginalStore
    from tests.integration.test_job_leases import seed
    jobs, jid = seed(mongo_db)
    row = jobs.claim(jid)
    client = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'], secret_key=os.environ['MINIO_SECRET_KEY'],
                   secure=os.getenv('MINIO_SECURE','').lower() == 'true')
    originals = OriginalStore(client, bucket=os.environ['MINIO_BUCKET_NAME'], prefix='m2-test/' + mongo_db.name + '/' + uuid4().hex + '/')
    calls = []
    def encode(texts):
        calls.append(list(texts))
        if texts == ['third'] and calls.count(['third']) == 1:
            raise TimeoutError('synthetic embedding timeout')
        return {'dense': [[1., 0.] for _ in texts], 'sparse': [{1: 1.} for _ in texts]}
    encoder = CheckpointEmbedder(Checkpoints(jobs, row, originals), encode, identity='test-vectors', batch_size=2)
    with pytest.raises(TimeoutError):
        encoder(['first', 'second', 'third'])
    result = encoder(['first', 'second', 'third'])
    assert len(result['dense']) == 3
    assert calls == [['first', 'second'], ['third'], ['third']]


def test_persisted_parse_and_image_cache_survive_later_embedding_failure(mongo_db, tmp_path):
    import os
    from types import SimpleNamespace
    from datetime import timedelta
    from minio import Minio
    from pymilvus import MilvusClient
    from PIL import Image
    from app.identity.models import Principal
    from app.knowledge.gateway import KnowledgeGateway
    from app.knowledge.originals import OriginalStore
    from app.knowledge.upload import UploadService
    from app.knowledge.index import V2Index
    from app.knowledge.assets import MongoSummaryCache
    from app.ingestion.models import Block
    from app.ingestion.runner import ImportRunner
    from app.ingestion.stages.images import ImageSummaryService
    from app.runs.events import utcnow
    storage = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'], secret_key=os.environ['MINIO_SECRET_KEY'],
                    secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
    index_client = MilvusClient(uri=os.environ['MILVUS_URL'])
    index = V2Index(index_client, 'm1_test_' + uuid4().hex + '_v2', dense_dim=2)
    originals = OriginalStore(storage, bucket=os.environ['MINIO_BUCKET_NAME'], prefix='m2-test/' + mongo_db.name + '/' + uuid4().hex + '/')
    g = KnowledgeGateway(mongo_db, originals, owner_id=uuid4().hex, index_factory=lambda: index)
    user = Principal(user_id=uuid4().hex, username='import-test', role='maintainer', kb_ids=('k',))
    raw = b'# text manual'
    result = UploadService(g).upload(user, kb_id='k', client_request_id='one', name='manual.md', media_type='text/markdown', data=raw, product_ids=[])
    did, rid = result['document_id'], result['revision_id']
    image = tmp_path / 'diagram.png'
    Image.new('RGB', (8, 6), 'green').save(image)
    ref = SourceRef(document_id=did, revision_id=rid, kind='markdown', line_start=1)
    parse_calls, summary_calls, encode_calls = [], [], []
    class Parser:
        version = 'explicit-fake-1'
        def parse(self, *args, **kwargs):
            parse_calls.append(1)
            return ParsedDocument(document_id=did, revision_id=rid, original_sha256=content_hash(raw), parser='fake-port', parser_version='1',
                blocks=(Block(block_id='text', kind='text', text='设备连接控制器。', source_refs=(ref,)),),
                images=(ParsedImage(image_id='image-' + rid, local_path=str(image), source_refs=(ref,)),))
    def describe(*args):
        summary_calls.append(1)
        return '设备通过网络连接控制器。'
    def encode(texts):
        encode_calls.append(1)
        if len(encode_calls) == 1:
            raise TimeoutError('synthetic later embedding interruption')
        return {'dense': [[1., 0.] for _ in texts], 'sparse': [{1: 1.} for _ in texts]}
    summary = ImageSummaryService(MongoSummaryCache(mongo_db), SimpleNamespace(acquire=lambda: None), describe)
    runner = ImportRunner(g.jobs, g, router=SimpleNamespace(parsers={'md': Parser()}, parse=Parser().parse), embedder=encode,
                          summary=summary, model='explicit-fake-vision', prompt_version='1', work_dir=tmp_path)
    try:
        old = g.jobs.claim(result['job_id'])
        with pytest.raises(TimeoutError):
            runner.execute(old)
        saved = g.jobs.jobs.find_one({'job_id': result['job_id']})
        assert 'parsed' in saved['checkpoints'] and 'images_completed' in saved['checkpoints']
        assert len(summary_calls) == 1
        # 仅过期独立测试任务；已存解析/原图快照和摘要缓存必须复用。
        g.jobs.jobs.update_one({'job_id': result['job_id']}, {'$set': {'lease_until': utcnow() - timedelta(seconds=1)}})
        new = g.jobs.claim(result['job_id'])
        assert runner.execute(new)['revision_id'] == rid
        assert len(parse_calls) == len(summary_calls) == 1 and len(encode_calls) == 2
        assert g.repo('k').get_document(did)['active_revision_id'] == rid
        with pytest.raises(APIError):
            runner.execute(old)
    finally:
        index_client.close()


def test_real_linux_worker_interrupt_resume_and_duplicate_publish(mongo_db, monkeypatch):
    import os
    import time
    import subprocess
    from minio import Minio
    from pymilvus import MilvusClient
    from app.identity.models import Principal
    from app.knowledge.gateway import KnowledgeGateway
    from app.knowledge.originals import OriginalStore
    from app.knowledge.upload import UploadService
    from app.knowledge.index import V2Index
    from app.ingestion.dispatcher import Dispatcher
    from scripts.verification.worker_environment import worker_environment
    monkeypatch.setenv('JOB_LEASE_SECONDS', '12')
    monkeypatch.setenv('JOB_HEARTBEAT_SECONDS', '2')
    with worker_environment(mongo_db.name) as env:
        values = env['container_env']
        storage = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'], secret_key=os.environ['MINIO_SECRET_KEY'],
                        secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
        milvus = MilvusClient(uri=os.environ['MILVUS_URL'])
        index = V2Index(milvus, values['M2_MILVUS_COLLECTION'])
        originals = OriginalStore(storage, bucket=values['M2_OBJECT_BUCKET'], prefix=values['M2_OBJECT_PREFIX'])
        g = KnowledgeGateway(mongo_db, originals, owner_id=values['M2_KNOWLEDGE_OWNER_ID'], index_factory=lambda: index)
        user = Principal(user_id=uuid4().hex, username='linux-import', role='maintainer', kb_ids=('k',))
        raw = '# 隔离设备手册\n\nLA2608使用display wlan ap检查设备连接状态。\n\n管理地址为192.0.2.20。'.encode()
        result = UploadService(g).upload(user, kb_id='k', client_request_id='linux-one', name='manual.md',
            media_type='text/markdown', data=raw, product_ids=[])
        jid = result['job_id']
        dispatcher = Dispatcher(g.jobs, env['send'])
        dispatcher.dispatch()
        for _ in range(120):
            saved = g.jobs.jobs.find_one({'job_id': jid})
            if saved.get('stage') == 'embedding_pending' or saved['state'] in {'failed', 'completed'}:
                break
            time.sleep(.2)
        assert saved['stage'] == 'embedding_pending', saved.get('error')
        parsed = saved['checkpoints']['parsed']
        # 仅强制停止本用例创建的隔离worker，不碰现有业务容器。
        assert subprocess.run(['docker', 'stop', '--time', '0', env['name']], capture_output=True).returncode == 0
        time.sleep(13)
        dispatcher.dispatch()
        assert subprocess.run(['docker', 'start', env['name']], capture_output=True).returncode == 0
        for _ in range(240):
            saved = g.jobs.jobs.find_one({'job_id': jid})
            if saved['state'] in {'failed', 'completed'}:
                break
            time.sleep(1)
        assert saved['state'] == 'completed', saved.get('error')
        assert saved['attempt'] >= 2 and saved['checkpoints']['parsed'] == parsed
        document = g.repo('k').get_document(result['document_id'])
        assert document['active_revision_id'] == result['revision_id'] and document['active_generation'] == 1
        attempt = saved['attempt']
        env['send'](jid)
        env['send'](jid)
        time.sleep(2)
        assert g.jobs.jobs.find_one({'job_id': jid})['attempt'] == attempt
        assert g.repo('k').get_document(result['document_id'])['active_generation'] == 1
        rows = index.revision_rows(g.repo('k'), result['revision_id'], vectors=True)
        assert rows and all(len(row['dense_vector']) == 1024 and row['sparse_vector'] for row in rows)
        milvus.close()
