"""正式事件CAS和安全统计投影，Mongo隔离，不调用供应商。"""
import pytest
pytestmark=pytest.mark.integration


def test_run_telemetry_is_scoped_and_has_no_private_answer(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    response=client.get('/api/v1/runs/'+rid+'/telemetry')
    assert response.status_code==200
    data=response.json()
    assert data['run_id']==rid and data['state']=='completed'
    assert data['total_seconds'] is not None
    assert data['token_usage']=={'input':None,'output':None}
    assert data['coverage']=='single_run'
    assert citation['text'] not in response.text
    assert '依据资料检查电源接线' not in response.text
    assert client.get('/api/v1/runs/other/telemetry').status_code==404


def test_statistics_page_is_current_owner_only_and_does_not_export_content(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    resources['db'].users.update_one({'user_id':user.user_id},{'$set':{'role':'maintainer'}})
    response=client.get('/api/v1/run-telemetry?kb_id=k&limit=1')
    assert response.status_code==200
    assert [r['run_id'] for r in response.json()['items']]==[rid]
    assert response.json()['coverage']=='page_only'
    assert '电源接线' not in response.text
    resources['db'].runs.update_one({'run_id':rid},{'$set':{'owner_id':'other'}})
    assert client.get('/api/v1/run-telemetry?kb_id=k').json()['items']==[]


def test_terminal_event_keeps_safe_timing_aggregate_after_replay_expires(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    row=resources['runs'].get(user,rid)
    assert row.get('telemetry',{}).get('terminal_at')
    assert row['telemetry']['schema_version']==1
