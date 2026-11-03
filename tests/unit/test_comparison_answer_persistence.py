from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.answering.comparison_answers import (
    bind_comparison_response, build_frame_catalog, prompt_used_identity,
)
from app.answering.evidence_attribution import EvidenceAttributionPolicy, evidence_labels, payload
from app.answering.service import AnswerBudget
from app.knowledge.repository import fingerprint
from app.evaluation.query_adapter import RealQueryExecutor
from app.retrieval.models import QueryPlan
from app.runs.query_runner import QueryRunner
from tests.unit.test_comparison_answers import _frozen_inputs


@pytest.mark.parametrize('version',[None,'comparison_answer_v1','comparison_answer_v2',
    'comparison_answer_v3','connection_comparison_v1'])
def test_finish_reason_identity_is_added_only_for_explicit_connection_mode(version):
    from app.evaluation.execution_identity import run_output
    row={'answer_finish_reason':'stop'}
    if version:
        row['evidence_attribution']={'comparison_answer':{'enabled':True,'function_version':version}}
    expected={'answer_finish_reason':'stop'} if version=='connection_comparison_v1' else {}
    assert run_output(row)==expected


def _projector_fixture(version='comparison_answer_v1'):
    text = '本设备上联通过以太网连接到核心网。'
    policy, doc, _ = _frozen_inputs(text)
    policy['products']['q'] = '另一合成网关'
    policy['scope']['product_ids'].append('q')
    policy['comparison_answer']['function_version'] = version
    policy = payload(policy)
    parsed = EvidenceAttributionPolicy.model_validate(policy)
    reference_map = [dict(evidence_labels([doc], parsed)[0], reference_number=1)]
    target = 'device_uplink'
    question = '比较两台合成设备的上联方式。'
    prompt_question = question + '\n\n证据限制：比较只能依据本轮参考内容，未提供某型号证据时必须明确资料不足，不得推断其参数。'
    prompt_hash = prompt_used_identity(prompt_question, reference_map, [doc], target)
    policy_hash = fingerprint(parsed.model_dump(mode='json'))
    raw = '{"schema_version":"comparison_frame_selection_v1","frames":[{"reference":1,"frame":0}]}'
    answer, proof = bind_comparison_response(raw,build_frame_catalog(reference_map, [doc], parsed),
        ['p', 'q'], target, policy_hash, prompt_hash, parsed.products, version=version)
    citation = {key: deepcopy(doc[key]) for key in (
        'chunk_uid', 'document_id', 'revision_id', 'text', 'source_refs', 'asset_ids')}
    row = dict(run_id='synthetic-run', state='completed', answer=answer, citations=[citation], question=question,
        product_snapshot={'product_ids':['p', 'q']}, prompt_reference_map=reference_map,
        prompt_used_docs=[doc], comparison_target=target, comparison_target_reason='explicit_single_target',
        comparison_policy_sha256=policy_hash, comparison_prompt_used_sha256=prompt_hash,
        comparison_answer=proof, query_plan={'route':'compare', 'product_ids':['p','q'], 'comparison_target':target,
            'comparison_target_reason':'explicit_single_target'})

    class Collection:
        def find_one(self, *_args, **_kwargs):
            return None

    class Database:
        knowledge_assets = Collection()
        knowledge_legacy_assets = Collection()

    executor = object.__new__(RealQueryExecutor)
    executor.config = {'parameters': {'evidence_attribution': policy}}
    executor.resources = {'knowledge': lambda: SimpleNamespace(db=Database())}
    executor.documents = {'d': {'revision_id':'r', 'original_sha256':'b' * 64}}
    executor.products = {'合成网关':'p', '另一合成网关':'q'}
    executor.comparison_question = dict(question=question,
        product_names=list(executor.products), history=[])
    return executor, row


@pytest.mark.parametrize('version', ['comparison_answer_v1','comparison_answer_v2','comparison_answer_v3'])
def test_first_projection_recomputes_comparison_and_exposes_only_sanitized_summary(version):
    executor, row = _projector_fixture(version)
    result = executor.project_result(row,question=executor.comparison_question)
    assert result['comparison_summary']['comparison_status'] == 'insufficient_comparison'
    assert 'raw_selection' not in result['comparison_summary']
    assert 'comparison_frame_selection_v1' not in result['answer']
    assert result['comparison_summary']['function_version'] == version


def test_first_projection_rejects_coordinated_old_proof_under_new_policy():
    executor, row = _projector_fixture('comparison_answer_v2')
    policy = executor.config['parameters']['evidence_attribution']
    old_answer, old_proof = bind_comparison_response(row['comparison_answer']['raw_selection'],
        build_frame_catalog(row['prompt_reference_map'], row['prompt_used_docs'], policy),
        ['p','q'], row['comparison_target'], row['comparison_policy_sha256'],
        row['comparison_prompt_used_sha256'], policy['products'])
    row.update(answer=old_answer, comparison_answer=old_proof)
    with pytest.raises(ValueError):
        executor.project_result(row,question=executor.comparison_question)


def test_first_projection_rejects_coordinated_saved_source_rewrite():
    executor, row = _projector_fixture()
    changed = deepcopy(row)
    text = '本设备上联通过同轴连接到核心网。'
    changed['prompt_used_docs'][0]['text'] = text
    changed['citations'][0]['text'] = text
    with pytest.raises(ValueError):
        executor.project_result(changed,question=executor.comparison_question)


def test_first_projection_rejects_removed_comparison_identity_and_proof():
    executor, row = _projector_fixture()
    changed = deepcopy(row)
    changed.pop('comparison_target')
    changed.pop('comparison_target_reason')
    changed.pop('comparison_answer')
    changed.pop('comparison_policy_sha256')
    changed.pop('comparison_prompt_used_sha256')
    changed['answer'] = '两台设备的上联方式相同。'
    with pytest.raises(ValueError):
        executor.project_result(changed,question=executor.comparison_question)


def test_first_projection_rejects_coordinated_route_and_target_downgrade():
    executor, row = _projector_fixture()
    changed = deepcopy(row)
    changed.pop('comparison_answer')
    changed.pop('comparison_policy_sha256')
    changed.pop('comparison_prompt_used_sha256')
    changed['comparison_target'] = None
    changed['comparison_target_reason'] = 'not_comparison'
    changed['query_plan'] = {'route': 'answer', 'comparison_target': None,
        'comparison_target_reason': 'not_comparison'}
    changed['answer'] = '两台设备的上联方式相同。'
    with pytest.raises(ValueError):
        executor.project_result(changed,question=executor.comparison_question)


def test_run_output_identity_includes_comparison_proof_and_failure():
    from app.evaluation.execution_identity import run_input,run_output
    value = {'state':'failed', 'comparison_target':'device_uplink',
        'comparison_target_reason':'explicit_single_target',
        'comparison_answer_failure':{'failure_code':'comparison_selection_rejected'},
        'comparison_answer':{'answer_sha256':'a' * 64}}
    assert run_output(value) == value
    class Cursor(list):
        def sort(self, *_args, **_kwargs): return self
        def limit(self, *_args, **_kwargs): return self
    db=SimpleNamespace(messages=SimpleNamespace(find=lambda *_args,**_kwargs:Cursor()))
    persisted=run_input(value|dict(run_id='r',conversation_id='c',owner_id='o'),db)
    assert persisted['comparison_target']=='device_uplink'
    assert persisted['comparison_target_reason']=='explicit_single_target'


def test_comparison_selection_rejection_has_a_safe_telemetry_code():
    from app.runs.telemetry import SAFE_CODES
    assert 'comparison_selection_invalid' in SAFE_CODES


def test_comparison_failure_record_bounds_raw_selection_and_keeps_input_identity():
    from app.answering.comparison_answers import comparison_failure_record
    executor, _ = _projector_fixture()
    policy = executor.config['parameters']['evidence_attribution']
    record = comparison_failure_record('x' * 5000, 'synthetic prompt', [], policy,
        'comparison_selection_rejected')
    assert len(record['raw_selection']) == 4096
    assert record['received_chars'] == 5000
    assert len(record['input_sha256']) == 64


def test_query_plan_comparison_identity_is_deterministic_and_scoped():
    from app.retrieval.query_planner import plan_query,comparison_target_identity
    products=[dict(product_id='p',model='合成网关'),dict(product_id='q',model='另一合成网关')]
    compare=plan_query('比较合成网关与另一合成网关的上联方式是否相同',products,
        selected_ids=['p','q'])
    assert compare.route=='compare'
    assert comparison_target_identity(compare)==dict(comparison_target='device_uplink',
        comparison_target_reason='explicit_single_target')
    ordinary=plan_query('合成网关上联方式是什么',products,selected_ids=['p'])
    assert comparison_target_identity(ordinary)==dict(comparison_target=None,
        comparison_target_reason='not_comparison')


def test_query_runner_passes_target_and_product_identity_only_on_compare_route(monkeypatch):
    from pathlib import Path
    monkeypatch.setattr('app.core.load_prompt.PROJECT_ROOT', Path(__file__).resolve().parents[2])
    text = '本设备上联通过以太网连接到核心网。'
    policy, doc, _ = _frozen_inputs(text)
    policy['products']['q'] = '另一合成网关'
    policy['scope']['product_ids'].append('q')
    runner = object.__new__(QueryRunner)
    runner.answer_budget = AnswerBudget(context_window=8192, output_tokens=512, reserve_tokens=64)
    runner.evidence_attribution = EvidenceAttributionPolicy.model_validate(policy)
    comparison_plan = QueryPlan(original_query='比较设备上联方式', route='compare',
        product_ids=('p', 'q'), comparison_target='device_uplink',
        comparison_target_reason='explicit_single_target')
    state, prompt = runner.evidence_prompt('比较设备上联方式', [doc], [], comparison_plan,
        item_names=['合成网关', '另一合成网关'], history=[], session_id='synthetic', product_ids=['p', 'q'])
    assert state['comparison_mode'] is True
    assert state['comparison_target'] == 'device_uplink'
    assert state['comparison_product_ids'] == ['p', 'q']
    assert 'comparison_frame_selection_v1' in prompt

    normal_plan = QueryPlan(original_query='设备上联是什么', route='answer', product_ids=('p',))
    normal_state, normal_prompt = runner.evidence_prompt('设备上联是什么', [doc], [], normal_plan,
        item_names=['合成网关'], history=[], session_id='synthetic', product_ids=['p'])
    assert 'comparison_mode' not in normal_state
    assert 'comparison_frame_selection_v1' not in normal_prompt
