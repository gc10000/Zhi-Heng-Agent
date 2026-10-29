"""正式任务的题级执行/观察复用关联；模型前持久化，不追认历史归属。"""
from datetime import datetime, timezone

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from .validate_dataset import fingerprint


def validate_execution(control_db, context, config):
    """控制账本来自正式job，不能从冻结Run目标推断或复制实验授权。"""
    if control_db is None:
        raise ValueError('缺少正式实验控制账本，拒绝建立题级来源')
    target = config['target']
    parent = control_db.evaluation_experiments.find_one(dict(experiment_id=context['experiment_id'],
        attempt=context['attempt'], worker_token=context['worker_token'],
        config_sha256=context['config_sha256'], owner_id=target['owner_id'], kb_id=target['kb_id'],
        state={'$in': ['running', 'cancel_requested']}, lease_until={'$gt': datetime.now(timezone.utc)}))
    if parent is None:
        raise ValueError('当前实验执行身份或租约无效，拒绝建立题级来源')
    if (parent.get('regression_source') != config.get('regression_source') or
            parent.get('regression_execution_key') != config.get('regression_execution_key')):
        raise ValueError('正式实验的反馈来源或执行身份不匹配')
    if config.get('regression_source'):
        from .feedback_regression import RegressionService
        from types import SimpleNamespace
        from .repository import EvaluationRepository
        # job已核验文件；Run写入前再次校验不可变绑定及当前反馈/原件，覆盖跨库写入窗口。
        ledger = RegressionService(EvaluationRepository(control_db),None)
        binding = ledger.scoped(SimpleNamespace(user_id=target['owner_id'],kb_ids=(target['kb_id'],)),
            control_db.regression_bindings,config['regression_source']['id'])
        source,_ = ledger.source(SimpleNamespace(kb_ids=(target['kb_id'],)),binding['source']['feedback_id'])
        if binding['sha256'] != config['regression_source']['sha256'] or binding['source'] != source:
            raise ValueError('反馈来源已经变化')
        if binding.get('annotation_id'):
            audit=ledger.scoped(SimpleNamespace(user_id=target['owner_id'],kb_ids=(target['kb_id'],)),
                control_db.regression_annotations,binding['annotation_id'])
            ledger.check_evidence(SimpleNamespace(kb_ids=(target['kb_id'],)),audit)
            if audit['sha256'] != binding['annotation_record_sha256']:
                raise ValueError('反馈独立审核关联变化')
    return parent


def bind_execution(db, control_db, context, config, question_id, checkpoint_key, input_sha256, run):
    # 跨库没有事务；创建Run后再次核验租约，失效时不继续模型调用，pending由正式恢复收敛。
    parent = validate_execution(control_db, context, config)
    target = config['target']
    if db.name != target['database']:
        raise ValueError('题级来源目标库与冻结Run目标不匹配')
    identity = dict(experiment_id=context['experiment_id'], attempt=context['attempt'],
        control_database=control_db.name, target_database=db.name,
        question_id=question_id, checkpoint_key=checkpoint_key, input_sha256=input_sha256,
        config_sha256=fingerprint(config), registered_config_sha256=parent['config_sha256'],
        owner_id=target['owner_id'], kb_id=target['kb_id'], run_id=run['run_id'],
        conversation_id=run['conversation_id'])
    if config.get('regression_source'):
        identity['regression_source'] = config['regression_source']
        from .execution_identity import run_input
        identity['run_input_sha256'] = fingerprint(run_input(run,db))
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


def require_source_link(db, control_db, context, *, checkpoint_key, input_sha256, run_id, question_id, config):
    if control_db is None:
        raise ValueError('缺少正式父实验控制账本，拒绝核验题级来源')
    source = context['source']
    target = config['target']
    parent = control_db.evaluation_experiments.find_one(dict(experiment_id=source['source_experiment_id'],
        attempt=source['source_attempt'], version=source['source_version'],
        owner_id=target['owner_id'], kb_id=target['kb_id'], state={'$in': ['failed', 'cancelled', 'incomplete']}))
    key = fingerprint([source['source_experiment_id'], source['source_attempt'], question_id])
    link = db.evaluation_execution_links.find_one({'_id': key})
    expected = dict(experiment_id=source['source_experiment_id'], attempt=source['source_attempt'],
        control_database=control_db.name, target_database=target['database'],
        question_id=question_id, checkpoint_key=checkpoint_key, input_sha256=input_sha256,
        run_id=run_id, config_sha256=fingerprint(config), owner_id=target['owner_id'], kb_id=target['kb_id'])
    if (db.name != target['database'] or parent is None or link is None or
            any(link.get(k) != v for k, v in expected.items()) or
            link.get('registered_config_sha256') != parent['config_sha256'] or
            source.get('source_config_sha256') != parent['config_sha256']):
        raise ValueError('父实验题级来源未核实或不匹配；历史缺少关联须另行留证审核，不能自动回填')
    return link
