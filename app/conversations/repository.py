"""会话范围查询及按原子序号分页；相同时间戳不会吞消息。"""
import copy
from datetime import datetime, timezone
from uuid import uuid4
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.knowledge.models import stable_id
from app.knowledge.repository import fingerprint


def public(value):
    return {k: v for k, v in value.items() if not k.startswith('_')}


class ConversationRepository:
    def __init__(self, db):
        self.db = db
        self.conversations, self.messages = db.conversations, db.messages
        self.conversations.create_index('conversation_id', unique=True)
        self.conversations.create_index([('owner_id', 1), ('conversation_id', 1)])
        self.messages.create_index('message_id', unique=True)
        self.messages.create_index([('conversation_id', 1), ('ordinal', 1)], unique=True)

    def create(self, user, data):
        if data.kb_id not in user.kb_ids:
            raise APIError(404, 'not_found', '知识库不在授权范围。')
        row = data.model_dump() | {'conversation_id': str(uuid4()), 'owner_id': user.user_id, 'version': 0,
                                  'archived': False, 'active_run_id': None, 'message_seq': 0,
                                  'created_at': datetime.now(timezone.utc).isoformat()}
        self.conversations.insert_one(copy.deepcopy(row))
        return public(row)

    def scope(self, user):
        return {'owner_id': user.user_id, 'kb_id': {'$in': list(user.kb_ids)}}

    def get(self, user, cid):
        row = self.conversations.find_one(self.scope(user) | {'conversation_id': cid})
        if row is None:
            raise APIError(404, 'not_found', '会话不存在或不在授权范围。')
        return public(row)

    def list(self, user, *, cursor=None, limit=50):
        query = self.scope(user)
        if cursor:
            query['conversation_id'] = {'$gt': cursor}
        rows = list(self.conversations.find(query).sort('conversation_id', 1).limit(limit + 1))
        return {'items': [public(r) for r in rows[:limit]],
                'next_cursor': rows[limit-1]['conversation_id'] if len(rows) > limit else None}

    def patch(self, user, cid, data):
        self.get(user, cid)
        fields = {k: v for k, v in data.model_dump().items() if k != 'expected_version' and v is not None}
        row = self.conversations.find_one_and_update(self.scope(user) | {'conversation_id': cid, 'version': data.expected_version},
            {'$set': fields, '$inc': {'version': 1}}, return_document=ReturnDocument.AFTER)
        if row is None:
            raise APIError(409, 'version_conflict', '会话已被修改，请刷新后重试。')
        return public(row)

    def append_message(self, user, cid, *, run_id, role, text, product_snapshot, citations=()):
        self.get(user, cid)
        if role not in {'user', 'assistant'}:
            raise ValueError('消息角色无效')
        mid = stable_id('message', run_id, [role])
        payload = {'run_id': run_id, 'role': role, 'text': text, 'product_snapshot': copy.deepcopy(product_snapshot),
                   'citations': copy.deepcopy(list(citations)), 'conversation_id': cid, 'owner_id': user.user_id}
        identity = fingerprint(payload)
        saved = self.messages.find_one({'message_id': mid})
        if saved:
            if saved['identity'] != identity:
                raise APIError(409, 'message_conflict', '消息快照不能被覆盖。')
            return public(saved)
        counter = self.conversations.find_one_and_update(self.scope(user) | {'conversation_id': cid},
                    {'$inc': {'message_seq': 1}}, return_document=ReturnDocument.AFTER)
        if counter is None:
            raise APIError(404, 'not_found', '会话不在授权范围。')
        row = payload | {'message_id': mid, 'identity': identity, 'ordinal': counter['message_seq'],
                         'created_at': datetime.now(timezone.utc).isoformat()}
        try:
            self.messages.insert_one(row)
        except DuplicateKeyError:
            return self.append_message(user, cid, run_id=run_id, role=role, text=text,
                                       product_snapshot=product_snapshot, citations=citations)
        return public(row)

    def history(self, user, cid, *, after=0, limit=50):
        self.get(user, cid)
        rows = list(self.messages.find({'conversation_id': cid, 'owner_id': user.user_id, 'ordinal': {'$gt': after}})
                    .sort('ordinal', 1).limit(limit + 1))
        return {'items': [public(r) for r in rows[:limit]],
                'next_cursor': str(rows[limit-1]['ordinal']) if len(rows) > limit else None}
