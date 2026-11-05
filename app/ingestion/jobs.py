"""导入任务持久账本；上传成功与执行完成是不同状态。"""
from datetime import datetime, timezone, timedelta
import os
from uuid import uuid4
from pymongo.errors import DuplicateKeyError
from pymongo import ReturnDocument
from app.api.errors import APIError


def job_view(row):
    view = {k: row[k] for k in ('job_id', 'document_id', 'revision_id', 'kb_id', 'state', 'stage', 'attempt',
                               'version', 'error', 'retryable', 'created_at') if k in row}
    if 'max_attempts' in row and row['attempt'] >= row['max_attempts']:
        view['retryable'] = False
    return view


def attempts_available():
    """只消费任务登记时冻结的上限，后续环境变化不能重新领取。"""
    return {'$or': [{'max_attempts': {'$exists': False}},
                    {'$expr': {'$lt': ['$attempt', '$max_attempts']}}]}


class JobRepository:
    def __init__(self, db):
        self.db, self.jobs = db, db.import_jobs
        self.jobs.create_index('job_id', unique=True)
        self.jobs.create_index('revision_id', unique=True)
        self.jobs.create_index([('dispatch_pending', 1), ('state', 1)])

    def register(self, user, revision, *, original_name, original_format, expected_active):
        raw_limit = os.getenv('IMPORT_MAX_ATTEMPTS')
        if raw_limit is not None and raw_limit not in {str(n) for n in range(1, 11)}:
            raise ValueError('IMPORT_MAX_ATTEMPTS须为1至10的整数，未配置沿用普通恢复。')
        key = {'revision_id': revision['revision_id']}
        row = key | {'job_id': str(uuid4()), 'owner_id': user.user_id, 'knowledge_owner_id': revision['owner_id'],
                     'kb_id': revision['kb_id'], 'document_id': revision['document_id'],
                     'object_key': revision['object_key'], 'sha256': revision['original_sha256'],
                     'original_name': original_name, 'format': original_format, 'expected_active': expected_active,
                     'state': 'pending', 'stage': 'uploaded', 'dispatch_pending': True, 'attempt': 0,
                     'version': 0, 'retryable': False, 'created_at': datetime.now(timezone.utc)}
        if raw_limit is not None:
            row['max_attempts'] = int(raw_limit)
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
        if (row['state'] != 'failed' or not row['retryable'] or
                ('max_attempts' in row and row['attempt'] >= row['max_attempts'])):
            raise APIError(409, 'job_not_retryable', '任务不能自动重试，请核对格式、权限或配置。')
        result = self.jobs.update_one({'job_id': jid, 'version': expected_version, 'state': 'failed',
                                      'retryable': True, **attempts_available()},
            {'$set': {'state': 'pending', 'dispatch_pending': True, 'error': None}, '$inc': {'version': 1}})
        if not result.matched_count:
            raise APIError(409, 'version_conflict', '任务已改变，请刷新。')
        return job_view(self.get(user, jid))

    def claim(self, jid, *, lease_seconds=60, now=None):
        now = now or datetime.now(timezone.utc)
        row = self.jobs.find_one_and_update({'job_id': jid, '$and': [attempts_available(), {'$or': [
            {'state': 'pending'}, {'state': 'running', 'lease_until': {'$lte': now}}]}]},
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
        # 不抢占有效租约；已用完的pending（含旧消息）也不能再次派发。
        ended = self.jobs.update_many({'max_attempts': {'$exists': True},
            '$expr': {'$gte': ['$attempt', '$max_attempts']}, '$or': [
                {'state': 'pending'}, {'state': 'running', 'lease_until': {'$lte': now}}]},
            {'$set': {'state': 'failed', 'retryable': False, 'dispatch_pending': False,
                      'error': {'code': 'job_attempt_limit_reached',
                                'message': '导入执行次数已用完；保留现场，不自动再次派发。'}},
             '$inc': {'version': 1}}).modified_count
        return ended + self.jobs.update_many({'state': 'running', 'lease_until': {'$lte': now},
                                               **attempts_available()},
            {'$set': {'state': 'pending', 'dispatch_pending': True}, '$inc': {'version': 1}}).modified_count
