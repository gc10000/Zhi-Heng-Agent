"""真实Mongo/MinIO的新上传链路；原课程对象仅共享客户端、不写原前缀。"""
import os
from uuid import uuid4
import pytest
from app.knowledge.gateway import KnowledgeGateway
from app.knowledge.originals import OriginalStore

pytestmark = pytest.mark.integration


@pytest.fixture
def knowledge_client(m2_client):
    from minio import Minio
    client, headers, resources = m2_client
    db = resources['db']
    minio = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'], secret_key=os.environ['MINIO_SECRET_KEY'],
                  secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
    originals = OriginalStore(minio, bucket=os.environ['MINIO_BUCKET_NAME'], prefix='m2-test/' + db.name + '/' + uuid4().hex + '/')
    g = KnowledgeGateway(db, originals, owner_id='org-' + uuid4().hex, max_upload_bytes=1024)
    resources['knowledge'] = lambda: g
    user = resources['identity'].authenticate(client.cookies.get('support_session'))
    resources['identity'].store.users.update_one({'user_id': user.user_id}, {'$set': {'role': 'maintainer'}})
    yield client, headers, resources, g


def upload(client, headers, *, key='one', name='manual.md', data=b'# manual\n\nvalue 5', **fields):
    return client.post('/api/v1/documents', headers=headers,
        data={'kb_id': 'k', 'client_request_id': key, **fields}, files={'file': (name, data, 'text/markdown')})


def test_upload_idempotence_same_name_no_overwrite_and_job_ledger(knowledge_client):
    client, headers, resources, g = knowledge_client
    a = upload(client, headers)
    assert a.status_code == 202
    b = upload(client, headers)
    assert b.status_code == 202 and b.json() == a.json()
    c = upload(client, headers, key='second', data=b'# manual\n\nvalue 9')
    assert c.status_code == 202 and c.json()['document_id'] != a.json()['document_id']
    first = g.repo('k').get_revision(a.json()['revision_id'])
    second = g.repo('k').get_revision(c.json()['revision_id'])
    assert first['object_key'] != second['object_key']
    assert g.originals.read(first) == b'# manual\n\nvalue 5'
    assert g.originals.read(second) == b'# manual\n\nvalue 9'
    assert upload(client, headers, data=b'# different').status_code == 409
    job = client.get('/api/v1/import-jobs/' + a.json()['job_id'])
    assert job.status_code == 200 and job.json()['state'] == 'pending' and job.json()['stage'] == 'uploaded'
    assert 'object_key' not in job.text
    assert g.repo('k').get_document(a.json()['document_id'])['active_revision_id'] is None


def test_directory_product_scopes_pagination_and_viewer_permissions(knowledge_client):
    client, headers, resources, g = knowledge_client
    ids = []
    for i in range(3):
        response = client.post('/api/v1/products', headers=headers, json={'kb_id': 'k', 'model': '模型' + str(i)})
        assert response.status_code == 201
        ids.append(response.json()['product_id'])
    import json
    item = upload(client, headers, product_ids=json.dumps([ids[0]]))
    assert item.status_code == 202
    page = client.get('/api/v1/products?kb_id=k&limit=2').json()
    rest = client.get('/api/v1/products', params={'kb_id': 'k', 'limit': 2, 'cursor': page['next_cursor']}).json()
    assert {p['product_id'] for p in page['items'] + rest['items']} == set(ids)
    assert client.get('/api/v1/products/' + ids[0] + '/documents?kb_id=k').json()['items'][0]['document_id'] == item.json()['document_id']
    assert client.get('/api/v1/products/' + ids[0] + '/documents?kb_id=other').status_code == 404
    assert upload(client, headers, key='forged', product_ids='["missing"]').status_code == 404
    did, rid = item.json()['document_id'], item.json()['revision_id']
    assert client.get('/api/v1/documents/' + did + '/revisions').json()['items'][0]['revision_id'] == rid
    user = resources['identity'].authenticate(client.cookies.get('support_session'))
    resources['identity'].store.users.update_one({'user_id': user.user_id}, {'$set': {'role': 'viewer'}})
    assert client.get('/api/v1/documents?kb_id=k').json()['items'][0]['document_id'] == did
    assert upload(client, headers, key='forbidden').status_code == 403
    assert client.get(f'/api/v1/documents/{did}/revisions/{rid}/chunks').status_code == 403
    assert client.post(f'/api/v1/documents/{did}/revisions/{rid}/publish', headers=headers, json={'expected_active_revision_id': None}).status_code == 403
    assert client.post('/api/v1/documents/' + did + '/withdraw', headers=headers, json={'expected_active_revision_id': None}).status_code == 403
    resources['identity'].store.users.update_one({'user_id': user.user_id}, {'$set': {'kb_ids': []}})
    assert client.get('/api/v1/documents/' + did + '/revisions').status_code == 404


def test_upload_persistence_failure_retries_reserved_object_and_rejects_bad_inputs(knowledge_client, monkeypatch):
    client, headers, resources, g = knowledge_client
    with monkeypatch.context() as patch:
        def fail(*args, **kwargs):
            raise OSError('synthetic-private-key')
        patch.setattr(g.originals, 'put', fail)
        failed = upload(client, headers)
        assert failed.status_code == 500 and 'synthetic-private-key' not in failed.text
    reserved = g.db.document_uploads.find_one({'owner_id': resources['identity'].authenticate(client.cookies.get('support_session')).user_id})
    retried = upload(client, headers)
    assert retried.status_code == 202
    assert g.repo('k').get_revision(retried.json()['revision_id'])['object_key'] == reserved['object_key']
    assert upload(client, headers, key='big', data=b'x' * 1025).status_code == 413
    assert upload(client, headers, key='path', name='../manual.md').status_code == 422
    assert upload(client, headers, key='pid', product_ids='{}').status_code == 422
    assert client.post('/api/v1/documents', content=b'x' * (1024 + 65537),
                       headers=headers | {'Content-Type': 'multipart/form-data; boundary=x'}).status_code == 413


def test_revision_publish_rollback_withdraw_and_chunk_api_use_real_validation(knowledge_client):
    from pymilvus import MilvusClient
    from app.knowledge.index import V2Index
    from app.knowledge.models import Chunk, SourceRef
    client, headers, resources, g = knowledge_client
    milvus = MilvusClient(uri=os.environ['MILVUS_URL'])
    index = V2Index(milvus, 'm1_test_' + uuid4().hex + '_v2', dense_dim=2)
    index.ensure_collection()
    g.index_factory = lambda: index
    try:
        first = upload(client, headers).json()
        did, rid = first['document_id'], first['revision_id']
        path = f'/api/v1/documents/{did}/revisions/{rid}'
        assert client.post(path + '/publish', headers=headers, json={'expected_active_revision_id': None}).status_code == 409
        repo = g.repo('k')
        def validate(revision_id, text):
            attempt = repo.claim_attempt(revision_id, expected_attempt=0)
            chunk = Chunk(chunk_uid=uuid4().hex, document_id=did, revision_id=revision_id,
                section_id='s', ordinal=0, text=text,
                source_refs=(SourceRef(document_id=did, revision_id=revision_id, kind='markdown', line_start=1),))
            # 合成向量仅验证真实存储/发布控制流，不冒充本地BGE语义验收。
            index.write_revision(repo, revision_id, [chunk], attempt=attempt,
                embedder=lambda texts: {'dense': [[1., 0.] for _ in texts], 'sparse': [{1: 1.} for _ in texts]})
            g.publisher('k').validate(revision_id, attempt=attempt)
        validate(rid, '第一版')
        assert client.post(path + '/publish', headers=headers, json={'expected_active_revision_id': None}).status_code == 200
        second = upload(client, headers, key='new-revision', document_id=did, data=b'# new').json()['revision_id']
        validate(second, '第二版')
        assert client.post(f'/api/v1/documents/{did}/revisions/{second}/publish', headers=headers,
            json={'expected_active_revision_id': 'stale'}).status_code == 409
        assert client.post(f'/api/v1/documents/{did}/revisions/{second}/publish', headers=headers,
            json={'expected_active_revision_id': rid}).status_code == 200
        assert client.post(f'/api/v1/documents/{did}/rollback', headers=headers,
            json={'expected_active_revision_id': second, 'target_revision_id': rid}).status_code == 200
        chunks = client.get(path + '/chunks?limit=1')
        assert chunks.status_code == 200 and chunks.json()['items'][0]['text'] == '第一版'
        assert client.post(f'/api/v1/documents/{did}/withdraw', headers=headers,
            json={'expected_active_revision_id': second}).status_code == 409
        assert client.post(f'/api/v1/documents/{did}/withdraw', headers=headers,
            json={'expected_active_revision_id': rid}).status_code == 200
        assert repo.get_document(did)['active_revision_id'] is None
        assert len(index.revision_rows(repo, rid)) == len(index.revision_rows(repo, second)) == 1
    finally:
        milvus.close()


def test_job_retry_and_other_owner_hiding(knowledge_client):
    client, headers, resources, g = knowledge_client
    result = upload(client, headers).json()
    jid = result['job_id']
    route = '/api/v1/import-jobs/' + jid
    assert client.post(route + '/retry', headers=headers, json={'expected_version': 0}).status_code == 409
    g.jobs.jobs.update_one({'job_id': jid}, {'$set': {'state': 'failed', 'retryable': True}})
    retried = client.post(route + '/retry', headers=headers, json={'expected_version': 0})
    assert retried.status_code == 200 and retried.json()['state'] == 'pending'
    assert client.post(route + '/retry', headers=headers, json={'expected_version': 0}).status_code == 409
    user = resources['identity'].authenticate(client.cookies.get('support_session'))
    g.jobs.jobs.update_one({'job_id': jid}, {'$set': {'owner_id': 'different'}})
    assert client.get(route).status_code == 404
