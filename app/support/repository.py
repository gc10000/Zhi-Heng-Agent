"""会话内支持聚合采用单文档CAS，不依赖Mongo事务或进程内锁。"""
from copy import deepcopy
from datetime import datetime, timezone
from pymongo import ReturnDocument
from app.api.errors import APIError
from .workflow import initial, advance


def now():
    return datetime.now(timezone.utc).isoformat()


class SupportRepository:
    def __init__(self, conversations, runs):
        self.conversations, self.runs = conversations, runs

    def get(self, user, cid):
        return deepcopy(self.conversations.get(user, cid).get('support', initial()))

    def save(self, user, cid, current, updated):
        version = current['version']
        updated = deepcopy(updated) | {'version': version + 1, 'updated_at': now()}
        query = self.conversations.scope(user) | {'conversation_id': cid, 'archived': False}
        if version == 0:
            query['$or'] = [{'support.version': 0}, {'support': {'$exists': False}}]
        else:
            query['support.version'] = version
        row = self.conversations.conversations.find_one_and_update(query,
            {'$set': {'support': updated}}, return_document=ReturnDocument.AFTER)
        if row is None:
            raise APIError(409, 'version_conflict', '支持上下文已改变或会话已归档，请刷新后重试。')
        return deepcopy(row['support'])

    def update(self, user, cid, data):
        current = self.get(user, cid)
        run = self.runs.get(user, data.run_id) if data.run_id else None
        if run and (run['conversation_id'] != cid or run['state'] != 'completed'):
            raise APIError(409, 'support_run_unavailable', '仅能关联本会话已完成的回答。')
        if run:
            from .commands import check_run_context
            check_run_context(current, run)
        return self.save(user, cid, current, advance(current, data, at=now(), run=run))

    def editable(self, user, cid, expected_version):
        row = self.get(user, cid)
        if row['version'] != expected_version:
            raise APIError(409, 'version_conflict', '支持上下文已改变，请刷新后重试。')
        if row['state'] in {'resolved', 'cancelled'}:
            raise APIError(409, 'support_terminal', '已结束的支持流程不能继续添加操作。')
        return row

    def completed_run(self, user, cid, rid):
        row = self.runs.get(user, rid)
        if row['conversation_id'] != cid or row['state'] != 'completed':
            raise APIError(409, 'support_run_unavailable', '仅能关联本会话已完成的回答。')
        return row
