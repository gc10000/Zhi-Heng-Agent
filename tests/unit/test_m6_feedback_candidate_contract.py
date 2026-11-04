"""两版完整反馈候选合同必须固定范围并保持关闭到授权清单齐备。"""
from copy import deepcopy

import pytest
from pydantic import ValidationError

from app.infrastructure.providers.output_contract import (
    FEEDBACK_CANDIDATE_VERSION,
    FeedbackCandidateContract,
    is_product_risk,
    parse_contract,
)


def contract():
    return dict(
        enabled=False,
        function_version=FEEDBACK_CANDIDATE_VERSION,
        n=1,
        status='unknown',
        endpoint_sha256='a'*64,
        model='qwen3.8-flash',
        client_versions={'openai':'2.28.0','langchain-openai':'1.1.11'},
        limit_field='max_completion_tokens',
        semantics='unknown',
        thinking=False,
        reasoning_budget=None,
        per_request_total_output_tokens=4096,
        ledger_id='m6-feedback-candidate-full-r1',
        max_total_input_tokens=4773888,
        max_total_output_tokens=688128,
        admission=None,
    )


def test_full_candidate_contract_is_risk_only_when_explicitly_authorized():
    value=parse_contract(contract())
    assert isinstance(value,FeedbackCandidateContract)
    assert value.admission is None
    assert not value.enabled
    assert not is_product_risk(value)


@pytest.mark.parametrize('change',[
    {'model':'other'}, {'n':2}, {'thinking':True}, {'limit_field':'max_tokens'},
    {'per_request_total_output_tokens':4095}, {'max_total_input_tokens':4773887},
    {'max_total_output_tokens':688127}, {'ledger_id':'old-048-ledger'},
])
def test_full_candidate_contract_rejects_profile_or_budget_drift(change):
    value=contract()|change
    with pytest.raises(ValidationError):parse_contract(value)


def test_full_candidate_contract_rejects_old_single_question_or_wrong_scope_slot():
    value=contract()
    value['admission']={'authorization':dict(commit='a'*40,path='docs/reviews/auth.json',sha256='b'*64),
                        'manifest_sha256':'c'*64,'member_slot':'m6-connection-comparison-048-r2-support-v1-048'}
    with pytest.raises(ValidationError):parse_contract(value)


def test_full_candidate_contract_enabled_requires_a_manifest_admission():
    with pytest.raises(ValidationError):parse_contract(contract()|{'enabled':True})


def test_answer_budget_preserves_the_full_candidate_contract_type():
    from app.answering.service import AnswerBudget
    value = contract() | {
        'enabled': True,
        'admission': {
            'authorization': dict(commit='a'*40,
                path='docs/development/reviews/M6-feedback-stage-authorization-r1.json',
                sha256='b'*64),
            'manifest_sha256': 'c'*64,
            'member_slot': 'm6-feedback-stage-r1-v1',
        },
    }
    budget = AnswerBudget.model_validate(dict(output_tokens=4096,
        output_token_field='max_completion_tokens', output_contract=value))
    assert isinstance(budget.output_contract, FeedbackCandidateContract)


def test_service_accepts_full_candidate_only_after_its_own_manifest_validator(monkeypatch):
    from app.api.errors import APIError
    from app.evaluation.service import EvaluationService
    from app.infrastructure.providers import m6_feedback_candidate_risk as risk
    from tests.unit.test_comparison_experiment_admission import Repository, Catalog

    authorized = contract() | {
        'enabled': True,
        'admission': {
            'authorization': {
                'commit': 'a' * 40,
                'path': 'docs/development/reviews/M6-feedback-stage-authorization-r1.json',
                'sha256': 'b' * 64,
            },
            'manifest_sha256': 'c' * 64,
            'member_slot': 'm6-feedback-stage-r1-v1',
        },
    }
    catalog = Catalog(authorized)
    resolve = catalog.resolve

    def candidate_config(*args, **kwargs):
        value = resolve(*args, **kwargs)
        value['config']['parameters']['evidence_attribution']['comparison_answer'].update(
            enabled=True, function_version='connection_comparison_v1')
        return value

    catalog.resolve = candidate_config
    repo = Repository()

    def validate(config, database):
        raise APIError(409, 'candidate_manifest_reached', '已进入全范围专属清单验证器。')

    monkeypatch.setattr(risk, 'validate_config', validate, raising=False)
    with pytest.raises(APIError) as error:
        EvaluationService(repo, catalog).create_experiment(object(), dict(
            kb_id='kb', eval_set_id='set', eval_set_version='v1',
            config_id='new', config_version='r1', client_request_id='one'))
    assert error.value.code == 'candidate_manifest_reached'
    assert not repo.created
