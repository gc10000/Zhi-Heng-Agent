"""真实Mongo归属/同时间消息分页/快照冻结，不删除现场。"""
from uuid import uuid4
import pytest
pytestmark = pytest.mark.integration


def test_ownership_cursor_and_immutable_turn_snapshot(mongo_db):
    from app.api.errors import APIError
    from app.identity.models import Principal
    from app.conversations.models import ConversationInput, ConversationPatch
    from app.conversations.repository import ConversationRepository
    repo = ConversationRepository(mongo_db)
    user = Principal(user_id=uuid4().hex, username='a', role='viewer', kb_ids=('k',))
    other = user.model_copy(update={'user_id': uuid4().hex})
    conv = repo.create(user, ConversationInput(kb_id='k', product_ids=['old']))
    cid = conv['conversation_id']
    assert repo.list(other)['items'] == []
    for operation in (lambda: repo.get(other, cid), lambda: repo.history(other, cid),
                      lambda: repo.patch(other, cid, ConversationPatch(expected_version=0, title='越权'))):
        with pytest.raises(APIError) as denied:
            operation()
        assert denied.value.status == 404
    selected = {'product_ids': ['old'], 'version': 1}
    for i in range(5):
        repo.append_message(user, cid, run_id=cid+str(i), role='user', text=str(i), product_snapshot=selected)
    selected['product_ids'][0] = 'new'
    # 合成相同时间戳，只改独立测试消息以验证排序键，不做真实破坏性故障。
    repo.messages.update_many({'conversation_id': cid}, {'$set': {'created_at': 'same-time'}})
    values, cursor = [], 0
    while True:
        page = repo.history(user, cid, after=cursor, limit=2)
        values.extend(page['items'])
        if page['next_cursor'] is None:
            break
        cursor = int(page['next_cursor'])
    assert [m['text'] for m in values] == ['0', '1', '2', '3', '4']
    assert all(m['product_snapshot']['product_ids'] == ['old'] for m in values)
    assert len({m['message_id'] for m in values}) == 5
    assert repo.patch(user, cid, ConversationPatch(expected_version=0, title='新标题'))['version'] == 1
    with pytest.raises(APIError) as conflict:
        repo.patch(user, cid, ConversationPatch(expected_version=0, title='迟到'))
    assert conflict.value.status == 409
    revoked = user.model_copy(update={'kb_ids': ()})
    with pytest.raises(APIError):
        repo.history(revoked, cid)


def test_real_http_conversation_auth_and_pagination(mongo_db):
    from contextlib import asynccontextmanager
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.settings import Settings
    from app.identity.service import IdentityService, MongoIdentityStore
    from app.conversations.repository import ConversationRepository
    service = IdentityService(MongoIdentityStore(mongo_db))
    username = uuid4().hex
    service.add_user(username, 'isolated-password', role='viewer', kb_ids=['k'])
    @asynccontextmanager
    async def resources(settings):
        yield {'identity': service, 'conversations': ConversationRepository(mongo_db)}
    with TestClient(create_app(settings=Settings('unused', mongo_db.name, ('http://testserver',), False), resource_factory=resources)) as client:
        data = client.post('/api/v1/auth/login', headers={'Origin': 'http://testserver'}, json={'username': username, 'password': 'isolated-password'}).json()
        headers = {'Origin': 'http://testserver', 'X-CSRF-Token': data['csrf_token']}
        assert client.post('/api/v1/conversations', json={'kb_id': 'k'}).status_code == 403
        assert client.post('/api/v1/conversations', headers=headers, json={'kb_id': 'other'}).status_code == 404
        assert client.post('/api/v1/conversations', headers=headers, json={'kb_id': 'k', 'owner_id': 'forged'}).status_code == 422
        ids = [client.post('/api/v1/conversations', headers=headers, json={'kb_id': 'k'}).json()['conversation_id'] for _ in range(3)]
        page = client.get('/api/v1/conversations?limit=2').json()
        rest = client.get('/api/v1/conversations', params={'limit': 2, 'cursor': page['next_cursor']}).json()
        assert {r['conversation_id'] for r in page['items'] + rest['items']} == set(ids)
        assert client.get('/api/v1/conversations/' + ids[0] + '/messages?cursor=-1').status_code == 422
