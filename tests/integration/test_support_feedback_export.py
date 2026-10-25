import pytest
pytestmark=pytest.mark.integration


def test_confirmed_export_escapes_fields_and_preserves_versions(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    response=client.post('/api/v1/cases',headers=headers,json={'run_id':rid,'expected_support_version':0})
    draft=response.json();url='/api/v1/cases/'+draft['case_id']
    response=client.get(url+'/export')
    assert response.status_code==409,response.text
    edited=client.patch(url,headers=headers,json={'expected_version':0,'fields':{'summary':'<script>bad</script> ![x](javascript:bad)\n# 注入标题'}})
    assert edited.status_code==200
    assert client.post(url+'/confirm',headers=headers,json={'expected_version':1}).status_code==200
    response=client.get(url+'/export')
    assert response.status_code==200,response.text
    text=response.json()['markdown']
    assert '<script>' not in text and '![x](' not in text and '\n# 注入标题' not in text
    assert citation['revision_id'] in text and citation['document_id'] in text
    assert '未知' in text and '用户自报' in text
    resources['db'].knowledge_documents.update_one({'document_id':citation['document_id']},{'$set':{'kb_id':'revoked'}})
    assert client.get(url+'/export').status_code==404


def test_feedback_is_scoped_idempotent_pending_and_does_not_publish(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    payload={'run_id':rid,'citation_ids':[citation['citation_id']],'category':'operation','note':'已试未解决','client_request_id':'once'}
    response=client.post('/api/v1/feedback',headers=headers,json=payload)
    assert response.status_code==201,response.text
    assert response.json()['state']=='pending_review'
    repeated=client.post('/api/v1/feedback',headers=headers,json=payload)
    assert repeated.json()['feedback_id']==response.json()['feedback_id']
    assert resources['db'].support_feedback.count_documents({})==1
    assert client.post('/api/v1/feedback',headers=headers,json=payload|{'note':'changed'}).status_code==409
    assert client.post('/api/v1/feedback',headers=headers,json=payload|{'citation_ids':['foreign'],'client_request_id':'bad'}).status_code==422
    assert resources['db'].knowledge_documents.count_documents({})==1
