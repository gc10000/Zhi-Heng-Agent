"""独立Mongo的支持流程；不调用模型或访问课程资料。"""
import pytest

pytestmark = pytest.mark.integration


def test_support_wait_survives_resource_rebuild_and_only_collects_one_slot(m2_client):
    client, headers, resources = m2_client
    cid = client.post('/api/v1/conversations', headers=headers,
        json={'title': '隔离排障', 'kb_id': 'k', 'product_ids': []}).json()['conversation_id']
    url = f'/api/v1/conversations/{cid}/support'
    response = client.get(url)
    assert response.status_code == 200, response.text
    initial = response.json()
    assert initial['state'] == 'awaiting_input' and initial['requested_slot'] == 'question'
    result = client.post(url, headers=headers, json={'expected_version': 0,
        'values': {'question': '设备通信失败'}, 'confirmed': True})
    assert result.status_code == 200, result.text
    row = result.json()
    assert row['requested_slot'] == 'device' and row['slots']['question']['value'] == '设备通信失败'
    from app.conversations.repository import ConversationRepository
    resources['conversations'] = ConversationRepository(resources['db'])
    assert client.get(url).json() == row
    stale = client.post(url, headers=headers, json={'expected_version': 0, 'values': {'device': '猜测型号'}, 'confirmed': False})
    assert stale.status_code == 409


def test_support_unconfirmed_is_not_fact_and_no_progress_exits(m2_client):
    client, headers, _ = m2_client
    cid = client.post('/api/v1/conversations', headers=headers,
        json={'title': '隔离排障', 'kb_id': 'k', 'product_ids': []}).json()['conversation_id']
    url = f'/api/v1/conversations/{cid}/support'
    for version in range(3):
        response = client.post(url, headers=headers, json={'expected_version': version,
            'values': {'question': '可能通信失败'}, 'confirmed': False})
        assert response.status_code == 200, response.text
    row = response.json()
    assert row['state'] == 'handoff' and row['reason'] == 'no_progress'
    assert row['slots']['question']['confirmed'] is False
    assert row['requested_slot'] is None


def test_support_permission_and_optimistic_update(m2_client):
    client, headers, resources = m2_client
    from app.identity.models import Principal
    from app.conversations.models import ConversationInput
    other = Principal(user_id='other', username='other', role='viewer', kb_ids=('k',))
    cid = resources['conversations'].create(other, ConversationInput(title='他人', kb_id='k'))['conversation_id']
    url = f'/api/v1/conversations/{cid}/support'
    assert client.get(url).status_code == 404
    assert client.post(url, headers=headers, json={'expected_version':0,'values':{'question':'secret'}}).status_code == 404


def test_concurrent_support_updates_only_one_wins(m2_client):
    from concurrent.futures import ThreadPoolExecutor
    from app.support.repository import SupportRepository
    from app.support.models import SupportInput
    from app.identity.models import Principal
    from app.conversations.models import ConversationInput
    from app.api.errors import APIError
    _, _, resources = m2_client
    repo = SupportRepository(resources['conversations'], resources['runs'])
    user = Principal(user_id='race', username='race', role='viewer', kb_ids=('k',))
    cid = resources['conversations'].create(user, ConversationInput(kb_id='k'))['conversation_id']
    def change(value):
        try:
            return repo.update(user, cid, SupportInput(expected_version=0, values={'question': value}))['version']
        except APIError as error:
            return error.status
    with ThreadPoolExecutor(2) as pool: results = list(pool.map(change, ['一', '二']))
    assert sorted(results) == [1, 409]
    assert repo.get(user, cid)['version'] == 1
