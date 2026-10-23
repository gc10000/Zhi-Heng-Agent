"""独立Mongo的可核对领取协议；准备记录先于会话占用，重试补足消息。"""
import copy
from datetime import datetime, timezone
from uuid import uuid4
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.knowledge.models import stable_id
from app.knowledge.repository import fingerprint
from app.runs.models import TERMINAL


class RunRepository:
    def __init__(self, db, conversations):
        self.db, self.conversations, self.runs = db, conversations, db.runs
        self.runs.create_index('run_id', unique=True)
        self.runs.create_index([('owner_id', 1), ('conversation_id', 1), ('client_request_id', 1)], unique=True)
        self.runs.create_index([('claim_state', 1), ('state', 1)])

    def get(self, user, rid):
        row = self.runs.find_one({'run_id': rid, 'owner_id': user.user_id, 'kb_id': {'$in': list(user.kb_ids)}})
        if row is None:
            raise APIError(404, 'not_found', '运行不存在或不在授权范围。')
        self.conversations.get(user, row['conversation_id'])
        return row

    def prepare(self, user, cid, data):
        conv = self.conversations.get(user, cid)
        if data.kb_id != conv['kb_id'] or conv['archived']:
            raise APIError(409, 'conversation_unavailable', '会话知识范围不匹配或已归档。')
        key = {'owner_id': user.user_id, 'conversation_id': cid, 'client_request_id': data.client_request_id}
        identity = fingerprint(data.model_dump())
        saved = self.runs.find_one(key)
        if saved is None:
            rid = str(uuid4())
            row = key | {'run_id': rid, 'kb_id': data.kb_id, 'question': data.question,
                         'message_id': stable_id('message', rid, ['user']),
                         'assistant_message_id': stable_id('message', rid, ['assistant']),
                         'product_snapshot': {'product_ids': list(data.product_ids or conv['product_ids']), 'version': conv['version']},
                         'identity': identity, 'state': 'pending', 'claim_state': 'preparing', 'version': 0,
                         'seq': 0, 'outbox': [], 'answer': '', 'citations': [],
                         'created_at': datetime.now(timezone.utc).isoformat()}
            try:
                self.runs.insert_one(copy.deepcopy(row))
            except DuplicateKeyError:
                pass
            saved = self.runs.find_one(key)
        if saved['identity'] != identity:
            raise APIError(409, 'idempotency_conflict', '相同请求标识的内容不同。')
        return saved

    def reconcile(self, user, rid):
        row = self.get(user, rid)
        if row['claim_state'] == 'rejected':
            raise APIError(409, 'conversation_busy', '会话已有未结束的运行。')
        if row['state'] in TERMINAL:
            self.release(row)
            return row
        cid = row['conversation_id']
        # 先准备再CAS占用，重试同run可进入；其他run永远不能释放本run占用。
        claimed = self.conversations.conversations.update_one(
            self.conversations.scope(user) | {'conversation_id': cid, 'archived': False,
                                              'active_run_id': {'$in': [None, rid]}},
            {'$set': {'active_run_id': rid}})
        if not claimed.matched_count:
            self.runs.update_one({'run_id': rid, 'claim_state': 'preparing'},
                                 {'$set': {'claim_state': 'rejected', 'state': 'failed',
                                           'error': {'code': 'conversation_busy', 'stage': 'claim'}}})
            raise APIError(409, 'conversation_busy', '会话已有未结束的运行或已归档。')
        self.runs.update_one({'run_id': rid, 'claim_state': 'preparing'}, {'$set': {'claim_state': 'claimed'}})
        self.conversations.append_message(user, cid, run_id=rid, role='user', text=row['question'],
                                          product_snapshot=row['product_snapshot'])
        return self.get(user, rid)

    def release(self, row):
        if row['state'] not in TERMINAL:
            return
        self.conversations.conversations.update_one({'conversation_id': row['conversation_id'],
            'owner_id': row['owner_id'], 'active_run_id': row['run_id']}, {'$set': {'active_run_id': None}})
