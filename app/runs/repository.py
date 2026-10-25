"""独立Mongo的可核对领取协议；准备记录先于会话占用，重试补足消息。"""
import copy
from datetime import datetime, timezone
from uuid import uuid4
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.knowledge.models import stable_id
from app.knowledge.repository import fingerprint
from app.runs.models import TERMINAL
from app.identity.models import Principal


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
            row['input_product_snapshot'] = copy.deepcopy(row['product_snapshot'])
            row['requested_product_ids'] = list(data.product_ids)
            row['input_support_version'] = conv.get('support', {}).get('version', 0)
            from app.support.commands import freeze_support
            support = freeze_support(conv)
            if support is not None:
                row['support_snapshot'] = support
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
        # 新轮领取前先物化上一轮终态消息；失败保留原占用，可用同请求恢复。
        conversation = self.conversations.get(user, cid)
        # active_run_id 已是本run时，说明prepare后的领取CAS已成功，只是进程在
        # 写claimed/首条消息前退出。此时继续用不可变旧快照补齐协议；不能撤回用户事实，
        # 也不能让新上下文版本永久卡住已经持有的run。
        occupied_window = row['claim_state'] == 'preparing' and conversation.get('active_run_id') == rid
        if (row['claim_state'] == 'preparing' and not occupied_window and 'input_support_version' in row
                and row['input_support_version'] != conversation.get('support', {}).get('version', 0)):
            raise APIError(409, 'support_context_changed', '支持上下文已改变，请用新请求标识重建运行。')
        previous = conversation.get('active_run_id')
        if previous and previous != rid:
            prior = self.get(user, previous)
            self.release(prior)
        # 先准备再CAS占用，重试同run可进入；其他run永远不能释放本run占用。
        claim_query = self.conversations.scope(user) | {'conversation_id': cid, 'archived': False}
        claim_query['active_run_id'] = rid if occupied_window else {'$in': [None, rid]}
        if row['claim_state'] == 'preparing' and not occupied_window and 'input_support_version' in row:
            if row['input_support_version']:
                claim_query['support.version'] = row['input_support_version']
            else:
                claim_query['support.version'] = {'$in': [None, 0]}
        claimed = self.conversations.conversations.update_one(
            claim_query,
            {'$set': {'active_run_id': rid}})
        if not claimed.matched_count:
            current = self.get(user, rid)
            if current['state'] in TERMINAL:
                self.release(current)
                return current
            latest = self.conversations.get(user, cid)
            if latest.get('active_run_id') == rid:
                return self.reconcile(user, rid)
            if (row['claim_state'] == 'preparing' and 'input_support_version' in row
                    and row['input_support_version'] != latest.get('support', {}).get('version', 0)):
                raise APIError(409, 'support_context_changed', '支持上下文已改变，请用新请求标识重建运行。')
            self.runs.update_one({'run_id': rid, 'claim_state': 'preparing'},
                                 {'$set': {'claim_state': 'rejected', 'state': 'failed',
                                           'error': {'code': 'conversation_busy', 'stage': 'claim'}}})
            raise APIError(409, 'conversation_busy', '会话已有未结束的运行或已归档。')
        self.runs.update_one({'run_id': rid, 'claim_state': 'preparing'}, {'$set': {'claim_state': 'claimed'}})
        current = self.get(user, rid)
        if current['state'] in TERMINAL:
            self.release(current)
            return current
        self.conversations.append_message(user, cid, run_id=rid, role='user', text=row['question'],
                                          product_snapshot=row.get('input_product_snapshot', row['product_snapshot']))
        return self.get(user, rid)

    def release(self, row):
        # 重新读取事实，不能以调用者持有的旧快照跳过完成消息。
        row = self.runs.find_one({'run_id': row['run_id'], 'owner_id': row['owner_id'],
                                  'conversation_id': row['conversation_id'], 'kb_id': row['kb_id']})
        if row is None:
            return
        if row['state'] not in TERMINAL:
            return
        if row['state'] == 'completed' and row.get('completion_snapshot'):
            snap = row['completion_snapshot']
            user = Principal(user_id=row['owner_id'], username='运行消息恢复', role='viewer', kb_ids=(row['kb_id'],))
            self.conversations.append_message(user, row['conversation_id'], run_id=row['run_id'], role='assistant',
                text=snap.get('text', row.get('answer', '')),
                product_snapshot=snap.get('product_snapshot', row.get('product_snapshot', {})),
                citations=snap.get('citations', row.get('citations', [])))
        # 消息已持久才释放，迟到恢复只匹配自己的占用。
        self.conversations.conversations.update_one({'conversation_id': row['conversation_id'],
            'owner_id': row['owner_id'], 'active_run_id': row['run_id']}, {'$set': {'active_run_id': None}})
