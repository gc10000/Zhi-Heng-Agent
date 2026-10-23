"""创建运行使用同一可恢复协议，不以进程内锁保证幂等。"""
from app.runs.models import snapshot


class RunService:
    def __init__(self, repository):
        self.repo = repository

    def create(self, user, cid, data):
        row = self.repo.prepare(user, cid, data)
        return snapshot(self.repo.reconcile(user, row['run_id']))
