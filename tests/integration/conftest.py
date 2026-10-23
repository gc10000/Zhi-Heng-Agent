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
