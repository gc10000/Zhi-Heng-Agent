"""真实测试仅连接显式独立库，不删除库/集合，保留现场供复核。"""
import os
import pytest


@pytest.fixture
def mongo_db():
    name = os.getenv('M1_TEST_DB', '')
    if not name.startswith('m1_test_'):
        pytest.fail('真实集成须显式填写M1_TEST_DB=m1_test_开头独立库；不自动跳过')
    from dotenv import load_dotenv
    from pathlib import Path
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    from pymongo import MongoClient
    client=MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000)
    client.admin.command('ping')
    from uuid import uuid4
    # 扫描类用例必须独立账本，不能派发或恢复前例保留的现场。
    yield client[name + '_' + uuid4().hex[:8]]
    client.close()


@pytest.fixture
def m2_client(mongo_db):
    """真实HTTP到独立Mongo的新入口，账号/会话每次随机隔离。"""
    from contextlib import asynccontextmanager
    from uuid import uuid4
    from fastapi.testclient import TestClient
    from app.main import create_app
    from app.settings import Settings
    from app.identity.service import IdentityService, MongoIdentityStore
    from app.conversations.repository import ConversationRepository
    from app.runs.repository import RunRepository
    from app.runs.service import RunService
    from app.runs.events import EventLedger
    from app.runs.commands import RunCommands
    identity = IdentityService(MongoIdentityStore(mongo_db))
    username = uuid4().hex
    identity.add_user(username, 'isolated-password', role='viewer', kb_ids=['k'])
    conversations = ConversationRepository(mongo_db)
    runs = RunRepository(mongo_db, conversations)
    resources = {'db': mongo_db, 'identity': identity, 'conversations': conversations,
                 'runs': runs, 'run_service': RunService(runs), 'events': EventLedger(runs)}
    resources['commands'] = RunCommands(runs, resources['events'])
    @asynccontextmanager
    async def factory(settings):
        yield resources
    app = create_app(settings=Settings('unused', mongo_db.name, ('http://testserver',), False), resource_factory=factory)
    with TestClient(app, raise_server_exceptions=False) as client:
        result = client.post('/api/v1/auth/login', headers={'Origin': 'http://testserver'},
                             json={'username': username, 'password': 'isolated-password'})
        assert result.status_code == 200
        headers = {'Origin': 'http://testserver', 'X-CSRF-Token': result.json()['csrf_token']}
        yield client, headers, resources


@pytest.fixture
def support_client(m2_client):
    """支持流程真实Mongo夹具：合成已发布资料和运行，不调用模型。"""
    from app.knowledge.gateway import KnowledgeGateway
    from app.identity.models import Principal
    from app.runs.models import RunInput
    client, headers, resources = m2_client
    user = Principal(**client.get('/api/v1/me').json()['user'])
    g = KnowledgeGateway(resources['db'], None, owner_id='m5-isolated')
    repo = g.repo('k')
    document = repo.register_document('m5-fixture', name='隔离操作手册.md', product_ids=[])
    revision = repo.create_revision(document.document_id, 'm5-fixture', original_sha256='e'*64, object_key='m5-isolated/manual.md')
    repo.documents.update_one({'document_id':document.document_id}, {'$set':{'active_revision_id':revision.revision_id}})
    citation = {'citation_id':'cite-m5', 'document_id':document.document_id, 'revision_id':revision.revision_id,
        'chunk_uid':'chunk-m5', 'text':'操作前提：设备已断电。检查电源接线并核对24V输入。风险：带电操作存在危险。',
        'source_refs':[{'kind':'markdown','line_start':1,'line_end':1}], 'asset_ids':[]}
    resources['knowledge'] = lambda: g
    cid = client.post('/api/v1/conversations', headers=headers, json={'kb_id':'k','title':'隔离排障'}).json()['conversation_id']
    row = resources['run_service'].create(user, cid, RunInput(question='设备通信失败',kb_id='k',client_request_id='m5-fixture'))
    token = resources['commands'].start(user, row['run_id'])
    answer = '依据资料检查电源接线。[1]'
    resources['commands'].finish(user,row['run_id'],token,'completed',{'answer':answer},fields={
        'answer':answer,'citations':[citation], 'completion_snapshot':{'text':answer,'citations':[citation],'product_snapshot':{'product_ids':[]}}})
    yield client, headers, resources, user, cid, row['run_id'], citation
