"""完整候选账本必须把两个候选版本映射到唯一的170个题级槽。"""
from app.infrastructure.providers.m6_feedback_candidate_risk import (
    validate_full_dispatch,
    entry_for_execution,
)


def manifest():
    entries = []
    order = []
    for version in (1, 2):
        for ordinal in range(1, 86):
            question_id = ("m6-g540-20-a" if ordinal == 40 else f"support-v1-{ordinal:03}")
            slot = f"m6-feedback-stage-r1-v{version}-{question_id}"
            order.append(slot)
            entries.append({
                "member": {
                    "candidate_slot": f"m6-feedback-stage-r1-v{version}",
                    "fixed_slot": slot,
                    "version": version,
                    "ordinal": ordinal,
                    "question_id": question_id,
                    "split": "dev",
                    "route": ("clarify" if question_id == "support-v1-047" else
                              "compare" if question_id == "support-v1-048" else
                              "series" if question_id == "m6-g540-20-a" else "answer"),
                    "expected_generation": question_id != "support-v1-047",
                    "max_provider_streams": int(question_id != "support-v1-047"),
                }
            })
    return {
        "dispatch_order": order,
        "entries": entries,
        "expected_members": 170,
        "expected_generated_members": 168,
        "expected_clarifications": 2,
    }


def test_full_dispatch_binds_each_question_to_its_single_versioned_slot():
    value = manifest()
    assert validate_full_dispatch(value) == value
    assert entry_for_execution(value, "m6-feedback-stage-r1-v2", "support-v1-048") == value["entries"][132]


def test_full_dispatch_rejects_shortened_or_reordered_members():
    value = manifest()
    value["entries"].pop()
    with __import__("pytest").raises(ValueError):
        validate_full_dispatch(value)

    value = manifest()
    value["dispatch_order"][0], value["dispatch_order"][1] = value["dispatch_order"][1], value["dispatch_order"][0]
    with __import__("pytest").raises(ValueError):
        validate_full_dispatch(value)


def test_full_dispatch_rejects_generation_drift_for_the_two_clarifications():
    value = manifest()
    value["entries"][46]["member"]["expected_generation"] = True
    value["entries"][46]["member"]["max_provider_streams"] = 1
    with __import__("pytest").raises(ValueError):
        validate_full_dispatch(value)


def test_run_cannot_claim_a_question_from_the_other_candidate_or_a_heldout_slot():
    value = manifest()
    with __import__("pytest").raises(ValueError):
        entry_for_execution(value, "m6-feedback-stage-r1-v1", "support-v1-048", version=2)
    with __import__("pytest").raises(ValueError):
        entry_for_execution(value, "m6-feedback-stage-r1-v1", "support-v1-086")


def test_evaluation_adapter_recognizes_only_the_frozen_candidate_clarification(monkeypatch):
    from app.evaluation.query_adapter import candidate_zero_generation
    from app.infrastructure.providers import m6_feedback_candidate_risk as risk
    from types import SimpleNamespace

    monkeypatch.setattr(risk, "expected_generation", lambda policy, question: question["id"] != "support-v1-047")
    policy = SimpleNamespace(enabled=True, function_version=risk.VERSION)
    assert candidate_zero_generation(policy, {"id": "support-v1-047"})
    assert not candidate_zero_generation(policy, {"id": "support-v1-048"})


def test_prepare_manifest_rejects_a_different_170_member_body_before_writing(tmp_path, monkeypatch):
    import copy
    import hashlib
    import json
    from app.infrastructure.providers import m6_feedback_candidate_risk as risk
    from app.knowledge.repository import fingerprint

    approved = manifest()
    approved.update(version=risk.VERSION, batch_slot=risk.BATCH,
        authorization_path=risk.AUTHORIZATION_PATH,
        shared_control_database="m1_test_m4_control")
    approved_path = tmp_path / "output" / "approved-inputs.json"
    approved_path.parent.mkdir(parents=True)
    approved_path.write_text(json.dumps(approved), encoding="utf-8")
    auth = dict(kind="coordinator_scoped_m6_feedback_candidates_authorization",
        status="authorized_for_two_complete_dev_candidates", admission_version=risk.VERSION,
        fixed_batch_slot=risk.BATCH, candidate_slots=list(risk.CANDIDATE_SLOTS),
        max_provider_streams=168, new_input_budget=4773888, new_output_budget=688128,
        stop_on_first_failure=True, sdk_max_retries=0, heldout_selected=0,
        old_43_question_batch_started=False, m7_started=False,
        production_manifest=dict(path="output/approved-inputs.json",
            sha256=hashlib.sha256(approved_path.read_bytes()).hexdigest()),
        production_manifest_sha256=fingerprint(approved))
    monkeypatch.setattr(risk, "ROOT", tmp_path)
    monkeypatch.setattr(risk, "AUTHORIZED_GIT", dict(commit='a'*40, path=risk.AUTHORIZATION_PATH, sha256='b'*64))
    monkeypatch.setattr(risk, "evidence_bytes", lambda _: json.dumps(auth).encode())
    forged = copy.deepcopy(approved)
    forged["production_input_manifest_sha256"] = "f" * 64
    with __import__("pytest").raises(ValueError):
        risk.prepare_manifest(forged)
    assert not (tmp_path / "output" / risk.BATCH).exists()


def test_candidate_contract_enables_reasoning_mode_observation():
    from app.query_process.agent.nodes.node_answer_output import observes_reasoning_mode
    assert observes_reasoning_mode({"function_version": "diagnostic_feedback_candidate_manifest_r1"})


def test_candidate_contract_binds_endpoint_runtime_and_all_budget_dimensions():
    import copy
    from app.infrastructure.providers.m6_feedback_candidate_risk import validate_contract_profile
    from tests.unit.test_m6_feedback_candidate_contract import contract
    from app.infrastructure.providers.output_contract import parse_contract

    value = contract()
    policy = parse_contract(value)
    auth = dict(runtime=dict(n=1, model='qwen3.8-flash', endpoint_sha256='a' * 64,
        client_versions={'openai': '2.28.0', 'langchain-openai': '1.1.11'},
        limit_field='max_completion_tokens', requested_total_output_tokens=4096,
        thinking=False, temperature=0.1, timeout_seconds=120, sdk_max_retries=0, stream=True),
        budget=dict(context_window=32768, output_tokens_requested=4096, reserve_tokens=256,
            max_chars=12000, single_input_limit=28416, max_new_product_streams=168,
            max_members=170, max_attempts_per_member=1))
    validate_contract_profile(policy, auth)
    bad = copy.deepcopy(auth)
    bad['runtime']['endpoint_sha256'] = 'c' * 64
    with __import__('pytest').raises(ValueError):
        validate_contract_profile(policy, bad)


def test_zero_provider_call_guard_detects_hidden_retrieval_or_answer_calls():
    from app.evaluation.query_adapter import require_zero_provider_calls
    zero = dict(invoke_started=3, stream_started=4)
    assert require_zero_provider_calls(zero, dict(zero)) is True
    with __import__('pytest').raises(ValueError):
        require_zero_provider_calls(zero, dict(invoke_started=3, stream_started=5))


def test_candidate_catalog_defaults_to_the_bound_full_dev_id_list():
    from app.infrastructure.providers.m6_feedback_candidate_risk import validate_question_scope
    expected = [f'q{i:03}' for i in range(85)]
    assert validate_question_scope({}, dict(question_ids=expected)) == expected
    with __import__('pytest').raises(ValueError):
        validate_question_scope({'question_ids': expected[:84]}, dict(question_ids=expected))


def test_full_dev_order_prioritizes_comparison_without_shortening_the_scope():
    from app.evaluation.runner import select_questions
    rows = [{'id': 'a', 'split': 'dev'}, {'id': 'b', 'split': 'dev'}, {'id': 'c', 'split': 'heldout'}]
    assert [q['id'] for q in select_questions(rows, {'split': 'dev', 'dev_question_order': ['b', 'a']})] == ['b', 'a']
    with __import__('pytest').raises(ValueError):
        select_questions(rows, {'split': 'dev', 'dev_question_order': ['b']})


def test_admission_rejects_changed_request_identity_before_creating_a_job(monkeypatch):
    from app.infrastructure.providers import m6_feedback_candidate_risk as risk
    from types import SimpleNamespace
    approved = dict(kb_id='k', client_request_id='fixed-request', config_id='fixed-config')
    config = {'parameters': {'answer_budget': {'output_contract':
        {'admission': {'member_slot': 'm6-feedback-stage-r1-v1'}}}}}
    monkeypatch.setattr(risk, 'require', lambda _: dict(candidate_versions=[
        dict(candidate_slot='m6-feedback-stage-r1-v1', request=approved)]))
    monkeypatch.setattr('app.infrastructure.providers.output_contract.parse_contract',
        lambda _: SimpleNamespace(admission=SimpleNamespace(member_slot='m6-feedback-stage-r1-v1')))
    risk.validate_request(config, approved)
    with __import__('pytest').raises(ValueError):
        risk.validate_request(config, approved | {'client_request_id': 'second-budget'})


def test_technical_review_must_be_independent_closed_and_cover_current_code(monkeypatch):
    import json
    from app.infrastructure.providers import m6_feedback_candidate_risk as risk
    from app.infrastructure.providers import product_risk
    import pytest
    ref = dict(commit='a' * 40, path='docs/development/reviews/M6-feedback-candidate-independent-review-r1.json', sha256='b' * 64)
    report = dict(kind='m6_feedback_candidate_independent_technical_review',
        final_technical_review='passed_with_specific_boundaries', implementation_participation=False,
        open_findings=[], source_code_sha256='c' * 64)
    monkeypatch.setattr(product_risk, 'code_version', lambda: 'c' * 64)
    monkeypatch.setattr(risk, 'evidence_bytes', lambda actual: json.dumps(report).encode() if actual == ref else b'{}')
    auth = dict(independent_technical_review=ref)
    assert risk.validate_technical_review(auth) == report
    for key, value in [('source_code_sha256', 'd' * 64), ('implementation_participation', True),
            ('open_findings', ['unresolved']), ('final_technical_review', 'open'), ('kind', 'old_report')]:
        previous = report[key]
        report[key] = value
        with pytest.raises(ValueError):
            risk.validate_technical_review(auth)
        report[key] = previous
    with pytest.raises(ValueError):
        risk.validate_technical_review({})
