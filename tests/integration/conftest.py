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
    yield client[name]
    client.close()
