import pytest
pytestmark = pytest.mark.integration


def test_draft_edit_regenerate_confirm_is_versioned_and_preserved(support_client):
    client, headers, resources, user, cid, rid, citation = support_client
    response = client.post('/api/v1/cases',headers=headers,json={'run_id':rid,'expected_support_version':0})
    assert response.status_code == 201, response.text
    draft = response.json()
    assert draft['status'] == 'draft' and draft['fields']['environment'] == '未知'
    assert draft['citations'] == [citation]
    url = '/api/v1/cases/'+draft['case_id']
    response = client.patch(url,headers=headers,json={'expected_version':0,'fields':{'summary':'用户编辑：需交接，尚未解决'}})
    assert response.status_code == 200, response.text
    edited = response.json()
    repeated = client.post('/api/v1/cases',headers=headers,json={'run_id':rid,'expected_support_version':0})
    assert repeated.json()['fields']['summary'] == edited['fields']['summary']
    assert repeated.json()['version'] == 1
    assert client.post(url+'/confirm',headers=headers,json={'expected_version':0}).status_code == 409
    confirmed = client.post(url+'/confirm',headers=headers,json={'expected_version':1})
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()['status'] == 'confirmed'
    assert confirmed.json()['confirmed_at']
    assert client.patch(url,headers=headers,json={'expected_version':2,'fields':{'summary':'覆盖'}}).status_code == 409
    assert client.get('/api/v1/cases?limit=1').json()['items'][0]['case_id'] == draft['case_id']


def test_case_owner_and_support_version_guards(support_client):
    client, headers, resources, user, cid, rid, citation = support_client
    assert client.post('/api/v1/cases',headers=headers,json={'run_id':rid,'expected_support_version':9}).status_code == 409
    draft = client.post('/api/v1/cases',headers=headers,json={'run_id':rid,'expected_support_version':0})
    assert draft.status_code == 201
    resources['db'].support_cases.update_one({'case_id':draft.json()['case_id']},{'$set':{'owner_id':'other'}})
    assert client.get('/api/v1/cases/'+draft.json()['case_id']).status_code == 404
    assert client.get('/api/v1/cases').json()['items'] == []
