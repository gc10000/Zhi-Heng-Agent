"""Mongo作为事实账本；发消息后才确认，崩溃最多重复而不丢任务。"""
from app.api.errors import APIError


def validate_key(key):
    if not isinstance(key, str) or not key or key.startswith('/') or any(s in key for s in ('..', '\\', ':', '//', '%')):
        raise ValueError('任务只能传递规范对象键，不能传本机路径或URL')


class Dispatcher:
    def __init__(self, jobs, send):
        self.jobs, self.send = jobs, send

    def dispatch(self, *, limit=50):
        self.jobs.requeue_expired()
        count = 0
        for row in self.jobs.jobs.find({'state': 'pending', 'dispatch_pending': True}).limit(limit):
            validate_key(row['object_key'])
            # broker中仅有job_id；原件地址、密钥、Windows路径均不随消息传递。
            self.send(row['job_id'])
            self.jobs.jobs.update_one({'job_id': row['job_id'], 'version': row['version'], 'state': 'pending'},
                                     {'$set': {'dispatch_pending': False}})
            count += 1
        return count
