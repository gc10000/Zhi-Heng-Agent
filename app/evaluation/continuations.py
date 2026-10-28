"""调用之前持久化后续请求身份；旧失败和未知费用不覆盖、不补零。"""
from copy import deepcopy
from datetime import datetime, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from .validate_dataset import fingerprint


def prepare_continuation(db, context, *, checkpoint_key, input_sha256, previous, request_key, question_id, config, control_db):
    rows = db.evaluation_continuations
    key = fingerprint([context['experiment_id'], checkpoint_key])
    identity = dict(experiment_id=context['experiment_id'], source=deepcopy(context['source']),
                    checkpoint_key=checkpoint_key, input_sha256=input_sha256)
    saved = rows.find_one({'_id': key})
    if saved is None and previous['state'] != 'interrupted':
        return None
    from .execution_links import require_source_link
    link = require_source_link(db, control_db, context, checkpoint_key=checkpoint_key, input_sha256=input_sha256,
        run_id=saved['source_run_id'] if saved else previous['run_id'], question_id=question_id, config=config)
    link_sha256 = fingerprint({k: v for k, v in link.items() if k != '_id'})
    identity.update(source_link_id=link['_id'], source_link_sha256=link_sha256)
    if saved is None:
        row = identity | dict(source_run_id=previous['run_id'],
            source_conversation_id=previous['conversation_id'],
            source_run_sha256=fingerprint({k: previous.get(k) for k in (
                'run_id', 'conversation_id', 'state', 'version', 'seq', 'identity', 'client_request_id')}),
            request_key=fingerprint([key, 'interrupted_followup', previous['run_id']]),
            run_id=None, state='prepared', logical_provider_calls=None, token_usage=None,
            exact_sdk_http_requests=None, exact_cost=None,
            created_at=datetime.now(timezone.utc).isoformat())
        try:
            saved = rows.find_one_and_update({'_id': key}, {'$setOnInsert': row},
                                            upsert=True, return_document=ReturnDocument.AFTER)
        except DuplicateKeyError:
            saved = rows.find_one({'_id': key})
    if any(saved.get(k) != v for k, v in identity.items()):
        raise ValueError('后续请求来源或冻结输入已改变')
    if (previous['run_id'] not in {saved['source_run_id'], saved.get('run_id')} and
            request_key != saved['request_key']):
        raise ValueError('检查点已属于其他运行，拒绝覆盖后续请求')
    return saved


def observe_continuation(db, saved, run):
    telemetry = run.get('telemetry') or {}
    result = db.evaluation_continuations.update_one({'_id': saved['_id'],
        'run_id': {'$in': [None, run['run_id']]}}, {'$set': dict(run_id=run['run_id'],
        state=run['state'], logical_provider_calls=deepcopy(telemetry.get('logical_provider_calls')),
        token_usage=deepcopy(telemetry.get('token_usage')),
        updated_at=datetime.now(timezone.utc).isoformat())})
    if not result.matched_count:
        raise ValueError('后续账本运行绑定冲突，拒绝执行其他请求')
