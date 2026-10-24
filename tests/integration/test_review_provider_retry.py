"""真实导入入口与存储，SDK异常注入，不请求供应商。"""
import os
from types import SimpleNamespace
from uuid import uuid4
import pytest
from tests.contract.test_provider_errors import sdk_error

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('kind,code', [('timeout', 'upstream_timeout'), ('connection', 'upstream_connection_failed')])
def test_sdk_image_failure_persisted_then_writer_retry_reuses_parse(m2_client, monkeypatch, tmp_path, kind, code):
    from minio import Minio
    from pymilvus import MilvusClient
    from PIL import Image
    from app.identity.models import Principal
    from app.knowledge.gateway import KnowledgeGateway
    from app.knowledge.originals import OriginalStore
    from app.knowledge.upload import UploadService
    from app.knowledge.index import V2Index
    from app.knowledge.assets import MongoSummaryCache
    from app.knowledge.resources import KnowledgeResources
    from app.knowledge.models import SourceRef, content_hash
    from app.ingestion.models import ParsedDocument, ParsedImage, Block
    from app.ingestion.stages.images import ImageSummaryService
    from app.ingestion import runner as module
    from app.settings import Settings
    client, headers, resources = m2_client
    db = resources['db']
    identity = resources['identity']
    account = identity.store.users.find_one({})
    user = Principal(**{k: account[k] for k in Principal.model_fields}).model_copy(update={'role': 'maintainer'})
    storage = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'],
                    secret_key=os.environ['MINIO_SECRET_KEY'], secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
    milvus = MilvusClient(uri=os.environ['MILVUS_URL'])
    index = V2Index(milvus, 'm1_test_' + uuid4().hex + '_v2', dense_dim=2)
    originals = OriginalStore(storage, bucket=os.environ['MINIO_BUCKET_NAME'], prefix='m2-test/' + db.name + '/' + uuid4().hex + '/')
    g = KnowledgeGateway(db, originals, owner_id=uuid4().hex, index_factory=lambda: index)
    resources['knowledge'] = lambda: g
    raw = b'# isolated SDK retry manual'
    uploaded = UploadService(g).upload(user, kb_id='k', client_request_id='sdk-retry', name='manual.md',
        media_type='text/markdown', data=raw, product_ids=[])
    did, rid, jid = (uploaded[k] for k in ('document_id', 'revision_id', 'job_id'))
    image = tmp_path / 'diagram.png'
    Image.new('RGB', (5, 5), 'green').save(image)
    ref = SourceRef(document_id=did, revision_id=rid, kind='markdown', line_start=1)
    calls = {'parse': 0, 'summary': 0}
    class Parser:
        version = 'review-sdk-1'
        def parse(self, *a, **kw):
            calls['parse'] += 1
            return ParsedDocument(document_id=did, revision_id=rid, original_sha256=content_hash(raw), parser='injected', parser_version='1',
                blocks=(Block(block_id='text', kind='text', text='控制器连接设备。', source_refs=(ref,)),),
                images=(ParsedImage(image_id='diagram', local_path=str(image), source_refs=(ref,)),))
    def describe(*a):
        calls['summary'] += 1
        if calls['summary'] == 1:
            raise sdk_error(kind)
        return '控制器连接设备。'
    summary = ImageSummaryService(MongoSummaryCache(db), SimpleNamespace(acquire=lambda: None), describe)
    def configured(jobs, gateway):
        return module.ImportRunner(jobs, gateway, router=SimpleNamespace(parsers={'md': Parser()}, parse=Parser().parse),
            embedder=lambda texts: {'dense': [[1., 0.] for _ in texts], 'sparse': [{1: 1.} for _ in texts]},
            summary=summary, model='injected-review', prompt_version='1', work_dir=tmp_path)
    monkeypatch.setattr(module, 'configured_runner', configured)
    monkeypatch.setattr(Settings, 'load', classmethod(lambda cls: Settings(os.environ['MONGO_URL'], db.name)))
    monkeypatch.setattr(KnowledgeResources, 'get', lambda self: g)
    try:
        module.run_import(jid)
        failed = g.jobs.get(user, jid)
        assert failed['state'] == 'failed' and failed['retryable'] is True
        assert failed['error'] == {'code': code, 'stage': 'images'}
        parsed = failed['checkpoints']['parsed']
        url = '/api/v1/import-jobs/' + jid + '/retry'
        assert client.post(url, headers=headers, json={'expected_version': failed['version']}).status_code == 403
        identity.store.users.update_one({'user_id': user.user_id}, {'$set': {'role': 'maintainer'}})
        assert client.post(url, headers=headers, json={'expected_version': failed['version'] - 1}).status_code == 409
        assert client.post(url, headers=headers, json={'expected_version': failed['version']}).status_code == 200
        assert client.post(url, headers=headers, json={'expected_version': failed['version']}).status_code == 409
        module.run_import(jid)
        completed = g.jobs.get(user, jid)
        assert completed['state'] == 'completed' and completed['attempt'] == 2
        assert completed['checkpoints']['parsed'] == parsed
        assert calls == {'parse': 1, 'summary': 2}
        assert g.repo('k').get_document(did)['active_revision_id'] == rid
        module.run_import(jid)
        assert calls == {'parse': 1, 'summary': 2}
    finally:
        milvus.close()
