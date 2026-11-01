"""来源跨度策略经正式Run、同/分库job与恢复的合成隔离验证。"""
from copy import deepcopy
import pytest

from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration import test_candidate_evidence_quality_fix as prior
from tests.integration.test_reviewed_subject_wiring import relation_config
from app.answering.evidence_attribution import payload

pytestmark = pytest.mark.integration


def configure(ctx, monkeypatch, base):
    relation_config(ctx, monkeypatch, base)
    cfg = ctx[0]
    p = cfg['parameters']['evidence_attribution']
    p['source_relations'] = dict(enabled=True, function_version='source_relation_spans_v1',
        frozen_payloads={c['chunk_uid']: c['payload_sha256']
                         for d in cfg['corpus']['snapshot']['documents'] for c in d['chunks']})
    return payload(p)


@pytest.mark.parametrize('separate', [False, True])
def test_policy_and_full_span_map_survive_formal_completion_and_reuse(evaluation_context, tmp_path, monkeypatch, separate):
    base = prior.attribution_config
    monkeypatch.setattr(prior, 'attribution_config', lambda ctx: configure(ctx, monkeypatch, base))
    prior.test_formal_attribution_identity_checkpoint_completed_reuse(evaluation_context, tmp_path, monkeypatch, separate)
    row = evaluation_context[2]['db'].runs.find_one({})
    assert row['evidence_attribution']['source_relations']['enabled'] is True
    assert all('source_relations' in r for r in row['prompt_reference_map'])
    assert any(r.get('reviewed_subject', {}).get('subject') == '合成扩展台乙' for r in row['prompt_reference_map'])
    assert 'source_relation_spans_v1' in evaluation_context[3][0]


@pytest.mark.parametrize('separate', [False, True])
@pytest.mark.parametrize('drift', [False, True])
def test_first_snapshot_revalidates_full_input(evaluation_context, tmp_path, monkeypatch, separate, drift):
    base = prior.attribution_config
    monkeypatch.setattr(prior, 'attribution_config', lambda ctx: configure(ctx, monkeypatch, base))
    prior.test_completed_attribution_input_rechecked_before_first_snapshot(evaluation_context, tmp_path, monkeypatch, separate, drift)


@pytest.mark.parametrize('drift', [False, True])
def test_completed_checkpoint_revalidates_full_output_map(evaluation_context, tmp_path, monkeypatch, drift):
    base = prior.attribution_config
    monkeypatch.setattr(prior, 'attribution_config', lambda ctx: configure(ctx, monkeypatch, base))
    prior.test_saved_attribution_checkpoint_rechecks_map_without_generation(evaluation_context, tmp_path, monkeypatch, drift)


@pytest.mark.parametrize('separate', [False, True])
@pytest.mark.parametrize('drift', [False, True])
def test_continuation_keeps_relation_identity_and_does_not_regenerate(evaluation_context, tmp_path, monkeypatch, separate, drift):
    from tests.integration.diagnostic_recovery import continuation_case
    configure(evaluation_context, monkeypatch, prior.attribution_config)
    continuation_case(evaluation_context, tmp_path, monkeypatch, separate=separate, drift=drift,
                      field='evidence_attribution_sha256')


@pytest.mark.parametrize('change', ['missing', 'hash', 'extra', 'source_version'])
def test_self_reported_source_identity_rejected_before_resources(evaluation_context, monkeypatch, change):
    from app.evaluation.query_adapter import RealQueryExecutor
    configure(evaluation_context, monkeypatch, prior.attribution_config)
    cfg = deepcopy(evaluation_context[0])
    p = cfg['parameters']['evidence_attribution']['source_relations']
    if change == 'missing': p['frozen_payloads'].pop(next(iter(p['frozen_payloads'])))
    if change == 'hash': p['frozen_payloads'][next(iter(p['frozen_payloads']))] = 'f' * 64
    if change == 'extra': p['frozen_payloads']['elsewhere'] = 'f' * 64
    if change == 'source_version': p['function_version'] = 'not_reviewed'
    with pytest.raises(ValueError):
        RealQueryExecutor(cfg, resource_factory=lambda _: pytest.fail('非法来源不能装载资源'))
