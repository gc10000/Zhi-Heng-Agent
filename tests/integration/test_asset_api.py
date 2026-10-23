"""真实受控原件/旧图HTTP读取与独立测试桶策略；不更改旧桶策略。"""
from io import BytesIO
from uuid import uuid4
import json
import os
import pytest
import requests
from PIL import Image
from app.knowledge.asset_api import original_asset
from app.knowledge.models import content_hash
from app.knowledge.legacy_assets import map_legacy_image
from tests.integration.test_document_api import knowledge_client, upload
from tests.integration.test_run_claim import request

pytestmark = pytest.mark.integration


def test_pdf_range_and_authorization_and_revision_after_withdraw(knowledge_client):
    import fitz
    client, headers, resources, g = knowledge_client
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), 'isolated manual')
    data = doc.tobytes()
    doc.close()
    g.max_upload_bytes = len(data) + 100
    response = client.post('/api/v1/documents', headers=headers, data={'kb_id': 'k', 'client_request_id': 'pdf'},
                           files={'file': ('manual.pdf', data, 'application/pdf')})
    assert response.status_code == 202
    aid = response.json()['original_asset_id']
    path = '/api/v1/assets/' + aid
    complete = client.get(path)
    assert complete.status_code == 200 and complete.content == data
    assert complete.headers['accept-ranges'] == 'bytes'
    partial = client.get(path, headers={'Range': 'bytes=0-4'})
    assert partial.status_code == 206 and partial.content == b'%PDF-'
    assert partial.headers['content-range'] == f'bytes 0-4/{len(data)}'
    suffix = client.get(path, headers={'Range': 'bytes=-3'})
    assert suffix.status_code == 206 and suffix.content == data[-3:]
    invalid = client.get(path, headers={'Range': 'bytes=999999-'})
    assert invalid.status_code == 416 and invalid.headers['content-range'] == f'bytes */{len(data)}'
    assert client.post('/api/v1/documents/' + response.json()['document_id'] + '/withdraw', headers=headers,
                       json={'expected_active_revision_id': None}).status_code == 200
    assert client.get(path).status_code == 200
    assert client.get('/api/v1/assets/unknown').status_code == 404
    user = resources['identity'].authenticate(client.cookies.get('support_session'))
    resources['identity'].store.users.update_one({'user_id': user.user_id}, {'$set': {'kb_ids': []}})
    assert client.get(path).status_code == 404


def test_legacy_map_precise_hash_private_test_bucket_and_run_citation(knowledge_client):
    client, headers, resources, g = knowledge_client
    created = upload(client, headers).json()
    did, rid = created['document_id'], created['revision_id']
    user = resources['identity'].authenticate(client.cookies.get('support_session'))
    bucket = 'm2-test-' + uuid4().hex
    storage = g.originals.client
    storage.make_bucket(bucket)
    output = BytesIO()
    Image.new('RGB', (8, 6), 'blue').save(output, format='PNG')
    data, key = output.getvalue(), 'legacy/topology.png'
    storage.put_object(bucket, key, BytesIO(data), len(data), content_type='image/png')
    # 只对新建测试桶先验证公开，再移除测试策略，原桶完全不调用策略操作。
    policy = {'Version': '2012-10-17', 'Statement': [{'Effect': 'Allow', 'Principal': {'AWS': ['*']},
        'Action': ['s3:GetObject'], 'Resource': ['arn:aws:s3:::' + bucket + '/*']}]}
    storage.set_bucket_policy(bucket, json.dumps(policy))
    scheme = 'https' if os.getenv('MINIO_SECURE', '').lower() == 'true' else 'http'
    url = scheme + '://' + os.environ['MINIO_ENDPOINT'] + '/' + bucket + '/' + key
    with requests.Session() as session:
        session.trust_env = False
        assert session.get(url, timeout=10).status_code == 200
        storage.delete_bucket_policy(bucket)
        assert session.get(url, timeout=10).status_code in {401, 403}
    with pytest.raises(ValueError):
        map_legacy_image(g, user, document_id=did, revision_id=rid, bucket=bucket, object_key=key, expected_sha256='0'*64)
    aid = map_legacy_image(g, user, document_id=did, revision_id=rid, bucket=bucket, object_key=key, expected_sha256=content_hash(data))
    image = client.get('/api/v1/assets/' + aid)
    assert image.status_code == 200 and content_hash(image.content) == content_hash(data)
    with Image.open(BytesIO(image.content)) as decoded:
        decoded.load()
        assert decoded.size == (8, 6)
    cid = client.post('/api/v1/conversations', headers=headers, json={'kb_id': 'k'}).json()['conversation_id']
    run_id = client.post('/api/v1/conversations/' + cid + '/runs', headers=headers, json=request().model_dump()).json()['run_id']
    citation = {'citation_id': 'cite', 'document_id': did, 'revision_id': rid, 'asset_ids': [aid],
                'text': '![图](asset://' + aid + ')', 'source_refs': [{'kind': 'legacy', 'page': None}]}
    resources['runs'].runs.update_one({'run_id': run_id}, {'$set': {'citations': [citation]}})
    response = client.get('/api/v1/runs/' + run_id + '/citations/cite')
    assert response.status_code == 200 and '/api/v1/assets/' + aid in response.json()['display_text']
    assert client.get('/api/v1/runs/' + run_id + '/citations/missing').status_code == 404
    # 同kb另一用户也不能读取个人run的引用。
    second = resources['identity'].add_user(uuid4().hex, 'isolated-password', role='viewer', kb_ids=['k'])
    resources['runs'].runs.update_one({'run_id': run_id}, {'$set': {'owner_id': second.user_id}})
    assert client.get('/api/v1/runs/' + run_id + '/citations/cite').status_code == 404
