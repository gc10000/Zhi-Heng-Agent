"""导入任务持久账本；上传成功与执行完成是不同状态。"""
from datetime import datetime, timezone, timedelta
from uuid import uuid4
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument
from app.api.errors import APIError


def job_view(row):
    return {k: row[k] for k in ('job_id', 'document_id', 'revision_id', 'kb_id', 'state', 'stage', 'attempt',
                               'version', 'error', 'retryable', 'created_at') if k in row}


class JobRepository:
    def __init__(self, db):
        self.db, self.jobs = db, db.import_jobs
        self.jobs.create_index('job_id', unique=True)
        self.jobs.create_index('revision_id', unique=True)
        self.jobs.create_index([('dispatch_pending', 1), ('state', 1)])

    def register(self, user, revision, *, original_name, original_format, expected_active):
        key = {'revision_id': revision['revision_id']}
        row = key | {'job_id': str(uuid4()), 'owner_id': user.user_id, 'knowledge_owner_id': revision['owner_id'],
                     'kb_id': revision['kb_id'], 'document_id': revision['document_id'],
                     'object_key': revision['object_key'], 'sha256': revision['original_sha256'],
                     'original_name': original_name, 'format': original_format, 'expected_active': expected_active,
                     'state': 'pending', 'stage': 'uploaded', 'dispatch_pending': True, 'attempt': 0,
                     'version': 0, 'retryable': False, 'created_at': datetime.now(timezone.utc)}
        try:
            self.jobs.update_one(key, {'$setOnInsert': row}, upsert=True)
        except DuplicateKeyError:
            pass
        return self.jobs.find_one(key)

    def get(self, user, jid):
        row = self.jobs.find_one({'job_id': jid, 'owner_id': user.user_id, 'kb_id': {'$in': list(user.kb_ids)}})
        if row is None:
            raise APIError(404, 'not_found', '导入任务不存在或不在授权范围。')
        return row

    def retry(self, user, jid, expected_version):
        row = self.get(user, jid)
        if row['state'] != 'failed' or not row['retryable']:
            raise APIError(409, 'job_not_retryable', '任务不能自动重试，请核对格式、权限或配置。')
        result = self.jobs.update_one({'job_id': jid, 'version': expected_version, 'state': 'failed', 'retryable': True},
            {'$set': {'state': 'pending', 'dispatch_pending': True, 'error': None}, '$inc': {'version': 1}})
        if not result.matched_count:
            raise APIError(409, 'version_conflict', '任务已改变，请刷新。')
        return job_view(self.get(user, jid))

    def claim(self, jid, *, lease_seconds=60, now=None):
        now = now or datetime.now(timezone.utc)
        row = self.jobs.find_one_and_update({'job_id': jid, '$or': [
            {'state': 'pending'}, {'state': 'running', 'lease_until': {'$lte': now}}]},
            {'$set': {'state': 'running', 'lease_until': now + timedelta(seconds=lease_seconds),
                      'lease_token': uuid4().hex, 'dispatch_pending': False}, '$inc': {'attempt': 1, 'version': 1}},
            return_document=ReturnDocument.AFTER)
        return row

    def fence(self, jid, attempt, token, *, now=None):
        now = now or datetime.now(timezone.utc)
        row = self.jobs.find_one({'job_id': jid, 'attempt': attempt, 'lease_token': token,
                                   'state': 'running', 'lease_until': {'$gt': now}})
        if row is None:
            raise APIError(409, 'job_lease_lost', '任务执行租约已失效。')
        return row

    def save(self, jid, attempt, token, fields, *, now=None):
        now = now or datetime.now(timezone.utc)
        result = self.jobs.update_one({'job_id': jid, 'attempt': attempt, 'lease_token': token,
            'state': 'running', 'lease_until': {'$gt': now}}, {'$set': fields, '$inc': {'version': 1}})
        if not result.matched_count:
            raise APIError(409, 'job_lease_lost', '任务执行租约已失效。')

    def renew(self, jid, attempt, token, *, lease_seconds=60, now=None):
        now = now or datetime.now(timezone.utc)
        self.save(jid, attempt, token, {'lease_until': now + timedelta(seconds=lease_seconds)}, now=now)

    def requeue_expired(self, *, now=None):
        now = now or datetime.now(timezone.utc)
        return self.jobs.update_many({'state': 'running', 'lease_until': {'$lte': now}},
            {'$set': {'state': 'pending', 'dispatch_pending': True}, '$inc': {'version': 1}}).modified_count
