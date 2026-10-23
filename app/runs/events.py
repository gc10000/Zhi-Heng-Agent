"""run文档内原子outbox后幂等投递，事件持久后才供SSE读取。"""
import copy
import json
import time
from datetime import datetime, timedelta, timezone
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.runs.models import TERMINAL


def utcnow():
    return datetime.now(timezone.utc)


def aware(value):
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value


class EventLedger:
    def __init__(self, repo, *, clock=utcnow):
        self.repo, self.events, self.clock = repo, repo.db.run_events, clock
        self.events.create_index([('run_id', 1), ('seq', 1)], unique=True)
        self.events.create_index('expires_at', expireAfterSeconds=0)

    def emit(self, user, rid, kind, payload, *, state=None, fields=None, expected_version=None, expected_states=None, expected_token=None):
        terminal = kind.removeprefix('run.') if kind.startswith('run.') else None
        if (terminal in TERMINAL or state in TERMINAL) and state != terminal:
            raise ValueError('终态事件必须与持久状态一致')
        for _ in range(25):
            row = self.repo.get(user, rid)
            if row['state'] in TERMINAL:
                raise APIError(409, 'run_finished', '运行已结束，不能再次写入事件。')
            if expected_version is not None and row['version'] != expected_version:
                raise APIError(409, 'version_conflict', '运行版本已改变，请刷新。')
            if expected_states is not None and row['state'] not in expected_states:
                raise APIError(409, 'state_conflict', '当前运行状态不接受此操作。')
            if row['state'] == 'cancel_requested' and state == 'completed':
                raise APIError(409, 'cancel_requested', '运行已请求取消，不能完成为成功。')
            now = self.clock()
            if expected_token is not None and (row.get('execution_token') != expected_token or
                    not row.get('execution_lease') or aware(row['execution_lease']) <= now):
                raise APIError(409, 'lease_lost', '执行租约已失效。')
            deadline = now + timedelta(hours=24)
            event = {'run_id': rid, 'seq': row['seq'] + 1, 'type': kind, 'at': now.isoformat(),
                     'payload': copy.deepcopy(payload), 'expires_at': deadline}
            updates = copy.deepcopy(fields or {})
            updates['replay_expires_at'] = deadline
            updates['first_event_seq'] = row.get('first_event_seq', event['seq'])
            if state:
                updates['state'] = state
            if kind == 'answer.delta':
                updates['answer'] = row['answer'] + payload['text']
            query = {'run_id': rid, 'version': row['version'], 'state': row['state']}
            if expected_token is not None:
                query.update({'execution_token': expected_token, 'execution_lease': {'$gt': now}})
            result = self.repo.runs.update_one(query,
                {'$set': updates, '$inc': {'version': 1, 'seq': 1}, '$push': {'outbox': event}})
            if result.matched_count:
                if state in TERMINAL:
                    self.repo.release(self.repo.get(user, rid))
                self.flush(rid)
                return {k: v for k, v in event.items() if k != 'expires_at'}
        raise APIError(409, 'version_conflict', '运行正在被修改，请重试。')

    def flush(self, rid):
        """允许状态保存后进程退出；新实例重复投递同seq不会重复事件。"""
        row = self.repo.runs.find_one({'run_id': rid})
        if row is None:
            return
        self.repo.release(row)
        for event in sorted(row['outbox'], key=lambda e: e['seq']):
            key = {'run_id': rid, 'seq': event['seq']}
            try:
                self.events.update_one(key, {'$setOnInsert': event}, upsert=True)
            except DuplicateKeyError:
                saved = self.events.find_one(key)
                if saved is None or saved['type'] != event['type'] or saved['payload'] != event['payload']:
                    raise RuntimeError('事件幂等载荷冲突')
            self.repo.runs.update_one({'run_id': rid}, {'$pull': {'outbox': {'seq': event['seq']}}})

    def read(self, user, rid, after=0, *, limit=200):
        row = self.repo.get(user, rid)
        if after < 0 or after > row['seq']:
            raise APIError(422, 'invalid_cursor', '事件游标超出运行范围。')
        self.flush(rid)
        now = self.clock()
        if row['seq']:
            # 不猜测相邻序号连续性；精确确认游标事件仍在有效窗口。
            anchor = after if after else row.get('first_event_seq', 1)
            cursor = self.events.find_one({'run_id': rid, 'seq': anchor})
            if cursor is None or aware(cursor['expires_at']) <= now:
                raise APIError(410, 'events_expired', '事件重放窗口已过期，请读取运行快照。', {'run_id': rid})
        rows = list(self.events.find({'run_id': rid, 'seq': {'$gt': after}, 'expires_at': {'$gt': now}})
                    .sort('seq', 1).limit(limit))
        return [{k: v for k, v in r.items() if k not in {'_id', 'expires_at'}} for r in rows]


def frame(event):
    return f"id: {event['seq']}\nevent: {event['type']}\ndata: {json.dumps(event, ensure_ascii=False, separators=(',', ':'))}\n\n"


class DeltaBuffer:
    """75ms或8Ki字符合并增量，显式flush用于阶段/终态前。"""
    def __init__(self, send, *, clock=time.monotonic):
        self.send, self.clock, self.text, self.started = send, clock, '', clock()

    def add(self, text):
        self.text += text
        if self.clock() - self.started >= .075 or len(self.text) >= 8192:
            self.flush()

    def flush(self):
        if self.text:
            self.send('answer.delta', {'text': self.text})
            self.text = ''
        self.started = self.clock()
