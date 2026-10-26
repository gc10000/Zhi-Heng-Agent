"""从持久运行和事件生成最小安全统计；默认不保存或返回私有正文。"""
from datetime import datetime, timezone
from copy import deepcopy
import re
import math

SAFE_FAILURE_STAGES = {'authorization', 'product', 'retrieve', 'rerank', 'answer', 'persistence', 'unknown'}
SAFE_CODES = {'upstream_timeout', 'upstream_connection_failed', 'provider_rate_limited',
    'provider_unavailable', 'provider_authentication_failed', 'provider_invalid_response',
    'provider_unknown_error', 'query_execution_failed', 'authorization_revoked', 'conversation_archived',
    'context_changed', 'lease_expired', 'input_timeout', 'provider_capability_unsupported'}


class ProviderTelemetry:
    """只收集逻辑调用和公开usage字段；异常/缺字段使对应统计未知。"""
    def __init__(self):
        self._calls = {'invoke_started': 0, 'stream_started': 0}
        self._usage = {'input': 0, 'output': 0}
        self._usage_complete = {'input': True, 'output': True}
        self._models, self._lock = set(), __import__('threading').Lock()

    def started(self, kind, client):
        with self._lock:
            self._calls[kind] += 1
            model = getattr(client, 'model_name', None) or getattr(client, 'model', None)
            if _safe_model(model):
                self._models.add(model)

    def usage(self, metadata):
        usage = metadata if isinstance(metadata, dict) else {}
        aliases = {'input': ('input_tokens', 'prompt_tokens', 'input'), 'output': ('output_tokens', 'completion_tokens', 'output')}
        with self._lock:
            for name, keys in aliases.items():
                value = next((usage.get(key) for key in keys if usage.get(key) is not None), None)
                if type(value) is int and value >= 0:
                    self._usage[name] += value
                else:
                    self._usage_complete[name] = False

    def failed(self):
        with self._lock:
            self._usage_complete['input'] = self._usage_complete['output'] = False

    def snapshot(self):
        with self._lock:
            return {'logical_provider_calls': dict(self._calls),
                    'token_usage': {k: self._usage[k] if self._usage_complete[k] else None for k in ('input', 'output')},
                    'models': sorted(self._models) if self._models else None}


class ObservedClient:
    """适配LangChain兼容invoke/stream，不复制提示词、响应正文或端点。"""
    def __init__(self, client, recorder): self.client, self.recorder = client, recorder
    @property
    def model_name(self):
        underlying = getattr(self.client, 'client', self.client)
        return getattr(self.client, 'model_name', None) or getattr(underlying, 'model_name', None) or getattr(underlying, 'model', None)
    @property
    def extra_body(self):
        from app.infrastructure.providers.clients import PolicyChatClient
        underlying = self.client.client if isinstance(self.client, PolicyChatClient) else self.client
        return getattr(underlying, 'extra_body', None)
    def invoke(self, *args, **kwargs):
        self.recorder.started('invoke_started', self.client)
        try:
            response = self.client.invoke(*args, **kwargs)
            self.recorder.usage(getattr(response, 'usage_metadata', None) or (getattr(response, 'response_metadata', None) or {}).get('token_usage'))
            return response
        except Exception:
            self.recorder.failed(); raise
    def stream(self, *args, **kwargs):
        self.recorder.started('stream_started', self.client)
        try:
            seen, metadata = False, None
            for chunk in self.client.stream(*args, **kwargs):
                seen = True
                usage = getattr(chunk, 'usage_metadata', None) or (getattr(chunk, 'response_metadata', None) or {}).get('token_usage')
                # OpenAI兼容流的usage通常只在最后一块给出全请求总量。
                if usage is not None:
                    metadata = usage
                yield chunk
            if not seen: self.recorder.failed()
            else: self.recorder.usage(metadata)
        except Exception:
            self.recorder.failed(); raise


def advance(row, kind, payload, now):
    """与事件同一次CAS写入安全聚合，事件TTL不导致耗时历史丢失。"""
    result = deepcopy(row.get('telemetry') or {})
    result['schema_version'] = 1
    result.setdefault('stage_seconds', {})
    result.setdefault('first_event_at', now.isoformat())
    stage = payload.get('stage') if isinstance(payload, dict) else None
    is_terminal = kind in {'run.completed', 'run.failed', 'run.cancelled', 'run.interrupted'}
    if (kind == 'stage.changed' and stage in SAFE_FAILURE_STAGES) or is_terminal:
        prior = result.get('active_stage')
        started = _time(result.get('stage_started_at'))
        if prior in SAFE_FAILURE_STAGES and started:
            result['stage_seconds'][prior] = round(result['stage_seconds'].get(prior, 0) + max(0, (now-started).total_seconds()), 6)
        result['active_stage'] = None if is_terminal else stage
        result['stage_started_at'] = None if is_terminal else now.isoformat()
    if is_terminal:
        result['terminal_at'] = now.isoformat()
    return result


def _safe_model(value):
    if isinstance(value, str) and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._/-]{0,100}', value) and not any(
            word in value.lower() for word in ('secret', 'token', 'password', 'api_key', 'sk-')):
        return value
    return None


def safe_counts(value, keys):
    value = value if isinstance(value, dict) else {}
    return {k: value[k] if type(value.get(k)) is int and value[k] >= 0 else None for k in keys}


def safe_seconds(value):
    return {stage: seconds for stage, seconds in (value or {}).items() if stage in SAFE_FAILURE_STAGES and
            type(seconds) in (int, float) and math.isfinite(seconds) and seconds >= 0}


def _time(value):
    if not value:
        return None
    try:
        parsed = value if isinstance(value, datetime) else datetime.fromisoformat(value.replace('Z', '+00:00'))
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError, AttributeError):
        return None


def _events(repo, rid):
    return list(repo.db.run_events.find({'run_id': rid}, {'type': 1, 'at': 1, 'payload': 1, 'seq': 1}).sort('seq', 1))


def run_telemetry(repo, user, rid):
    row = repo.get(user, rid)
    events = _events(repo, rid)
    began = _time(row.get('created_at'))
    ended = None
    stages, current_stage, stage_started = {}, None, began
    failure = row.get('error') or {}
    for event in events:
        at = _time(event.get('at'))
        kind, payload = event.get('type', ''), event.get('payload') or {}
        if kind == 'run.started' and began is None:
            began = at
        stage = payload.get('stage') if isinstance(payload, dict) else None
        if kind == 'stage.changed' and stage in SAFE_FAILURE_STAGES:
            if current_stage and stage_started and at:
                stages[current_stage] = round(stages.get(current_stage, 0)+max(0.0, (at - stage_started).total_seconds()), 3)
            current_stage, stage_started = stage, at
        if kind.startswith('run.') and kind.removeprefix('run.') in {'completed', 'failed', 'cancelled', 'interrupted'}:
            ended = at
            if current_stage and stage_started and at:
                stages[current_stage] = round(stages.get(current_stage, 0)+max(0.0, (at - stage_started).total_seconds()), 3)
    persisted = row.get('telemetry') or {}
    if persisted.get('schema_version') == 1:
        ended = _time(persisted.get('terminal_at'))
        stages = safe_seconds(persisted.get('stage_seconds'))
    total = round(max(0.0, (ended - began).total_seconds()), 3) if ended and began else None
    code = failure.get('code') if isinstance(failure, dict) else None
    stage = failure.get('stage') if isinstance(failure, dict) else None
    models = [_safe_model(m) for m in persisted.get('models', []) or [] if _safe_model(m)]
    return {
        'run_id': rid, 'conversation_id': row.get('conversation_id'), 'state': row.get('state'),
        'created_at': row.get('created_at'), 'ended_at': ended.isoformat() if ended else None,
        'total_seconds': total, 'stage_seconds': stages, 'failure_stage': stage if stage in SAFE_FAILURE_STAGES else ('unknown' if code else None),
        'failure_code': code if code in SAFE_CODES else 'unknown' if code else None,
        'model': ','.join(models) if models else _safe_model(row.get('model_name')),
        'token_usage': safe_counts(persisted.get('token_usage'), ('input', 'output')),
        'logical_provider_calls': safe_counts(persisted['logical_provider_calls'], ('invoke_started', 'stream_started')) if persisted.get('logical_provider_calls') is not None else None,
        'revision_count': len(row['revision_snapshot']) if isinstance(row.get('revision_snapshot'), list) else None,
        'strategy': {'fusion': (row.get('retrieval_policy') or {}).get('fusion') if (row.get('retrieval_policy') or {}).get('fusion') in {'rrf','weighted'} else None},
        'degradation': [{'branch': b['name'], 'status': b['status']} for b in row.get('retrieval_branches', [])
                        if b.get('name') in {'hyde','decomposition'} and b.get('status') in {'timeout','busy','failed'}],
        'coverage': 'single_run', 'timing_coverage': 'persistent' if persisted else 'retained_events_only',
    }


def page(repo, user, kb_id, *, cursor=None, limit=50):
    query = {'owner_id': user.user_id, 'kb_id': kb_id}
    if cursor:
        query['run_id'] = {'$gt': cursor}
    rows = list(repo.runs.find(query, {'run_id': 1}).sort('run_id', 1).limit(limit + 1))
    items = [run_telemetry(repo, user, row['run_id']) for row in rows[:limit]]
    return {'items': items, 'next_cursor': rows[limit - 1]['run_id'] if len(rows) > limit else None,
            'coverage': 'page_only'}
