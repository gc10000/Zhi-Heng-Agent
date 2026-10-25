import pytest
pytestmark = pytest.mark.integration


def test_checklist_is_suggestion_then_user_reports_are_append_only(support_client):
    client, headers, resources, user, cid, rid, citation = support_client
    url = f'/api/v1/conversations/{cid}/support'
    initial = client.post(url, headers=headers, json={'expected_version':0,'run_id':rid,
        'values':{'question':'通信失败','device':'AX-24','symptom':'指示灯熄灭'}})
    assert initial.status_code == 200, initial.text
    response = client.post(url+'/checklist',headers=headers,json={'expected_version':1,'run_id':rid})
    assert response.status_code == 200, response.text
    row = response.json()
    step = row['operations'][0]
    assert step['status'] == 'not_tried' and step['reports'] == []
    assert step['citation_ids'] == [citation['citation_id']] and '断电' in step['prerequisites']
    report_url = url+'/operations/'+step['operation_id']
    response = client.post(report_url, headers=headers, json={'expected_version':row['version'],'status':'ineffective','note':'已核对，仍失败'})
    assert response.status_code == 200, response.text
    row = response.json()
    assert row['operations'][0]['reports'][0]['source'] == 'user_report'
    assert row['operations'][0]['reports'][0]['recorded_at']
    # 重复生成不能使无效步骤复活，也不抹掉实际报告。
    response = client.post(url+'/checklist',headers=headers,json={'expected_version':row['version'],'run_id':rid})
    assert response.status_code == 200
    assert response.json()['operations'][0]['status'] == 'ineffective'
    assert len(response.json()['operations']) == 1


def test_checklist_rejects_foreign_run_before_any_change(support_client):
    client, headers, resources, user, cid, rid, citation = support_client
    other = client.post('/api/v1/conversations', headers=headers, json={'kb_id':'k'}).json()['conversation_id']
    response = client.post(f'/api/v1/conversations/{other}/support/checklist',headers=headers,json={'expected_version':0,'run_id':rid})
    assert response.status_code == 409
    assert client.get(f'/api/v1/conversations/{other}/support').json()['version'] == 0
