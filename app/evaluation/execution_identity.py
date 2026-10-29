"""执行输入及结果的稳定投影：排除租约/计量，保留实际对象、澄清与完整引用。"""
from copy import deepcopy
from pymongo.errors import DuplicateKeyError
from .validate_dataset import fingerprint


def run_input(row, db):
    value = {k: deepcopy(row[k]) for k in (
        'run_id', 'conversation_id', 'owner_id', 'kb_id', 'identity', 'client_request_id',
        'question', 'requested_product_ids', 'input_product_snapshot', 'input_support_version',
        'support_snapshot', 'source_prerequisites', 'source_prerequisites_sha256') if k in row}
    # 与QueryRunner实际历史读取口径一致；操作时间/消息ID不属于生成输入。
    history = list(db.messages.find({'conversation_id':row['conversation_id'],
        'owner_id':row['owner_id'],'run_id':{'$ne':row['run_id']}}).sort('ordinal',-1).limit(30))
    value['history'] = [{'role':r['role'],'text':r['text']} for r in reversed(history)]
    return value


def run_output(row):
    return {k: deepcopy(row[k]) for k in (
        'state', 'answer', 'citations', 'candidates', 'resume_point', 'product_snapshot',
        'revision_snapshot', 'answer_support', 'output_truncated', 'retrieval_branches',
        'evaluation_candidates', 'prompt_budget', 'completion_snapshot') if k in row}


def result_subject(result):
    # 计量与耗时来自本次进程/持久Run，可以变化；其余实际执行结果全部参与比较。
    telemetry = {'logical_provider_calls', 'logical_provider_calls_scope', 'execution_logical_provider_calls',
                 'stage_timings', 'token_usage'}
    return {k: deepcopy(v) for k, v in result.items() if k not in telemetry}


def outcome_identity(db, config, checkpoint_key, run, result):
    return dict(checkpoint_key=checkpoint_key, run_id=run['run_id'], config_sha256=fingerprint(config),
        regression_source=config['regression_source'], run_input_sha256=fingerprint(run_input(run,db)),
        run_output_sha256=fingerprint(run_output(run)), result_sha256=fingerprint(result_subject(result)))


def freeze_outcome(db, config, checkpoint_key, run, result):
    identity = outcome_identity(db,config,checkpoint_key,run,result)
    key = fingerprint([checkpoint_key, run['run_id']])
    try:
        db.evaluation_outcomes.update_one({'_id': key}, {'$setOnInsert': identity}, upsert=True)
    except DuplicateKeyError:
        pass
    saved = db.evaluation_outcomes.find_one({'_id': key})
    if any(saved.get(k) != v for k, v in identity.items()):
        raise ValueError('已冻结执行输入或完整结果变化，拒绝观察复用')
    return identity
