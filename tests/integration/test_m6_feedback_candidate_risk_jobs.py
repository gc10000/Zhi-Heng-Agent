"""完整候选共享CAS、顺序、零调用澄清与故障阻断；只使用随机隔离Mongo。"""
from concurrent.futures import ThreadPoolExecutor
from threading import Event, Thread
from types import SimpleNamespace

import pytest

from app.api.errors import APIError

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('publication', ['exception', 'timeout', 'no_publication', 'cancelled', 'incomplete', 'in_flight'])
def test_job_publication_failure_seals_shared_candidate_batch(mongo_db, tmp_path, monkeypatch, publication):
    """已结算Run之后的发布失败也必须阻断下一版，不能留下open账本。"""
    import json
    from app.evaluation import runner, validate_dataset
    from app.evaluation.jobs import execute_job
    from app.evaluation.repository import EvaluationRepository
    from tests.integration.test_evaluation_jobs import create

    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    case.ledger.begin(case.run_id, case.run_identity, input_reservation=12, risk_context=case.context)
    if publication!='in_flight': settle(case)
    repo = EvaluationRepository(mongo_db)
    user, row = create(repo)
    row = repo.experiments.find_one({'experiment_id':row['experiment_id']})
    config = dict(target=dict(database=case.db.name), parameters=dict(answer_budget=dict(
        output_contract=case.ledger.policy.model_dump(mode='json'))))
    resolved = dict(dataset_sha256=row['dataset_sha256'], manifest_sha256=row['manifest_sha256'],
        config_sha256=row['config_sha256'], config=config, dataset_path=tmp_path/'unused-dataset',
        manifest_path=tmp_path/'unused-manifest')
    catalog = SimpleNamespace(resolve=lambda *args, **kwargs: resolved)
    question = dict(id='q', split='dev', category='parameter', question='合成问题')
    monkeypatch.setattr(validate_dataset, 'validate_dataset', lambda *args, **kwargs: [question])
    def run(*args, **kwargs):
        output = args[3]
        output.mkdir(parents=True)
        (output/'results.jsonl').write_text(json.dumps(dict(id='q', status='completed',
            result=dict(answer='合成结果', citations=[])))+'\n', encoding='utf-8')
        return dict(status='incomplete' if publication=='incomplete' else 'completed', completed=1, failed=0)
    monkeypatch.setattr(runner, 'run_experiment', run)
    complete = repo.complete
    def publish(*args, **kwargs):
        if publication in ('exception','in_flight'): raise OSError('synthetic publication failure')
        if publication=='timeout': raise TimeoutError('synthetic publication timeout')
        if publication=='no_publication': return None
        if publication=='cancelled': repo.cancel(user, row['experiment_id'], repo.experiments.find_one(
            {'experiment_id':row['experiment_id']})['version'])
        return complete(*args, **kwargs)
    monkeypatch.setattr(repo, 'complete', publish)
    class Executor:
        def __init__(self, config): pass
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def verify_completed_checkpoint(self, *args): pass
    execute_job(repo, catalog, tmp_path/'publication', row['experiment_id'], executor_factory=Executor)
    saved = case.ledger._read()
    if publication=='in_flight':
        assert saved['state']=='dispatching' and saved['pending']['run_id']==case.run_id
        assert saved['unknown_windows'] and not (case.batch/'halt.json').exists()
        failed=repo.experiments.find_one({'experiment_id':row['experiment_id']})
        assert failed['error']['code']=='evaluation_execution_failed' and failed['retryable'] is False
        return
    assert saved['state']=='blocked' and saved['cursor']==1
    assert saved['provider_stream_reservations']==1 and saved['pending'] is None
    assert (case.batch/'halt.json').is_file()
    assert repo.experiments.find_one({'experiment_id':row['experiment_id']})['retryable'] is False


def policy(slot='m6-feedback-stage-r1-v1'):
    from app.infrastructure.providers.output_contract import parse_contract
    return parse_contract(dict(
        enabled=True,
        function_version='diagnostic_feedback_candidate_manifest_r1',
        n=1,
        status='unknown',
        endpoint_sha256='a' * 64,
        model='qwen3.8-flash',
        client_versions={'openai': '2.28.0', 'langchain-openai': '1.1.11'},
        limit_field='max_completion_tokens',
        semantics='unknown',
        thinking=False,
        reasoning_budget=None,
        per_request_total_output_tokens=4096,
        ledger_id='m6-feedback-candidate-full-r1',
        max_total_input_tokens=4773888,
        max_total_output_tokens=688128,
        admission=dict(
            authorization=dict(commit='a' * 40,
                path='docs/development/reviews/M6-feedback-stage-authorization-r1.json',
                sha256='b' * 64),
            manifest_sha256='c' * 64,
            member_slot=slot,
        ),
    ))


def full_manifest(control_database, target_databases):
    from app.infrastructure.providers.m6_feedback_candidate_risk import CANDIDATE_SLOTS
    entries = []
    order = []
    for version, candidate_slot in enumerate(CANDIDATE_SLOTS, 1):
        for ordinal in range(1, 86):
            question_id = ('m6-g540-20-a' if ordinal == 40 else f'support-v1-{ordinal:03}')
            slot = f'm6-feedback-stage-r1-v{version}-{question_id}'
            route = ('clarify' if question_id == 'support-v1-047' else
                     'compare' if question_id == 'support-v1-048' else
                     'series' if question_id == 'm6-g540-20-a' else 'answer')
            question = dict(id=question_id, question='合成冻结问题', product_names=['AX'], history=[], split='dev')
            member = dict(candidate_slot=candidate_slot, fixed_slot=slot, version=version,
                ordinal=ordinal, question_id=question_id, split='dev', route=route,
                expected_generation=route != 'clarify', max_provider_streams=int(route != 'clarify'))
            generated = route != 'clarify'
            result = dict(prompt='合成输入-' + slot, context=[], prompt_reference_map=[], groups=[],
                budget=dict(input_tokens=12 if generated else 0, input_limit=28416))
            entries.append(dict(member=member, question=question, production_input=dict(result=result)))
            order.append(slot)
    return dict(version='diagnostic_feedback_candidate_manifest_r1', batch_slot='m6-feedback-candidate-full-r1',
        authorization=dict(commit='a' * 40, path='docs/development/reviews/M6-feedback-stage-authorization-r1.json', sha256='b' * 64),
        shared_control_database=control_database, dispatch_order=order, entries=entries,
        expected_members=170, expected_generated_members=168, expected_clarifications=2)


def isolated_case(mongo_db, tmp_path, monkeypatch, *, separate=False, candidate_slot='m6-feedback-stage-r1-v1'):
    from app.infrastructure.providers import m6_feedback_candidate_risk as risk
    from app.infrastructure.providers.output_contract import OutputLedger

    control = mongo_db.name + '_ctl' if separate else mongo_db.name
    targets = [mongo_db.name + '_t1', mongo_db.name + '_t2']
    manifest = full_manifest(control, targets)
    monkeypatch.setattr(risk, 'require', lambda _: manifest)
    monkeypatch.setattr(risk, 'validate_config', lambda *args, **kwargs: manifest)
    monkeypatch.setattr(risk, 'validate_runtime', lambda *args, **kwargs: None)
    batch = tmp_path / 'batch'
    monkeypatch.setattr(risk, 'batch_dir', lambda: batch)
    monkeypatch.setattr(risk, 'slot_dir', lambda slot: batch / 'members' / slot)
    for entry in manifest['entries']:
        (batch / 'members' / entry['member']['fixed_slot']).mkdir(parents=True, exist_ok=True)

    candidate = 1 if candidate_slot.endswith('v1') else 2
    question_id = 'support-v1-001'
    entry = next(item for item in manifest['entries'] if item['member']['candidate_slot'] == candidate_slot
        and item['member']['question_id'] == question_id)
    db = mongo_db.client[targets[candidate - 1]]
    run_id, run_identity = 'synthetic-run-v1', 'synthetic-run-identity-v1'
    db.runs.insert_one(dict(run_id=run_id, identity=run_identity))
    config = dict(target=dict(database=db.name), synthetic=True)
    context = dict(config=config, question=entry['question'], control_database=control,
        execution=dict(experiment_id=candidate_slot, attempt=1, config_sha256='d' * 64))
    ledger = OutputLedger(db, policy(candidate_slot))
    run = db.runs.find_one({'run_id': run_id})
    expected = risk.input_identity(ledger.policy, run, entry)
    db.feedback_candidate_generation_inputs.insert_one(dict(expected, _id=run_id))
    return SimpleNamespace(risk=risk, manifest=manifest, db=db, ledger=ledger, context=context,
        run_id=run_id, run_identity=run_identity, entry=entry, batch=batch, control=control)


def settle(case, *, completed=True, usage=None, product=None):
    return case.ledger.settle(case.run_id, case.run_identity,
        usage if usage is not None else dict(input=12, output=18), completed=completed,
        product_state=product if product is not None else dict(visible_body=True, truncated=False,
            finish_reason='stop', observed_reasoning=False),
        logical_calls=dict(invoke_started=0, stream_started=1))


@pytest.mark.parametrize('separate', [False, True])
def test_shared_batch_cas_reserves_one_member_across_control_database_layouts(
        mongo_db, tmp_path, monkeypatch, separate):
    case = isolated_case(mongo_db, tmp_path, monkeypatch, separate=separate)
    peer = case.risk.FeedbackCandidateLedger(case.db, case.ledger.policy)

    def reserve(ledger):
        try:
            ledger.begin(case.run_id, case.run_identity, input_reservation=12, risk_context=case.context)
            return True
        except (APIError, FileExistsError):
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(reserve, (case.ledger, peer))) == 1
    saved = case.ledger._read()
    assert saved['state'] == 'dispatching'
    assert saved['pending']['slot'] == case.entry['member']['fixed_slot']
    assert saved['provider_stream_reservations'] == 1
    assert case.ledger.rows.database.name == case.control


def test_successful_member_settlement_advances_exactly_one_cursor_and_duplicate_is_idempotent(
        mongo_db, tmp_path, monkeypatch):
    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    case.ledger.begin(case.run_id, case.run_identity, input_reservation=12, risk_context=case.context)
    first = settle(case)
    again = settle(case)
    assert first == again
    assert first['state'] == 'open' and first['cursor'] == 1
    assert first['known_new_input_tokens'] == 12 and first['known_new_output_tokens'] == 18
    with pytest.raises(APIError):
        case.ledger.begin(case.run_id, case.run_identity, input_reservation=12, risk_context=case.context)


@pytest.mark.parametrize('fault', ['usage_unknown', 'stream_interrupted', 'reasoning_observed', 'truncated', 'input_over_reservation'])
def test_first_member_failure_halts_the_shared_batch_without_releasing_its_slot(
        mongo_db, tmp_path, monkeypatch, fault):
    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    case.ledger.begin(case.run_id, case.run_identity, input_reservation=12, risk_context=case.context)
    usage = {} if fault == 'usage_unknown' else dict(input=12, output=18)
    product = dict(visible_body=True, truncated=False, finish_reason='stop', observed_reasoning=False)
    completed = fault != 'stream_interrupted'
    if fault == 'reasoning_observed':
        product['observed_reasoning'] = True
    if fault == 'truncated':
        product.update(truncated=True, finish_reason='length')
    if fault == 'input_over_reservation':
        usage['input'] = 13
    saved = settle(case, completed=completed, usage=usage, product=product)
    assert saved['state'] == 'blocked' and saved['cursor'] == 0 and saved['pending'] is None
    assert saved['unknown_windows'] and (case.batch / 'halt.json').is_file()
    with pytest.raises(APIError):
        case.ledger.begin(case.run_id, case.run_identity, input_reservation=12, risk_context=case.context)


@pytest.mark.parametrize('logical_calls', [None, {},
    {'invoke_started': 0, 'stream_started': 0},
    {'invoke_started': 0, 'stream_started': 2},
    {'invoke_started': 1, 'stream_started': 1}])
def test_generated_member_requires_exactly_one_observed_provider_call(
        mongo_db, tmp_path, monkeypatch, logical_calls):
    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    case.ledger.begin(case.run_id, case.run_identity, input_reservation=12, risk_context=case.context)
    saved = case.ledger.settle(case.run_id, case.run_identity, dict(input=12, output=18),
        completed=True, product_state=dict(visible_body=True, truncated=False,
            finish_reason='stop', observed_reasoning=False), logical_calls=logical_calls)
    assert saved['state'] == 'blocked' and saved['cursor'] == 0
    assert saved['unknown_windows'] and (case.batch / 'halt.json').is_file()


def test_halt_winning_after_start_marker_prevents_provider_dispatch(
        mongo_db, tmp_path, monkeypatch):
    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    marker_written = Event()
    allow_begin = Event()
    original_exclusive = case.risk.exclusive

    def interleaved_exclusive(path, value):
        original_exclusive(path, value)
        if path.name == 'started.json':
            marker_written.set()
            assert allow_begin.wait(5)

    monkeypatch.setattr(case.risk, 'exclusive', interleaved_exclusive)
    result = []

    def begin():
        try:
            case.ledger.begin(case.run_id, case.run_identity, input_reservation=12,
                risk_context=case.context)
            result.append('dispatched')
        except APIError:
            result.append('blocked')

    thread = Thread(target=begin)
    thread.start()
    assert marker_written.wait(5)
    peer = case.risk.FeedbackCandidateLedger(case.db, case.ledger.policy)
    peer.handler = case.risk
    peer.halt(dict(status='concurrent-stop', slot=case.entry['member']['fixed_slot']))
    allow_begin.set()
    thread.join(5)
    assert not thread.is_alive()
    assert result == ['blocked']
    assert case.ledger._read()['state'] == 'blocked'


def test_unsettled_generated_run_halts_instead_of_releasing_next_member(
        mongo_db, tmp_path, monkeypatch):
    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    case.ledger.initialize()
    with pytest.raises(case.risk.CandidateBatchStop):
        case.ledger.require_run_settled(case.run_id, case.run_identity)
    saved = case.ledger._read()
    assert saved['state'] == 'blocked' and saved['cursor'] == 0
    assert saved['unknown_windows'] and (case.batch / 'halt.json').is_file()


def test_generated_member_requires_its_independent_persisted_input_checkpoint(
        mongo_db, tmp_path, monkeypatch):
    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    run = case.db.runs.find_one({'run_id': case.run_id})
    expected = case.entry['production_input']['result']
    state = dict(evaluation_question_id=case.context['question']['id'],
        prompt_used_docs=expected['context'], prompt_reference_map=expected['prompt_reference_map'],
        evidence_groups=expected['groups'], prompt_budget=expected['budget'])
    case.risk.persist_input(case.ledger.policy, case.db, run, expected['prompt'], state)
    case.risk.validate_persisted_input(case.ledger.policy, case.db, run, case.context['question']['id'])
    case.db.feedback_candidate_generation_inputs.update_one({'_id': case.run_id},
        {'$set': {'input_sha256': 'f' * 64}})
    with pytest.raises(ValueError):
        case.risk.validate_persisted_input(case.ledger.policy, case.db, run, case.context['question']['id'])


def test_recovery_cannot_claim_halt_while_a_dispatch_right_is_in_flight(
        mongo_db, tmp_path, monkeypatch):
    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    case.ledger.begin(case.run_id, case.run_identity, input_reservation=12, risk_context=case.context)
    with pytest.raises(APIError) as error:
        case.ledger.recover_unknown(dict(status='observer-cannot-prove-provider-finished'))
    assert error.value.code == 'output_dispatch_in_flight'
    saved = case.ledger._read()
    assert saved['state'] == 'dispatching' and saved['pending'] is not None
    assert saved['unknown_windows'] and not (case.batch / 'halt.json').exists()
    assert (case.batch / 'in-flight-unknown.json').is_file()
    saved = settle(case)
    assert saved['state'] == 'blocked' and (case.batch / 'halt.json').is_file()


def test_completed_run_observation_rejects_missing_persisted_input(
        mongo_db, tmp_path, monkeypatch):
    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    case.ledger.begin(case.run_id, case.run_identity, input_reservation=12, risk_context=case.context)
    settle(case)
    case.db.feedback_candidate_generation_inputs.delete_one({'_id': case.run_id})
    with pytest.raises(ValueError):
        case.ledger.require_run_settled(case.run_id, case.run_identity)


def test_complete_two_candidates_settle_170_members_and_block_further_generation(mongo_db, tmp_path, monkeypatch):
    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    for entry in case.manifest['entries']:
        member = entry['member']
        selected = policy(member['candidate_slot'])
        ledger = case.risk.FeedbackCandidateLedger(case.db, selected)
        rid = 'complete-' + member['fixed_slot']
        run = dict(run_id=rid, identity=rid + '-identity', state='awaiting_input')
        case.db.runs.insert_one(run.copy())
        generated = member['expected_generation']
        if generated:
            record = case.risk.input_identity(selected, run, entry)
            case.db.feedback_candidate_generation_inputs.insert_one(dict(record, _id=rid))
        context = dict(case.context, question=entry['question'])
        ledger.begin(rid, run['identity'], input_reservation=12 if generated else 0,
            risk_context=context, zero_generation=not generated)
        if generated:
            ledger.settle(rid, run['identity'], dict(input=12, output=18), completed=True,
                logical_calls=dict(invoke_started=0, stream_started=1),
                product_state=dict(visible_body=True, truncated=False, finish_reason='stop', observed_reasoning=False))
        else:
            ledger.settle_clarification(run, dict(run_id=rid, behavior='clarify', answer=''))
    final = ledger.require_open()
    assert final['state'] == 'awaiting_quality_review'
    assert final['cursor'] == len(final['settled']) == 170
    assert final['provider_stream_reservations'] == 168
    assert final['job_reservations'] == 170
    assert final['pending'] is None and final['unknown_windows'] == []
    assert final['known_new_input_tokens'] == 168 * 12
    assert final['known_new_output_tokens'] == 168 * 18
    with pytest.raises(APIError):
        ledger.begin(rid, run['identity'], input_reservation=12,
            risk_context=context, zero_generation=False)


def test_frozen_clarification_uses_zero_stream_and_advances_shared_cursor(
        mongo_db, tmp_path, monkeypatch):
    case = isolated_case(mongo_db, tmp_path, monkeypatch)
    from app.infrastructure.providers.m6_feedback_candidate_risk import entry_for_execution
    entry = entry_for_execution(case.manifest, 'm6-feedback-stage-r1-v1', 'support-v1-047')
    slot = entry['member']['fixed_slot']
    case.ledger.rows.insert_one(dict(_id=case.ledger.key, manifest_sha256=case.ledger.sha, version=0,
        state='open', pending=None, settled={f'previous-{i}': {} for i in range(46)}, cursor=46,
        prior_input_tokens=0, prior_output_tokens=0, known_new_input_tokens=1000,
        known_new_output_tokens=1000, new_input_tokens=1000, new_output_tokens=1000,
        provider_stream_reservations=46, job_reservations=46, unknown_windows=[],
        exact_http_requests=None, exact_cost=None))
    run_id, identity = 'synthetic-clarification', 'synthetic-clarification-identity'
    case.db.runs.insert_one(dict(run_id=run_id, identity=identity))
    question = entry['question']
    context = case.context | dict(question=question)
    case.ledger.begin(run_id, identity, input_reservation=0, risk_context=context, zero_generation=True)
    saved = case.ledger.settle_clarification(
        dict(run_id=run_id, identity=identity, state='awaiting_input'),
        dict(run_id=run_id, state='awaiting_input', behavior='clarify', answer=''))
    assert saved['state'] == 'open' and saved['cursor'] == 47
    assert saved['provider_stream_reservations'] == 46
    assert saved['settled'][slot]['logical_provider_calls'] == dict(invoke_started=0, stream_started=0)
