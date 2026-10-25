import pytest
pytestmark=pytest.mark.integration


def test_revoked_citation_is_not_exposed_in_support_or_case_snapshots(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    url=f'/api/v1/conversations/{cid}/support'
    assert client.post(url,headers=headers,json={'expected_version':0,'run_id':rid,'values':{'device':'AX-24','symptom':'无响应'}}).status_code==200
    resources['db'].knowledge_documents.update_one({'document_id':citation['document_id']},{'$set':{'kb_id':'revoked'}})
    result=client.get(url)
    assert result.status_code==404,result.text
    assert citation['text'] not in result.text


def test_exhausted_ineffective_steps_exit_without_claiming_resolution(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    url=f'/api/v1/conversations/{cid}/support'
    client.post(url,headers=headers,json={'expected_version':0,'run_id':rid,'values':{'device':'AX-24','symptom':'无响应'}})
    row=client.post(url+'/checklist',headers=headers,json={'expected_version':1,'run_id':rid}).json()
    response=client.post(url+'/operations/'+row['operations'][0]['operation_id'],headers=headers,
        json={'expected_version':2,'status':'ineffective','note':'已试仍未解决'})
    assert response.status_code==200,response.text
    row=response.json()
    assert row['state']=='handoff' and row['reason']=='all_steps_ineffective'
    assert row['operations'][0]['reports'][0]['source']=='user_report'
