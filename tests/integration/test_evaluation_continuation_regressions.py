"""R1/R2定向回归：源于独立审查探针，正式关联由adapter实际创建。"""
from datetime import datetime, timedelta, timezone
import json

import pytest

from tests.integration.test_evaluation_run_adapter import (
    evaluation_context, begin_parent_execution, finish_parent_execution)
from app.evaluation.query_adapter import RealQueryExecutor
from app.evaluation.provider_counts import LogicalProviderCounts
from app.evaluation.validate_dataset import fingerprint
from app.identity.models import Principal

pytestmark = pytest.mark.integration


def interrupted_source(ctx):
    cfg, factory, resources, prompts, question, _ = ctx
    cfg['metric_schema_version'] = 1
    counts = LogicalProviderCounts()
    model = resources['query_runner'].llm_factory
    resources['provider_counts'] = counts
    resources['query_runner'].llm_factory = lambda: counts.wrap(model())
    parent = begin_parent_execution(cfg, resources)
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        execute.control_db = resources['db']
        execute.execution = parent[-1]
        original = execute(question)
    resources['runs'].runs.update_one({'run_id': original['run_id']}, {'$set': {
        'state': 'running', 'execution_token': 'expired-test',
        'execution_lease': datetime.now(timezone.utc) - timedelta(seconds=1)}})
    assert original['run_id'] in resources['commands'].recover()
    context = finish_parent_execution(parent)
    return cfg, factory, resources, prompts, question, context, parent


def test_completed_run_crash_recovery_preserves_observed_call_count(evaluation_context, monkeypatch, tmp_path):
    from tests.unit.test_evaluation_dataset import case, freeze
    from app.evaluation.runner import run_experiment
    cfg, _, _, _, question, _ = evaluation_context
    row = case() | {k: question[k] for k in ('question', 'product_names', 'history')}
    dataset, manifest, frozen = freeze(tmp_path, [row])
    from app.evaluation.validate_dataset import file_sha
    cfg.update({k: frozen[k] for k in ('dataset_sha256', 'phase', 'split', 'versions', 'execution_mode')})
    cfg.update(seed=11, split_manifest_sha256=file_sha(manifest))
    cfg, factory, resources, prompts, question, context, _ = interrupted_source(evaluation_context)
    real_execute = resources['query_runner'].execute
    def finish_then_crash(rid):
        real_execute(rid)
        raise RuntimeError('合成退出：Run完成后、结果落盘前')
    monkeypatch.setattr(resources['query_runner'], 'execute', finish_then_crash)
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        execute.control_db = resources['db']
        execute.continuation = context
        with pytest.raises(RuntimeError, match='合成退出'):
            execute(question)
    ledger = resources['db'].evaluation_continuations.find_one({})
    assert ledger['state'] == 'completed'
    assert ledger['logical_provider_calls'] == dict(invoke_started=0, stream_started=1)
    before = len(prompts)
    monkeypatch.setattr(resources['query_runner'], 'execute', real_execute)
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        execute.control_db = resources['db']
        execute.continuation = context
        result = execute(question)
        assert result['logical_provider_calls'] == ledger['logical_provider_calls']
        assert result['execution_logical_provider_calls'] == dict(invoke_started=0, stream_started=0)
        assert result['logical_provider_calls_scope'] == 'run_total'
        report = run_experiment(dataset, manifest, cfg, tmp_path/'out', execute)
        again = run_experiment(dataset, manifest, cfg, tmp_path/'out', lambda q: pytest.fail('不得再执行'))
    assert report['summary']['accounting']['logical_provider_calls'] == dict(invoke_started=0, stream_started=1)
    assert again['summary'] == report['summary']
    stored = json.loads((tmp_path/'out/results.jsonl').read_text('utf-8'))
    assert stored['result']['logical_provider_calls'] == ledger['logical_provider_calls']
    assert len(prompts) == before and result['run_id'] == ledger['run_id']


def test_normal_completion_and_reuse_separate_run_total_from_invocation(evaluation_context):
    cfg, factory, resources, prompts, question, context, _ = interrupted_source(evaluation_context)
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        execute.control_db = resources['db']
        execute.continuation = context
        fresh = execute(question)
        replay = execute(question)
    assert fresh['logical_provider_calls'] == replay['logical_provider_calls'] == dict(invoke_started=0, stream_started=1)
    assert fresh['execution_logical_provider_calls'] == dict(invoke_started=0, stream_started=1)
    assert replay['execution_logical_provider_calls'] == dict(invoke_started=0, stream_started=0)
    assert fresh['run_id'] == replay['run_id'] and len(prompts) == 2


@pytest.mark.parametrize('mismatch', ['experiment', 'attempt', 'input', 'missing'])
def test_declared_source_must_match_parent_question_link(evaluation_context, mismatch):
    cfg, factory, resources, prompts, question, context, parent = interrupted_source(evaluation_context)
    repo, user, descriptor, resolved, data, execution = parent
    child = repo.get_experiment(user, context['experiment_id'])
    repo.cancel(user, child['experiment_id'], child['version'])
    if mismatch == 'experiment':
        other = repo.create(user, data | {'client_request_id': 'unrelated-parent'}, descriptor=descriptor, resolved=resolved)
        claim = repo.claim(other['experiment_id'])
        failed = repo.fail(other['experiment_id'], claim['attempt'], claim['worker_token'],
                           error_code='provider_invalid_response', retryable=False)
        child = repo.create(user, data | dict(client_request_id='unrelated-child', continuation=dict(
            source_experiment_id=failed['experiment_id'], source_attempt=failed['attempt'],
            source_version=failed['version'], reason='不能认领另一实验的Run')),
            descriptor=descriptor, resolved=resolved)
        context = dict(experiment_id=child['experiment_id'], source=child['continuation'])
    elif mismatch == 'attempt':
        context = dict(context, source=dict(context['source'], source_attempt=execution['attempt']+1))
    elif mismatch == 'input':
        question = dict(question, history=[{'role': 'user', 'text': '不同的输入历史'}])
    else:
        # 历史缺少正式关联：使用另一新config生成旧式直接运行，不创建execution link。
        cfg['experiment_id'] = 'legacy-no-source-link'
        with RealQueryExecutor(cfg, resource_factory=factory) as execute:
            legacy = execute(question)
        resources['runs'].runs.update_one({'run_id': legacy['run_id']}, {'$set': {
            'state': 'running', 'execution_token': 'expired-legacy',
            'execution_lease': datetime.now(timezone.utc)-timedelta(seconds=1)}})
        resources['commands'].recover()
    before = len(prompts)
    runs_before = resources['runs'].runs.count_documents({})
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        execute.control_db = resources['db']
        execute.continuation = context
        with pytest.raises(ValueError, match='来源|父|输入'):
            execute(question)
    assert len(prompts) == before and resources['runs'].runs.count_documents({}) == runs_before
    assert resources['db'].evaluation_continuations.count_documents({}) == 0


def test_current_parent_attempt_without_link_cannot_inherit_previous_attempt_run(evaluation_context):
    cfg, factory, resources, prompts, question, _ = evaluation_context
    cfg['metric_schema_version'] = 1
    parent = begin_parent_execution(cfg, resources)
    repo, user, descriptor, resolved, data, execution = parent
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        execute.control_db = resources['db']
        execute.execution = execution
        original = execute(question)
    resources['runs'].runs.update_one({'run_id': original['run_id']}, {'$set': {
        'state': 'running', 'execution_token': 'expired-first-attempt',
        'execution_lease': datetime.now(timezone.utc)-timedelta(seconds=1)}})
    resources['commands'].recover()
    failed = repo.fail(execution['experiment_id'], execution['attempt'], execution['worker_token'],
                       error_code='upstream_timeout', retryable=True)
    repo.retry(user, failed['experiment_id'], failed['version'])
    second = repo.claim(failed['experiment_id'])
    failed = repo.fail(second['experiment_id'], second['attempt'], second['worker_token'],
                       error_code='provider_invalid_response', retryable=False)
    child = repo.create(user, data | dict(client_request_id='attempt-two-child', continuation=dict(
        source_experiment_id=failed['experiment_id'], source_attempt=failed['attempt'],
        source_version=failed['version'], reason='当前父attempt未执行题目，不能继承上代来源')),
        descriptor=descriptor, resolved=resolved)
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        execute.control_db = resources['db']
        execute.continuation = dict(experiment_id=child['experiment_id'], source=child['continuation'])
        with pytest.raises(ValueError, match='父.*来源'):
            execute(question)
    assert len(prompts) == 1 and resources['runs'].runs.count_documents({}) == 1


def test_missing_persistent_measurement_is_unknown_even_when_replay_counter_is_zero(evaluation_context):
    cfg, factory, resources, prompts, question, _ = evaluation_context
    cfg['metric_schema_version'] = 1
    counts = LogicalProviderCounts()
    model = resources['query_runner'].llm_factory
    resources['provider_counts'] = counts
    resources['query_runner'].llm_factory = lambda: counts.wrap(model())
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        first = execute(question)
    resources['runs'].runs.update_one({'run_id': first['run_id']}, {'$unset': {'telemetry.logical_provider_calls': ''}})
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        replay = execute(question)
    assert replay['logical_provider_calls'] is None
    assert replay['execution_logical_provider_calls'] == dict(invoke_started=0, stream_started=0)
    assert len(prompts) == 1


def test_clarify_persists_measured_zero_and_replay_keeps_zero(evaluation_context):
    from app.knowledge.api import ProductInput
    cfg, factory, resources, prompts, question, _ = evaluation_context
    cfg['metric_schema_version'] = 1
    g = resources['knowledge']()
    user = Principal(user_id=cfg['target']['owner_id'], username='合成验证', role='maintainer', kb_ids=(cfg['target']['kb_id'],))
    g.add_product(user, cfg['target']['kb_id'], ProductInput(kb_id=cfg['target']['kb_id'], model='AX2'))
    question = dict(question, product_names=[], history=[], question='它的额定电压是多少？')
    resources['provider_counts'] = LogicalProviderCounts()
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        first = execute(question)
        replay = execute(question)
    assert first['state'] == replay['state'] == 'awaiting_input'
    assert first['logical_provider_calls'] == replay['logical_provider_calls'] == dict(invoke_started=0, stream_started=0)
    assert replay['execution_logical_provider_calls'] == dict(invoke_started=0, stream_started=0)
    assert prompts == []


def test_formal_job_binds_source_before_execution_and_continuation_verifies_it(evaluation_context, tmp_path, monkeypatch):
    from app.evaluation.catalog import EvaluationCatalog
    from app.evaluation.repository import EvaluationRepository
    from app.evaluation.service import EvaluationService
    from app.evaluation.jobs import execute_job
    from app.evaluation.validate_dataset import file_sha
    from tests.unit.test_evaluation_dataset import case, freeze
    from app.identity.models import Principal
    cfg, factory, resources, prompts, question, _ = evaluation_context
    questions = [case() | {k: question[k] for k in ('question', 'product_names', 'history')}]
    questions += [case('unused-'+str(i), 'heldout', 'heldout-'+str(i)) for i in range(49)]
    dataset, manifest, frozen = freeze(tmp_path, questions)
    cfg.update({k: frozen[k] for k in ('dataset_sha256', 'phase', 'split', 'versions')})
    cfg.update(metric_schema_version=1, seed=11, execution_mode='real_query_runner', split_manifest_sha256=file_sha(manifest))
    (tmp_path/'config.json').write_text(json.dumps(cfg), encoding='utf-8')
    (tmp_path/'catalog.json').write_text(json.dumps(dict(datasets=[dict(id='set', version='r1', dataset=dataset.name,
        manifest=manifest.name, kb_ids=[cfg['target']['kb_id']])], configs=[dict(id='control', version='r1', path='config.json')])), encoding='utf-8')
    catalog = EvaluationCatalog(tmp_path/'catalog.json')
    repo = EvaluationRepository(resources['db'])
    service = EvaluationService(repo, catalog)
    user = Principal(user_id=cfg['target']['owner_id'], username='合成任务', role='maintainer', kb_ids=(cfg['target']['kb_id'],))
    service.register_set(user, dict(kb_id=cfg['target']['kb_id'], eval_set_id='set', version='r1'))
    data = dict(kb_id=cfg['target']['kb_id'], eval_set_id='set', eval_set_version='r1',
                config_id='control', config_version='r1', client_request_id='job-parent')
    parent = service.create_experiment(user, data)
    counts = LogicalProviderCounts()
    model = resources['query_runner'].llm_factory
    resources['provider_counts'] = counts
    resources['query_runner'].llm_factory = lambda: counts.wrap(model())
    class InjectedResources(RealQueryExecutor):
        def __init__(self, config): super().__init__(config, resource_factory=factory)
    monkeypatch.setattr('app.evaluation.query_adapter.RealQueryExecutor', InjectedResources)
    real_execute = resources['query_runner'].execute
    def interrupted_job_run(rid):
        link = resources['db'].evaluation_execution_links.find_one({'run_id': rid})
        assert link['experiment_id'] == parent['experiment_id'] and link['attempt'] == 1
        assert link['mode'] == 'execution'
        real_execute(rid)
        resources['runs'].runs.update_one({'run_id': rid}, {'$set': {'state': 'running',
            'execution_token': 'expired-job-test', 'execution_lease': datetime.now(timezone.utc)-timedelta(seconds=1)}})
        resources['commands'].recover()
        raise RuntimeError('合成中断')
    monkeypatch.setattr(resources['query_runner'], 'execute', interrupted_job_run)
    execute_job(repo, catalog, tmp_path/'out', parent['experiment_id'])
    failed = repo.get_experiment(user, parent['experiment_id'])
    assert failed['state'] == 'failed' and failed['attempt'] == 1
    before = dict(failed)
    child = service.create_experiment(user, data | dict(client_request_id='job-child', continuation=dict(
        source_experiment_id=failed['experiment_id'], source_attempt=failed['attempt'],
        source_version=failed['version'], reason='正式任务关联后续')))
    monkeypatch.setattr(resources['query_runner'], 'execute', real_execute)
    execute_job(repo, catalog, tmp_path/'out', child['experiment_id'])
    assert repo.get_experiment(user, child['experiment_id'])['state'] == 'completed'
    ledger = resources['db'].evaluation_continuations.find_one({})
    parent_link = resources['db'].evaluation_execution_links.find_one({'experiment_id': parent['experiment_id']})
    child_link = resources['db'].evaluation_execution_links.find_one({'experiment_id': child['experiment_id']})
    assert ledger['source_link_id'] == parent_link['_id']
    assert ledger['source_run_id'] == parent_link['run_id']
    assert ledger['run_id'] == child_link['run_id'] != parent_link['run_id']
    assert repo.get_experiment(user, parent['experiment_id']) == before
    inherited = service.create_experiment(user, data | {'client_request_id': 'observed-reuse'})
    execute_job(repo, catalog, tmp_path/'out', inherited['experiment_id'])
    inherited_link = resources['db'].evaluation_execution_links.find_one({'experiment_id': inherited['experiment_id']})
    assert inherited_link['mode'] == 'observed_reuse' and inherited_link['run_id'] == child_link['run_id']
    result = repo.results_page(inherited['experiment_id'])['items'][0]['result']
    assert result['logical_provider_calls_scope'] == 'run_total'
    assert result['logical_provider_calls'] == dict(invoke_started=0, stream_started=1)
    assert result['execution_logical_provider_calls'] == dict(invoke_started=0, stream_started=0)
    assert len(prompts) == 2
