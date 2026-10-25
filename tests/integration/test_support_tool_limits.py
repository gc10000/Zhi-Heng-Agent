import pytest
pytestmark=pytest.mark.integration


def test_tools_reject_document_commands_and_stop_on_repeat(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    url=f'/api/v1/conversations/{cid}/support'
    assert client.post(url,headers=headers,json={'expected_version':0,'run_id':rid,
        'values':{'question':'通信失败','device':'AX-24','symptom':'无响应'}}).status_code==200
    unknown=client.post(url+'/tools',headers=headers,json={'expected_version':1,'tool':'execute_device','arguments':{'command':'erase'}})
    assert unknown.status_code==422
    for version in [1,3]:
        result=client.post(url+'/tools',headers=headers,json={'expected_version':version,'tool':'read_evidence','arguments':{'citation_id':citation['citation_id']}})
        assert result.status_code==200,result.text
    row=result.json()
    assert row['state']=='handoff' and row['reason']=='tool_repeat'
    assert len(row['tool_calls'])==2
    assert row['tool_calls'][0]['output']['items'][0]['revision_id']==citation['revision_id']
    assert client.post(url+'/tools',headers=headers,json={'expected_version':5,'tool':'read_evidence','arguments':{'citation_id':citation['citation_id']}}).status_code==409
