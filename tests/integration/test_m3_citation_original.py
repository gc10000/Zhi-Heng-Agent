"""前端PDF定位使用已授权修订的登记原件，不在浏览器推导业务ID。"""
import pytest
from tests.integration.test_document_api import knowledge_client
from tests.integration.test_run_claim import request

pytestmark = pytest.mark.integration


def test_citation_original_descriptor_and_authorization(knowledge_client):
    import fitz
    client, headers, resources, g = knowledge_client
    doc = fitz.open()
    doc.new_page().insert_text((50, 50), 'M3 isolated PDF')
    raw = doc.tobytes()
    doc.close()
    g.max_upload_bytes = len(raw) + 100
    created = client.post('/api/v1/documents', headers=headers, data={'kb_id': 'k', 'client_request_id': 'm3-pdf'},
        files={'file': ('manual.pdf', raw, 'application/pdf')}).json()
    cid = client.post('/api/v1/conversations', headers=headers, json={'kb_id': 'k'}).json()['conversation_id']
    rid = client.post('/api/v1/conversations/' + cid + '/runs', headers=headers, json=request().model_dump()).json()['run_id']
    selected = {'citation_id': 'source', 'document_id': created['document_id'], 'revision_id': created['revision_id'],
                'text': '原文', 'asset_ids': [], 'source_refs': [{'kind': 'pdf', 'page': 1}]}
    resources['runs'].runs.update_one({'run_id': rid}, {'$set': {'citations': [selected]}})
    path = '/api/v1/runs/' + rid + '/citations/source'
    response = client.get(path)
    assert response.status_code == 200
    original = response.json().get('original')
    assert original is not None, '缺少该引用精确修订的授权原件描述，前端无法定位PDF'
    assert original['asset_id'] == created['original_asset_id']
    assert original['media_type'] == 'application/pdf'
    assert original['url'] == '/api/v1/assets/' + created['original_asset_id']
    assert 'object_key' not in original and 'bucket' not in original
    assert client.get(original['url'], headers={'Range': 'bytes=0-4'}).content == b'%PDF-'
    user = resources['identity'].authenticate(client.cookies.get('support_session'))
    resources['identity'].store.users.update_one({'user_id': user.user_id}, {'$set': {'kb_ids': []}})
    assert client.get(path).status_code == 404
    assert client.get(original['url']).status_code == 404
