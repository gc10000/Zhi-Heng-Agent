"""持久命令、执行租约和超时核对，不把等待人工输入当执行卡死。"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field
from app.api.errors import APIError
from app.identity.models import Principal
from app.conversations.context import confirm_snapshot
from app.runs.events import aware, utcnow
from app.runs.models import TERMINAL, snapshot
from app.runs.state_machine import check


class VersionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0)


class ConfirmInput(VersionInput):
    product_ids: list[str] = Field(min_length=1, max_length=50)


class RunCommands:
    def __init__(self, repo, events, *, lease_seconds=60, input_wait_seconds=86400, pending_seconds=300, clock=utcnow):
        self.repo, self.events, self.clock = repo, events, clock
        # 仓储的归档领取路径也必须使用同一个事件账本，避免worker启动与扫描分叉。
        self.repo._event_ledger = events
        self.lease_seconds, self.input_wait_seconds, self.pending_seconds = lease_seconds, input_wait_seconds, pending_seconds

    def start(self, user, rid):
        row = self.repo.reconcile(user, rid)
        check(row['state'], 'running')
        token = uuid4().hex
        self.events.emit(user, rid, 'run.started', {'conversation_id': row['conversation_id'], 'message_id': row['message_id']},
            state='running', expected_version=row['version'], expected_states={'pending'},
            fields={'execution_token': token, 'execution_lease': self.clock() + timedelta(seconds=self.lease_seconds)})
        return token

    def boundary(self, user, rid, token):
        row = self.repo.get(user, rid)
        if row.get('execution_token') != token or not row.get('execution_lease') or aware(row['execution_lease']) <= self.clock():
            raise APIError(409, 'lease_lost', '执行租约已失效。')
        if row['state'] == 'cancel_requested':
            self.finish(user, rid, token, 'cancelled', {'reason': 'user_requested'})
            return False
        if row['state'] != 'running':
            raise APIError(409, 'state_conflict', '运行不在执行状态。')
        result = self.repo.runs.update_one({'run_id': rid, 'execution_token': token, 'state': 'running',
                                            'execution_lease': {'$gt': self.clock()}},
            {'$set': {'execution_lease': self.clock() + timedelta(seconds=self.lease_seconds)}, '$inc': {'version': 1}})
        if not result.matched_count:
            return self.boundary(user, rid, token)
        return True

    def wait_input(self, user, rid, token, *, candidates, resume_point, telemetry_measurements=None):
        if not self.boundary(user, rid, token):
            return snapshot(self.repo.get(user, rid))
        row = self.repo.get(user, rid)
        check(row['state'], 'awaiting_input')
        if not candidates or any(not c.get('product_id') for c in candidates):
            raise ValueError('等待输入必须有明确候选标识')
        self.events.emit(user, rid, 'product.candidates', {'candidates': candidates, 'expected_version': row['version'] + 1},
            state='awaiting_input', expected_version=row['version'], expected_states={'running'}, expected_token=token,
            fields={'candidates': candidates, 'resume_point': resume_point, 'execution_token': None, 'execution_lease': None,
                    'input_expires_at': self.clock() + timedelta(seconds=self.input_wait_seconds)} |
                   ({'telemetry_measurements': telemetry_measurements} if telemetry_measurements is not None else {}))
        return snapshot(self.repo.get(user, rid))

    def confirm(self, user, rid, data):
        row = self.repo.get(user, rid)
        check(row['state'], 'pending')
        if row.get('input_expires_at') and aware(row['input_expires_at']) <= self.clock():
            raise APIError(409, 'input_expired', '本次确认已过期，请新建运行。')
        selected = confirm_snapshot(row, data.product_ids)
        self.events.emit(user, rid, 'product.confirmed', selected, state='pending', expected_version=data.expected_version,
            expected_states={'awaiting_input'}, fields={'product_snapshot': selected, 'candidates': [],
                'execution_token': None, 'execution_lease': None, 'resumed_at': self.clock()})
        return snapshot(self.repo.get(user, rid))

    def cancel(self, user, rid, data):
        row = self.repo.get(user, rid)
        if row.get('cancel_request_version') == data.expected_version and row['state'] in {'cancel_requested', 'cancelled'}:
            return snapshot(row)
        check(row['state'], 'cancel_requested')
        self.events.emit(user, rid, 'stage.changed', {'state': 'cancel_requested'}, state='cancel_requested',
                         expected_version=data.expected_version, expected_states={'pending', 'running', 'awaiting_input'},
                         fields={'cancel_request_version': data.expected_version})
        return snapshot(self.repo.get(user, rid))

    def finish(self, user, rid, token, state, payload, *, fields=None):
        row = self.repo.get(user, rid)
        check(row['state'], state)
        self.events.emit(user, rid, 'run.' + state, payload, state=state, fields=fields,
                         expected_token=token, expected_states={row['state']})
        return snapshot(self.repo.get(user, rid))

    def recover(self):
        """可反复执行的补偿扫描；只操作本运行账本，不执行图或外部模型。"""
        recovered = []
        for row in self.repo.runs.find({'state': {'$in': ['pending', 'running', 'awaiting_input', 'cancel_requested']}}):
            if not self._recoverable_scope(row):
                continue
            user = Principal(user_id=row['owner_id'], username='运行恢复', role='viewer', kb_ids=(row['kb_id'],))
            conversation = self.repo.conversations.conversations.find_one(
                {'conversation_id': row['conversation_id'], 'owner_id': row['owner_id'], 'kb_id': row['kb_id']},
                {'archived': 1})
            if conversation and conversation.get('archived'):
                try:
                    self.events.emit(user, row['run_id'], 'run.interrupted',
                        {'reason': 'conversation_archived'}, state='interrupted',
                        fields={'claim_state': 'rejected',
                                'error': {'code': 'conversation_archived', 'stage': 'recovery'}},
                        expected_version=row['version'], expected_states={row['state']})
                    recovered.append(row['run_id'])
                except APIError as exc:
                    if exc.status != 409:
                        raise
                continue
            if row['state'] == 'pending':
                try:
                    row = self.repo.reconcile(user, row['run_id'])
                except APIError as exc:
                    # 未领取run的支持版本门禁仍应拒绝；但不能因此跳过其pending租约。
                    # 运行已占用的中断窗口由reconcile补偿，过期未占用的准备记录在此终止。
                    if exc.status == 409 and exc.code == 'support_context_changed':
                        row = self.repo.runs.find_one({'run_id': row['run_id']}) or row
                    elif exc.status == 409:
                        continue
                    else:
                        raise
            now, state = self.clock(), row['state']
            lease = row.get('execution_lease')
            timed_out = ((state == 'running' and (not lease or aware(lease) <= now)) or
                         (state == 'awaiting_input' and row.get('input_expires_at') and aware(row['input_expires_at']) <= now) or
                         (state == 'pending' and now - aware(row.get('resumed_at') or datetime.fromisoformat(row['created_at'])) >= timedelta(seconds=self.pending_seconds)))
            cancel_idle = state == 'cancel_requested' and (not lease or aware(lease) <= now)
            if timed_out or cancel_idle:
                # 有执行租约但未确认取消的worker失联，不能伪称已合作停止。
                target = 'cancelled' if cancel_idle and not lease else 'interrupted'
                try:
                    fields = None
                    if state == 'pending' and row.get('claim_state') == 'preparing' and row.get('error', {}).get('code') != 'support_context_changed':
                        latest = self.repo.conversations.conversations.find_one({'conversation_id': row['conversation_id'],
                            'owner_id': row['owner_id']}, {'active_run_id': 1})
                        # 仅过期且仍未占用的旧快照因版本冲突终止；不能释放其他run的占用。
                        if latest and latest.get('active_run_id') != row['run_id']:
                            fields = {'claim_state': 'rejected', 'error': {'code': 'support_context_changed', 'stage': 'recovery'}}
                    self.events.emit(user, row['run_id'], 'run.' + target, {'reason': 'input_timeout' if state == 'awaiting_input' else 'lease_expired'},
                        state=target, fields=fields, expected_version=row['version'], expected_states={state})
                    recovered.append(row['run_id'])
                except APIError as exc:
                    if exc.status != 409:
                        raise
        # 终态保存后释放失败的占用，以及已保存但未投递的outbox均可补偿。
        for row in self.repo.runs.find({'state': {'$in': list(TERMINAL)}}):
            if not self._recoverable_scope(row):
                continue
            self.repo.release(row)
            self.events.flush(row['run_id'])
        return recovered

    def _recoverable_scope(self, row):
        conversation = self.repo.conversations.conversations.find_one({
            'conversation_id': row['conversation_id'], 'owner_id': row['owner_id'], 'kb_id': row['kb_id']})
        if conversation is not None:
            return True
        # 异常归属需人工核对，不接管、不删除，也不阻断其他账本条目。
        self.repo.runs.update_one({'run_id': row['run_id'], 'version': row['version']},
            {'$set': {'recovery_issue': {'code': 'conversation_scope_mismatch'}}})
        return False
