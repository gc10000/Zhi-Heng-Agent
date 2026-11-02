import pytest


pytestmark = pytest.mark.integration


def seed_running_experiment(db, *, role='maintainer', kb_ids=('kb-delegated',)):
    from app.evaluation.repository import EvaluationRepository
    from app.evaluation.validate_dataset import fingerprint
    from app.identity.models import Principal

    owner_id = 'evaluation-maintainer'
    user = Principal(user_id=owner_id, username='isolated-evaluation-maintainer', role=role,
                     kb_ids=tuple(kb_ids))
    db.users.insert_one(user.model_dump(mode='json') | {'enabled': True})
    config = {
        'target': {'owner_id': 'knowledge-owner', 'kb_id': 'kb-delegated'},
    }
    descriptor = {
        'id': 'm6-owner-scope', 'version': 'r1', 'kb_id': 'kb-delegated',
        'dataset_sha256': 'd' * 64, 'manifest_sha256': 'e' * 64,
        'question_count': 1, 'dev_count': 1, 'review_eligible_count': 0,
        'configs': [{'id': 'm6-owner-scope', 'version': 'r1'}],
    }
    repo = EvaluationRepository(db)
    repo.register_set(user, descriptor)
    resolved = {
        'config_sha256': fingerprint(config), 'config': config,
        'selected_questions': 1, 'eligible_questions': 0,
    }
    created = repo.create(user, {
        'kb_id': 'kb-delegated', 'eval_set_id': descriptor['id'],
        'eval_set_version': descriptor['version'], 'config_id': 'm6-owner-scope',
        'config_version': 'r1', 'client_request_id': 'm6-owner-scope-r1',
    }, descriptor=descriptor, resolved=resolved)
    parent = repo.claim(created['experiment_id'])
    context = {key: parent[key] for key in (
        'experiment_id', 'attempt', 'worker_token', 'config_sha256')}
    return context, config, owner_id


def test_execution_link_accepts_authorized_evaluation_owner_separate_from_kb_owner(mongo_db):
    from app.evaluation.execution_links import validate_execution

    context, config, owner_id = seed_running_experiment(mongo_db)

    parent = validate_execution(mongo_db, context, config)

    assert parent['owner_id'] == owner_id
    assert parent['owner_id'] != config['target']['owner_id']
    assert parent['knowledge_owner_id'] == config['target']['owner_id']


@pytest.mark.parametrize('role,kb_ids', [
    ('viewer', ('kb-delegated',)),
    ('maintainer', ('another-kb',)),
])
def test_execution_link_rejects_unqualified_evaluation_owner(mongo_db, role, kb_ids):
    from app.evaluation.execution_links import validate_execution

    context, config, _ = seed_running_experiment(mongo_db, role=role, kb_ids=kb_ids)

    with pytest.raises(ValueError):
        validate_execution(mongo_db, context, config)


@pytest.mark.parametrize('change', ['target_owner', 'revoked', 'expired', 'legacy_separate'])
def test_execution_link_rejects_changed_target_permission_or_legacy_owner(mongo_db, change):
    from datetime import datetime, timedelta, timezone
    from app.evaluation.execution_links import validate_execution

    context, config, owner_id = seed_running_experiment(mongo_db)
    if change == 'target_owner':
        config['target']['owner_id'] = 'another-knowledge-owner'
    elif change == 'revoked':
        mongo_db.users.update_one({'user_id': owner_id}, {'$set': {'enabled': False}})
    elif change == 'expired':
        mongo_db.evaluation_experiments.update_one({'experiment_id': context['experiment_id']},
            {'$set': {'lease_until': datetime.now(timezone.utc) - timedelta(seconds=1)}})
    else:
        mongo_db.evaluation_experiments.update_one({'experiment_id': context['experiment_id']},
            {'$unset': {'knowledge_owner_id': ''}})
    with pytest.raises(ValueError):
        validate_execution(mongo_db, context, config)


@pytest.mark.parametrize('separate', [False, True])
def test_delegated_formal_job_continuation_and_completed_reuse(
        evaluation_context, tmp_path, monkeypatch, separate):
    from app.evaluation.jobs import execute_job
    from app.identity.models import Principal
    from tests.integration.test_evaluation_split_ledger import formal_case, interrupt

    cfg, resources, prompts, question, repo, service, _, data, catalog = formal_case(
        evaluation_context, tmp_path, monkeypatch, separate=separate)
    user = Principal(user_id='delegated-maintainer', username='授权维护者',
        role='maintainer', kb_ids=(cfg['target']['kb_id'],))
    repo.db.users.insert_one(user.model_dump(mode='json') | {'enabled': True})
    service.register_set(user, dict(kb_id=cfg['target']['kb_id'], eval_set_id='set', version='r1'))
    parent = service.create_experiment(user, data)
    original_execute = resources['query_runner'].execute

    def interrupted(rid):
        original_execute(rid)
        interrupt(resources, rid)
        raise RuntimeError('合成中断，验证授权维护者恢复来源')

    monkeypatch.setattr(resources['query_runner'], 'execute', interrupted)
    execute_job(repo, catalog, tmp_path/'out', parent['experiment_id'])
    failed = repo.get_experiment(user, parent['experiment_id'])
    assert failed['state'] == 'failed' and len(prompts) == 1
    child = service.create_experiment(user, data | dict(client_request_id='delegated-child',
        continuation=dict(source_experiment_id=failed['experiment_id'],
            source_attempt=failed['attempt'], source_version=failed['version'], reason='合成恢复')))
    monkeypatch.setattr(resources['query_runner'], 'execute', original_execute)
    execute_job(repo, catalog, tmp_path/'out', child['experiment_id'])
    assert repo.get_experiment(user, child['experiment_id'])['state'] == 'completed'
    assert len(prompts) == 2
    reused = service.create_experiment(user, data | dict(client_request_id='delegated-reuse'))
    execute_job(repo, catalog, tmp_path/'out', reused['experiment_id'])
    assert repo.get_experiment(user, reused['experiment_id'])['state'] == 'completed'
    assert len(prompts) == 2
    assert resources['db'].evaluation_execution_links.find_one({
        'experiment_id': reused['experiment_id']})['mode'] == 'observed_reuse'


# 复用正式隔离Run夹具，模型和检索端口为合成输入。
from tests.integration.test_evaluation_run_adapter import evaluation_context
