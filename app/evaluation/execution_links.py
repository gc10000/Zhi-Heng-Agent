"""正式任务的题级执行/观察复用关联；模型前持久化，不追认历史归属。"""
from datetime import datetime, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from .validate_dataset import fingerprint


def bind_execution(db, context, config, question_id, checkpoint_key, input_sha256, run):
    target = config['target']
    parent = db.evaluation_experiments.find_one(dict(experiment_id=context['experiment_id'],
        attempt=context['attempt'], worker_token=context['worker_token'],
        config_sha256=context['config_sha256'], owner_id=target['owner_id'], kb_id=target['kb_id'],
        state={'$in': ['running', 'cancel_requested']}, lease_until={'$gt': datetime.now(timezone.utc)}))
    if parent is None:
        raise ValueError('当前实验执行身份或租约无效，拒绝建立题级来源')
    identity = dict(experiment_id=context['experiment_id'], attempt=context['attempt'],
        question_id=question_id, checkpoint_key=checkpoint_key, input_sha256=input_sha256,
        config_sha256=fingerprint(config), registered_config_sha256=parent['config_sha256'],
        owner_id=target['owner_id'], kb_id=target['kb_id'], run_id=run['run_id'],
        conversation_id=run['conversation_id'])
    key = fingerprint([context['experiment_id'], context['attempt'], question_id])
    row = identity | dict(mode='execution' if run['state'] == 'pending' else 'observed_reuse',
                          created_at=datetime.now(timezone.utc).isoformat())
    try:
        saved = db.evaluation_execution_links.find_one_and_update({'_id': key}, {'$setOnInsert': row},
                                                                 upsert=True, return_document=ReturnDocument.AFTER)
    except DuplicateKeyError:
        saved = db.evaluation_execution_links.find_one({'_id': key})
    if any(saved.get(k) != v for k, v in identity.items()):
        raise ValueError('当前实验题级来源已绑定其他输入或Run')
    return saved


def require_source_link(db, context, *, checkpoint_key, input_sha256, run_id, question_id, config):
    source = context['source']
    target = config['target']
    parent = db.evaluation_experiments.find_one(dict(experiment_id=source['source_experiment_id'],
        attempt=source['source_attempt'], version=source['source_version'],
        owner_id=target['owner_id'], kb_id=target['kb_id'], state={'$in': ['failed', 'cancelled', 'incomplete']}))
    key = fingerprint([source['source_experiment_id'], source['source_attempt'], question_id])
    link = db.evaluation_execution_links.find_one({'_id': key})
    expected = dict(experiment_id=source['source_experiment_id'], attempt=source['source_attempt'],
        question_id=question_id, checkpoint_key=checkpoint_key, input_sha256=input_sha256,
        run_id=run_id, config_sha256=fingerprint(config), owner_id=target['owner_id'], kb_id=target['kb_id'])
    if (parent is None or link is None or any(link.get(k) != v for k, v in expected.items()) or
            link.get('registered_config_sha256') != parent['config_sha256'] or
            source.get('source_config_sha256') != parent['config_sha256']):
        raise ValueError('父实验题级来源未核实或不匹配；历史缺少关联须另行留证审核，不能自动回填')
    return link
