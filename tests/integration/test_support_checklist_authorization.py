"""清单真实API→隔离Mongo：新引用合法不能授予旧聚合原文的访问权。"""
from copy import deepcopy
import pytest
from app.runs.models import RunInput

pytestmark = pytest.mark.integration


def bind_second_document(client, headers, resources, user, cid):
    gateway = resources['knowledge']()
    repo = gateway.repo('k')
    document = repo.register_document('m5-r2-second', name='另一份隔离手册.md', product_ids=[])
    revision = repo.create_revision(document.document_id, 'm5-r2-second', original_sha256='f'*64,
                                   object_key='m5-isolated/second.md')
    repo.documents.update_one({'document_id': document.document_id}, {'$set': {'active_revision_id': revision.revision_id}})
    citation = {'citation_id': 'cite-second', 'document_id': document.document_id,
                'revision_id': revision.revision_id, 'chunk_uid': 'second', 'text': '检查另一份手册中的通信指示灯。',
                'source_refs': [{'kind': 'markdown', 'line_start': 1, 'line_end': 1}], 'asset_ids': []}
    row = resources['run_service'].create(user, cid, RunInput(question='新的回答', kb_id='k', client_request_id='second'))
    token = resources['commands'].start(user, row['run_id'])
    resources['commands'].finish(user, row['run_id'], token, 'completed', {'answer': '隔离回答B'},
        fields={'answer': '隔离回答B', 'citations': [citation]})
    url = f'/api/v1/conversations/{cid}/support'
    current = client.get(url).json()
    result = client.post(url, headers=headers, json={'expected_version': current['version'], 'run_id': row['run_id']})
    assert result.status_code == 200, result.text
    return result.json(), row['run_id'], citation


@pytest.mark.parametrize('old_source', ['operation', 'tool_output'])
@pytest.mark.parametrize('revoked', [True, False])
def test_checklist_authorizes_old_aggregate_before_any_write(support_client, old_source, revoked):
    client, headers, resources, user, cid, rid, citation = support_client
    url = f'/api/v1/conversations/{cid}/support'
    assert client.post(url, headers=headers, json={'expected_version': 0, 'run_id': rid,
        'values': {'device': 'AX-24', 'symptom': '无响应'}}).status_code == 200
    if old_source == 'operation':
        result = client.post(url+'/checklist', headers=headers, json={'expected_version': 1, 'run_id': rid})
    else:
        result = client.post(url+'/tools', headers=headers, json={'expected_version': 1, 'tool': 'read_evidence',
            'arguments': {'citation_id': citation['citation_id']}})
    assert result.status_code == 200, result.text
    current, second_run, new_citation = bind_second_document(client, headers, resources, user, cid)
    assert current['citations'] == [new_citation]
    if revoked:
        resources['db'].knowledge_documents.update_one({'document_id': citation['document_id']}, {'$set': {'kb_id': 'revoked'}})
        assert client.get(url).status_code == 404
    before = deepcopy(resources['conversations'].get(user, cid)['support'])
    response = client.post(url+'/checklist', headers=headers,
        json={'expected_version': before['version'], 'run_id': second_run})
    if revoked:
        assert response.status_code == 404, response.text
        assert citation['text'] not in response.text
        assert resources['conversations'].get(user, cid)['support'] == before
    else:
        assert response.status_code == 200, response.text
        assert response.json()['version'] == before['version'] + 1
        assert any(new_citation['text'] == step['suggestion'] for step in response.json()['operations'])


def test_checklist_refuses_revoked_new_run_citation_without_mutation(support_client):
    client, headers, resources, user, cid, rid, citation = support_client
    url = f'/api/v1/conversations/{cid}/support'
    assert client.post(url, headers=headers, json={'expected_version': 0, 'run_id': rid,
        'values': {'device': 'AX-24', 'symptom': '无响应'}}).status_code == 200
    before = deepcopy(resources['conversations'].get(user, cid)['support'])
    resources['db'].knowledge_documents.update_one({'document_id': citation['document_id']}, {'$set': {'kb_id': 'revoked'}})
    response = client.post(url+'/checklist', headers=headers, json={'expected_version': 1, 'run_id': rid})
    assert response.status_code == 404
    assert resources['conversations'].get(user, cid)['support'] == before
