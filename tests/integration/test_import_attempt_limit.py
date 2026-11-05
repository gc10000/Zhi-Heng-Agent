"""合成导入次数上限：到期只封存，不再进入第二次推理。"""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.ingestion.jobs import JobRepository, job_view
from app.ingestion.dispatcher import Dispatcher
from app.api.errors import APIError

pytestmark=pytest.mark.integration


def registered(db,monkeypatch,limit):
    if limit is None:monkeypatch.delenv('IMPORT_MAX_ATTEMPTS',raising=False)
    else:monkeypatch.setenv('IMPORT_MAX_ATTEMPTS',str(limit))
    jobs=JobRepository(db)
    user=SimpleNamespace(user_id='synthetic',kb_ids=['k'])
    revision=dict(revision_id='r',owner_id='org',kb_id='k',document_id='d',object_key='test/manual.md',original_sha256='a'*64)
    row=jobs.register(user,revision,original_name='manual.md',original_format='md',expected_active=None)
    return jobs,user,row


def test_one_attempt_expiry_never_redispatches(mongo_db,monkeypatch):
    jobs,user,row=registered(mongo_db,monkeypatch,1)
    assert row.get('max_attempts')==1
    now=datetime.now(timezone.utc)
    first=jobs.claim(row['job_id'],lease_seconds=1,now=now)
    assert first['attempt']==1
    assert jobs.claim(row['job_id'],now=now+timedelta(seconds=2)) is None
    jobs.requeue_expired(now=now+timedelta(seconds=2))
    assert jobs.claim(row['job_id'],now=now+timedelta(seconds=3)) is None
    ended=jobs.get(user,row['job_id'])
    assert ended['state']=='failed' and ended['retryable'] is False
    assert ended['attempt']==1 and ended['error']['code']=='job_attempt_limit_reached'
    with pytest.raises(APIError):jobs.retry(user,row['job_id'],ended['version'])
    sent=[];Dispatcher(jobs,sent.append).dispatch();assert sent==[]


def test_limit_is_persistent_and_concurrent_claim_only_once(mongo_db,monkeypatch):
    jobs,user,row=registered(mongo_db,monkeypatch,1)
    monkeypatch.delenv('IMPORT_MAX_ATTEMPTS')
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims=list(pool.map(lambda _:jobs.claim(row['job_id']),range(4)))
    assert sum(x is not None for x in claims)==1
    current=jobs.get(user,row['job_id'])
    jobs.save(row['job_id'],1,current['lease_token'],{'state':'failed','retryable':True})
    assert job_view(jobs.get(user,row['job_id']))['retryable'] is False
    with pytest.raises(APIError):jobs.retry(user,row['job_id'],jobs.get(user,row['job_id'])['version'])


def test_pending_exhausted_is_not_sent_or_claimed(mongo_db,monkeypatch):
    jobs,user,row=registered(mongo_db,monkeypatch,1)
    jobs.jobs.update_one({'job_id':row['job_id']},{'$set':{'attempt':1}})
    assert jobs.claim(row['job_id']) is None
    sent=[];Dispatcher(jobs,sent.append).dispatch();assert sent==[]
    assert jobs.get(user,row['job_id'])['state']=='failed'


def test_two_attempt_limit_and_live_lease_preserved(mongo_db,monkeypatch):
    jobs,user,row=registered(mongo_db,monkeypatch,2)
    now=datetime.now(timezone.utc)
    first=jobs.claim(row['job_id'],lease_seconds=1,now=now)
    second=jobs.claim(row['job_id'],lease_seconds=10,now=now+timedelta(seconds=2))
    assert first['attempt']==1 and second['attempt']==2
    jobs.requeue_expired(now=now+timedelta(seconds=3))
    assert jobs.get(user,row['job_id'])['state']=='running'
    jobs.requeue_expired(now=now+timedelta(seconds=13))
    assert jobs.get(user,row['job_id'])['attempt']==2
    assert jobs.claim(row['job_id'],now=now+timedelta(seconds=14)) is None


def test_default_recovery_keeps_existing_behavior(mongo_db,monkeypatch):
    jobs,_,row=registered(mongo_db,monkeypatch,None)
    now=datetime.now(timezone.utc)
    assert 'max_attempts' not in row
    assert jobs.claim(row['job_id'],lease_seconds=1,now=now)['attempt']==1
    jobs.requeue_expired(now=now+timedelta(seconds=2))
    assert jobs.claim(row['job_id'],now=now+timedelta(seconds=3))['attempt']==2


@pytest.mark.parametrize('value',['0','-1','x','1.5','11'])
def test_invalid_limit_rejected_before_registration(mongo_db,monkeypatch,value):
    with pytest.raises(ValueError):registered(mongo_db,monkeypatch,value)
    assert mongo_db.import_jobs.count_documents({})==0
