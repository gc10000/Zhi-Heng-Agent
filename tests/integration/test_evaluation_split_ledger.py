"""正式job组合：控制账本与隔离Run库可分离，不复制实验身份。"""
from datetime import datetime, timedelta, timezone
import json

import pytest

from app.evaluation.catalog import EvaluationCatalog
from app.evaluation.jobs import execute_job
from app.evaluation.provider_counts import LogicalProviderCounts
from app.evaluation.query_adapter import RealQueryExecutor
from app.evaluation.repository import EvaluationRepository
from app.evaluation.service import EvaluationService
from app.evaluation.validate_dataset import file_sha
from app.identity.models import Principal
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.unit.test_evaluation_dataset import case, freeze

pytestmark = pytest.mark.integration


def formal_case(ctx, tmp_path, monkeypatch, *, separate=True, reviewed=False):
    cfg, factory, resources, prompts, question, _ = ctx
    rows = [case() | {k: question[k] for k in ('question', 'product_names', 'history')}]
    rows += [case('heldout-'+str(i), 'heldout', 'fresh-'+str(i)) for i in range(49)]
    if reviewed:
        from tests.unit.test_evaluation_dataset import independent_annotation
        rows[0]['annotation'] = independent_annotation(rows[0])
    dataset, manifest, frozen = freeze(tmp_path, rows)
    cfg.update({k: frozen[k] for k in ('dataset_sha256', 'phase', 'split', 'versions')})
    cfg.update(metric_schema_version=1, seed=11, execution_mode='real_query_runner',
               split_manifest_sha256=file_sha(manifest))
    (tmp_path/'config.json').write_text(json.dumps(cfg), encoding='utf-8')
    (tmp_path/'catalog.json').write_text(json.dumps(dict(datasets=[dict(id='set', version='r1',
        dataset=dataset.name, manifest=manifest.name, kb_ids=[cfg['target']['kb_id']])],
        configs=[dict(id='control', version='r1', path='config.json')])), encoding='utf-8')
    catalog = EvaluationCatalog(tmp_path/'catalog.json')
    target = resources['db']
    control = target.client[target.name+'_ctrl'] if separate else target
    repo = EvaluationRepository(control)
    service = EvaluationService(repo, catalog)
    user = Principal(user_id=cfg['target']['owner_id'], username='分库隔离验证',
                     role='maintainer', kb_ids=(cfg['target']['kb_id'],))
    service.register_set(user, dict(kb_id=cfg['target']['kb_id'], eval_set_id='set', version='r1'))
    data = dict(kb_id=cfg['target']['kb_id'], eval_set_id='set', eval_set_version='r1',
                config_id='control', config_version='r1', client_request_id='first')
    class InjectedResources(RealQueryExecutor):
        def __init__(self, config): super().__init__(config, resource_factory=factory)
    monkeypatch.setattr('app.evaluation.query_adapter.RealQueryExecutor', InjectedResources)
    counts = LogicalProviderCounts()
    model = resources['query_runner'].llm_factory
    resources['provider_counts'] = counts
    resources['query_runner'].llm_factory = lambda: counts.wrap(model())
    return cfg, resources, prompts, question, repo, service, user, data, catalog


def interrupt(resources, rid):
    resources['runs'].runs.update_one({'run_id': rid}, {'$set': {'state': 'running',
        'execution_token': 'isolated-expired', 'execution_lease': datetime.now(timezone.utc)-timedelta(seconds=1)}})
    assert rid in resources['commands'].recover()


@pytest.mark.parametrize('separate', [False, True])
def test_formal_first_question_and_completed_observed_reuse(evaluation_context, tmp_path, monkeypatch, separate):
    cfg, resources, prompts, question, repo, service, user, data, catalog = formal_case(
        evaluation_context, tmp_path, monkeypatch, separate=separate)
    target = resources['db']
    for key in ('first', 'reuse'):
        job = service.create_experiment(user, data | {'client_request_id': key})
        execute_job(repo, catalog, tmp_path/'out', job['experiment_id'])
        assert repo.get_experiment(user, job['experiment_id'])['state'] == 'completed'
        link = target.evaluation_execution_links.find_one({'experiment_id': job['experiment_id']})
        assert link['control_database'] == repo.db.name
        assert link['target_database'] == target.name
        assert link['mode'] == ('execution' if key == 'first' else 'observed_reuse')
        assert 'worker_token' not in link
        result = repo.results_page(job['experiment_id'])['items'][0]['result']
        assert result['logical_provider_calls'] == dict(invoke_started=0, stream_started=1)
        assert result['execution_logical_provider_calls']['stream_started'] == (1 if key == 'first' else 0)
    assert len(prompts) == 1 and target.runs.count_documents({}) == 1
    assert target.runs.find_one({})['state'] == 'completed'
    if separate:
        assert target.evaluation_experiments.count_documents({}) == 0
        assert repo.db.runs.count_documents({}) == repo.db.evaluation_execution_links.count_documents({}) == 0


@pytest.mark.parametrize('crash_point', [None, 'after_create', 'after_link'])
def test_split_continuation_and_reconstructed_job_keep_fixed_run(evaluation_context, tmp_path, monkeypatch, crash_point):
    cfg, resources, prompts, question, repo, service, user, data, catalog = formal_case(
        evaluation_context, tmp_path, monkeypatch)
    target = resources['db']
    parent = service.create_experiment(user, data)
    real_execute = resources['query_runner'].execute
    def parent_interrupted(rid):
        link = target.evaluation_execution_links.find_one({'run_id': rid})
        assert link['experiment_id'] == parent['experiment_id']
        real_execute(rid)
        interrupt(resources, rid)
        raise RuntimeError('合成父任务中断')
    monkeypatch.setattr(resources['query_runner'], 'execute', parent_interrupted)
    execute_job(repo, catalog, tmp_path/'out', parent['experiment_id'])
    failed = repo.get_experiment(user, parent['experiment_id'])
    assert failed['state'] == 'failed'
    parent_before = dict(failed)
    child = service.create_experiment(user, data | dict(client_request_id='child', continuation=dict(
        source_experiment_id=failed['experiment_id'], source_attempt=failed['attempt'],
        source_version=failed['version'], reason='分库后续来源验证')))
    monkeypatch.setattr(resources['query_runner'], 'execute', real_execute)
    if crash_point:
        real_create = resources['run_service'].create
        def create_then_exit(*args, **kwargs):
            real_create(*args, **kwargs)
            raise SystemExit('合成进程退出：新Run已创建，尚未关联')
        def linked_then_exit(rid):
            assert target.evaluation_execution_links.find_one({'run_id': rid})
            raise SystemExit('合成进程退出：已关联，尚未模型调用')
        if crash_point == 'after_create':
            monkeypatch.setattr(resources['run_service'], 'create', create_then_exit)
        else:
            monkeypatch.setattr(resources['query_runner'], 'execute', linked_then_exit)
        with pytest.raises(SystemExit, match='合成进程退出'):
            execute_job(repo, catalog, tmp_path/'out', child['experiment_id'])
        assert len(prompts) == 1 and target.runs.count_documents({'state': 'pending'}) == 1
        pending = target.runs.find_one({'state': 'pending'})['run_id']
        monkeypatch.setattr(resources['run_service'], 'create', real_create)
        monkeypatch.setattr(resources['query_runner'], 'execute', real_execute)
        # 仅在随机测试控制库模拟进程退出后的lease超时，再由正式claim领取新attempt。
        repo.experiments.update_one({'experiment_id': child['experiment_id']},
            {'$set': {'lease_until': datetime.now(timezone.utc)-timedelta(seconds=1)}})
    execute_job(repo, catalog, tmp_path/'out', child['experiment_id'])
    actual = repo.get_experiment(user, child['experiment_id'])
    assert actual['state'] == 'completed' and actual['attempt'] == (2 if crash_point else 1)
    ledger = target.evaluation_continuations.find_one({})
    source = target.evaluation_execution_links.find_one({'_id': ledger['source_link_id']})
    assert source['control_database'] == repo.db.name and source['target_database'] == target.name
    assert ledger['source_run_id'] == source['run_id'] != ledger['run_id']
    if crash_point:
        assert ledger['run_id'] == pending
    assert target.runs.count_documents({}) == 2 and len(prompts) == 2
    assert repo.get_experiment(user, parent['experiment_id']) == parent_before
    assert target.evaluation_experiments.count_documents({}) == 0
    # 已完成job重投由正式claim拒绝，不新建Run/调用。
    execute_job(repo, catalog, tmp_path/'out', child['experiment_id'])
    assert target.runs.count_documents({}) == 2 and len(prompts) == 2


@pytest.mark.parametrize('invalid', ['missing_control', 'token', 'expired_lease', 'attempt'])
def test_invalid_control_identity_rejected_before_target_side_effects(evaluation_context, tmp_path, monkeypatch, invalid):
    cfg, resources, prompts, question, repo, service, user, data, catalog = formal_case(
        evaluation_context, tmp_path, monkeypatch)
    job = service.create_experiment(user, data)
    claim = repo.claim(job['experiment_id'])
    context = {k: claim[k] for k in ('experiment_id', 'attempt', 'worker_token', 'config_sha256')}
    if invalid == 'token': context['worker_token'] = 'wrong-worker'
    if invalid == 'attempt': context['attempt'] += 1
    if invalid == 'expired_lease':
        repo.experiments.update_one({'experiment_id': job['experiment_id']},
            {'$set': {'lease_until': datetime.now(timezone.utc)-timedelta(seconds=1)}})
    # 即便目标库有同名控制记录，也不能作为真实控制库的替代授权。
    resources['db'].evaluation_experiments.insert_one(claim)
    with RealQueryExecutor(cfg, resource_factory=evaluation_context[1]) as execute:
        execute.execution = context
        if invalid != 'missing_control': execute.control_db = repo.db
        with pytest.raises(ValueError, match='控制|身份|租约'):
            execute(question)
    assert prompts == []
    for name in ('conversations', 'runs', 'evaluation_items', 'evaluation_execution_links', 'evaluation_continuations'):
        assert resources['db'][name].count_documents({}) == 0, name


@pytest.mark.parametrize('mismatch', ['parent', 'attempt', 'control_mapping', 'target_mapping'])
def test_split_wrong_parent_attempt_or_database_mapping_rejected_before_new_run(evaluation_context, tmp_path, monkeypatch, mismatch):
    cfg, resources, prompts, question, repo, service, user, data, catalog = formal_case(
        evaluation_context, tmp_path, monkeypatch)
    parent = service.create_experiment(user, data)
    claim = repo.claim(parent['experiment_id'])
    with RealQueryExecutor(cfg, resource_factory=evaluation_context[1]) as execute:
        execute.control_db = repo.db
        execute.execution = {k: claim[k] for k in ('experiment_id', 'attempt', 'worker_token', 'config_sha256')}
        original = execute(question)
    interrupt(resources, original['run_id'])
    failed = repo.fail(claim['experiment_id'], claim['attempt'], claim['worker_token'],
                       error_code='upstream_timeout', retryable=True)
    if mismatch == 'parent':
        other = service.create_experiment(user, data | {'client_request_id': 'unrelated-parent'})
        other_claim = repo.claim(other['experiment_id'])
        failed = repo.fail(other_claim['experiment_id'], other_claim['attempt'], other_claim['worker_token'],
                           error_code='provider_invalid_response', retryable=False)
    elif mismatch == 'attempt':
        # 父实验正式推进attempt2，但仅attempt1有该题执行关联。
        repo.retry(user, failed['experiment_id'], failed['version'])
        second = repo.claim(failed['experiment_id'])
        failed = repo.fail(second['experiment_id'], second['attempt'], second['worker_token'],
                           error_code='provider_invalid_response', retryable=False)
    else:
        # 仅随机测试库构造来源映射损坏；不能读取另一控制库/目标库的关联放行。
        field = 'control_database' if mismatch == 'control_mapping' else 'target_database'
        resources['db'].evaluation_execution_links.update_one({'run_id': original['run_id']},
                                                              {'$set': {field: 'unrelated-ledger'}})
    child = service.create_experiment(user, data | dict(client_request_id='rejected-child', continuation=dict(
        source_experiment_id=failed['experiment_id'], source_attempt=failed['attempt'],
        source_version=failed['version'], reason='不能认领其他父代际或库映射')))
    execute_job(repo, catalog, tmp_path/'out', child['experiment_id'])
    assert repo.get_experiment(user, child['experiment_id'])['state'] == 'failed'
    target = resources['db']
    assert target.runs.count_documents({}) == 1 and len(prompts) == 1
    assert target.evaluation_continuations.count_documents({}) == 0
    assert target.evaluation_execution_links.count_documents({'experiment_id': child['experiment_id']}) == 0
    details = json.loads((tmp_path/'out'/child['experiment_id']/'results.jsonl').read_text('utf-8'))
    assert details['status'] == 'failed' and details['error']['type'] == 'ValueError'


def test_control_lease_lost_after_run_creation_uses_formal_pending_recovery(evaluation_context, tmp_path, monkeypatch):
    cfg, resources, prompts, question, repo, service, user, data, catalog = formal_case(
        evaluation_context, tmp_path, monkeypatch)
    job = service.create_experiment(user, data)
    real_create = resources['run_service'].create
    def create_then_lease_expires(*args, **kwargs):
        run = real_create(*args, **kwargs)
        repo.experiments.update_one({'experiment_id': job['experiment_id']},
            {'$set': {'lease_until': datetime.now(timezone.utc)-timedelta(seconds=1)}})
        return run
    monkeypatch.setattr(resources['run_service'], 'create', create_then_lease_expires)
    execute_job(repo, catalog, tmp_path/'out', job['experiment_id'])
    target = resources['db']
    pending = target.runs.find_one({})
    assert pending['state'] == 'pending' and prompts == []
    assert target.evaluation_execution_links.count_documents({}) == 0
    # 不清lease/slot，不删Run；注入恢复时钟，走正式pending超时协议。
    commands = resources['commands']
    monkeypatch.setattr(commands, 'clock', lambda: datetime.now(timezone.utc)+timedelta(days=1))
    assert pending['run_id'] in commands.recover()
    assert target.runs.find_one({'run_id': pending['run_id']})['state'] == 'interrupted'
    assert target.run_events.count_documents({'run_id': pending['run_id'], 'type': 'run.interrupted'}) == 1
    assert resources['conversations'].conversations.find_one({'conversation_id': pending['conversation_id']})['active_run_id'] is None
