import pytest
from app.runs.models import RunInput
pytestmark=pytest.mark.integration


def test_future_run_freezes_correction_and_late_old_evidence_rejected(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    url=f'/api/v1/conversations/{cid}/support'
    first=client.post(url,headers=headers,json={'expected_version':0,'run_id':rid,
        'values':{'device':'AX-24','symptom':'通信失败'}}).json()
    assert first['state']=='ready'
    second=client.post(url,headers=headers,json={'expected_version':1,'values':{'device':'AX-25'}}).json()
    new=resources['run_service'].create(user,cid,RunInput(question='它仍然失败',kb_id='k',client_request_id='after-correction'))
    stored=resources['runs'].get(user,new['run_id'])
    assert stored.get('support_snapshot',{}).get('slots',{}).get('device',{}).get('value')=='AX-25'
    # 用户可继续更正，已开始run不得被回写；其晚到产物不能替换新上下文。
    assert client.post(url,headers=headers,json={'expected_version':2,'values':{'environment':'新环境'}}).status_code==200
    token=resources['commands'].start(user,new['run_id'])
    resources['commands'].finish(user,new['run_id'],token,'completed',{'answer':'synthetic'},fields={'answer':'synthetic','citations':[citation]})
    result=client.post(url,headers=headers,json={'expected_version':3,'run_id':new['run_id']})
    assert result.status_code==409,result.text
    assert resources['runs'].get(user,new['run_id'])['support_snapshot']['context_version']==second['context_version']
    assert client.get(url).json()['slots']['environment']['value']=='新环境'


def test_cancelled_support_rejects_stale_commands_and_is_not_future_context(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    url=f'/api/v1/conversations/{cid}/support'
    row=client.post(url,headers=headers,json={'expected_version':0,'run_id':rid,'values':{'device':'AX-24','symptom':'通信失败'}}).json()
    assert client.post(url,headers=headers,json={'expected_version':row['version'],'action':'cancel'}).status_code==200
    assert client.post(url,headers=headers,json={'expected_version':1,'values':{'device':'AX-25'}}).status_code==409
    new=resources['run_service'].create(user,cid,RunInput(question='新问题',kb_id='k',client_request_id='new-after-cancel'))
    assert resources['runs'].get(user,new['run_id']).get('support_snapshot') is None


def test_corrected_device_cannot_generate_old_checklist(support_client):
    client,headers,resources,user,cid,rid,citation=support_client
    url=f'/api/v1/conversations/{cid}/support'
    assert client.post(url,headers=headers,json={'expected_version':0,'run_id':rid,'values':{'device':'AX-24','symptom':'通信失败'}}).status_code==200
    assert client.post(url,headers=headers,json={'expected_version':1,'values':{'device':'AX-25'}}).status_code==200
    result=client.post(url+'/checklist',headers=headers,json={'expected_version':2,'run_id':rid})
    assert result.status_code==409,result.text
    assert client.get(url).json()['operations']==[]


def test_context_change_between_prepare_and_claim_refuses_stale_snapshot(support_client):
    from app.support.repository import SupportRepository
    from app.support.models import SupportInput
    from app.api.errors import APIError
    client,headers,resources,user,cid,rid,citation=support_client
    support=SupportRepository(resources['conversations'],resources['runs'])
    support.update(user,cid,SupportInput(expected_version=0,run_id=rid,values={'device':'AX-24','symptom':'失败'}))
    prepared=resources['runs'].prepare(user,cid,RunInput(question='继续',kb_id='k',client_request_id='prepared-before-change'))
    support.update(user,cid,SupportInput(expected_version=1,values={'device':'AX-25'}))
    with pytest.raises(APIError) as error: resources['runs'].reconcile(user,prepared['run_id'])
    assert error.value.status==409
    assert resources['conversations'].get(user,cid)['active_run_id'] is None
    assert resources['conversations'].messages.count_documents({'run_id':prepared['run_id']})==0
