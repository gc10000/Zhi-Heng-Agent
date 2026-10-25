import pytest
from tests.contract.test_auth import auth_client,login
from app.support.export import escape,export_markdown
from app.api.errors import APIError


def test_export_blocks_unconfirmed_and_escapes_injection():
    with pytest.raises(APIError):export_markdown({'status':'draft'})
    text=escape('<script>x</script> ![pic](javascript:x)\n# injected\n- item')
    assert '<script>' not in text and '![pic](' not in text
    assert '\n# injected' not in text and '\n- item' not in text
    assert 'doc-123'==escape('doc-123')


@pytest.mark.parametrize('category',['model','evidence','missing_material','operation','image'])
def test_feedback_requires_run_authorization(auth_client,category):
    client,_,_=auth_client
    response=client.post('/api/v1/feedback',json={'run_id':'r','client_request_id':'k','category':category,'note':'反馈'})
    assert response.status_code==401


def test_feedback_unknown_category_and_injected_owner_rejected(auth_client):
    client,_,_=auth_client;result=login(client)
    headers={'Origin':'http://testserver','X-CSRF-Token':result.json()['csrf_token']}
    data={'run_id':'r','client_request_id':'k','category':'evidence','note':'反馈'}
    for changed in [{'category':'execute_device'},{'owner_id':'foreign'},{'note':''}]:
        assert client.post('/api/v1/feedback',headers=headers,json=data|changed).status_code==422
