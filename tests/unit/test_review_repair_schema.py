"""限定补证拒绝隐式分值、越界适用性和空依据。"""
import pytest
from pydantic import ValidationError
from app.evaluation.review_repairs import RepairJudgment, RepairTarget


@pytest.mark.parametrize('value', [True, False, 1.0, '2', -1, 3, None])
def test_repair_rejects_noncanonical_scores(value):
    with pytest.raises(ValidationError):
        RepairJudgment(question_id='q', subject_sha256='a'*64, scores={'citation_support':value},
            dimension_evidence={'citation_support':'依据'}, source_checked=True, critical_errors=[])


@pytest.mark.parametrize('change', [dict(scores={'factuality':'not_applicable'}),
    dict(dimension_evidence={'citation_support':' '}), dict(dimension_evidence={'factuality':'依据'}), dict(passed=True)])
def test_repair_rejects_invalid_evidence(change):
    values=dict(question_id='q', subject_sha256='a'*64, scores={'citation_support':2},
        dimension_evidence={'citation_support':'依据'}, source_checked=True, critical_errors=[])
    with pytest.raises(ValidationError): RepairJudgment(**(values|change))


@pytest.mark.parametrize('change', [dict(replace_dimensions=[]), dict(replace_dimensions=['actionability']),
    dict(replace_dimensions=['factuality','factuality']), dict(correct_actionability_na=True),
    dict(correct_actionability_na=True, actionability_applicable=True), dict(actionability_applicable=False),
    dict(replace_dimensions=['actionability'], correct_actionability_na=True, actionability_applicable=False)])
def test_repair_rejects_implicit_or_overlapping_scope(change):
    values=dict(question_id='q', subject_sha256='a'*64, replace_dimensions=['factuality'], rationale='明确题意')
    with pytest.raises(ValidationError): RepairTarget(**(values|change))


def test_reading_old_reviews_does_not_weaken_current_generation_runtime_check(monkeypatch):
    from app.evaluation.query_adapter import open_evaluation_resources
    monkeypatch.setattr('app.evaluation.versions.runtime_versions', lambda:dict(code='new', prompt='p', model='m'))
    with pytest.raises(ValueError, match='指纹'):
        with open_evaluation_resources(dict(versions=dict(code='old', prompt='p', model='m'))):
            pytest.fail('旧生成配置不得进入新执行资源')
