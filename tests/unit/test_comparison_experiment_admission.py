import pytest

from app.api.errors import APIError
from app.evaluation.service import EvaluationService


class Repository:
    db = type('Database', (), {'name': 'm6_evaluation_control'})()

    def __init__(self):
        self.created = False

    def get_set(self, *args):
        return {'dataset_sha256': 'a' * 64, 'manifest_sha256': 'b' * 64}

    def create(self, *args, **kwargs):
        self.created = True
        raise AssertionError('unapproved comparison mode must not reserve a run slot')


class Catalog:
    def __init__(self, output_contract):
        self.output_contract = output_contract

    def resolve(self, *args, **kwargs):
        return {
            'dataset_sha256': 'a' * 64,
            'manifest_sha256': 'b' * 64,
            'config': {
                'parameters': {
                    'evidence_attribution': {
                        'comparison_answer': {'enabled': True, 'function_version': 'comparison_answer_v1'}
                    },
                    'answer_budget': {'output_contract': self.output_contract},
                },
            },
        }


def output_contract(*, enabled):
    return {
        'enabled': enabled,
        'function_version': 'diagnostic_total_output_v2',
        'status': 'unknown',
        'endpoint_sha256': 'c' * 64,
        'model': 'qwen3.8-flash',
        'client_versions': {'langchain-openai': '1.1.11', 'openai': '2.28.0'},
        'limit_field': 'max_completion_tokens',
        'semantics': 'unknown',
        'thinking': False,
        'per_request_total_output_tokens': 4096,
        'ledger_id': 'unapproved-comparison',
        'max_total_output_tokens': 4096,
    }


@pytest.mark.parametrize('contract', [
    output_contract(enabled=True),
    output_contract(enabled=False),
    None,
])
def test_comparison_mode_without_scoped_output_admission_is_rejected_before_slot_reservation(contract):
    repo = Repository()
    service = EvaluationService(repo, Catalog(contract))
    with pytest.raises(APIError) as error:
        service.create_experiment(object(), {
            'kb_id': 'kb', 'eval_set_id': 'set', 'eval_set_version': 'v1',
            'config_id': 'comparison', 'config_version': 'r1', 'client_request_id': 'one',
        })
    assert error.value.status == 422
    assert error.value.code == 'comparison_admission_required'
    assert not repo.created


def test_unregistered_comparison_admission_fails_closed_with_public_admission_error():
    contract = output_contract(enabled=True) | {
        'function_version': 'diagnostic_comparison_answer_048_v1',
        'ledger_id': 'm6-comparison-answer-048-r1',
    }
    repo = Repository()
    service = EvaluationService(repo, Catalog(contract))
    with pytest.raises(APIError) as error:
        service.create_experiment(object(), {
            'kb_id': 'kb', 'eval_set_id': 'set', 'eval_set_version': 'v1',
            'config_id': 'comparison', 'config_version': 'r1', 'client_request_id': 'one',
        })
    assert error.value.status == 422
    assert error.value.code == 'comparison_admission_required'
    assert not repo.created


def test_registered_comparison_contract_without_new_git_authorization_is_rejected_before_slot():
    from tests.unit.test_comparison_answer_048_risk import comparison_contract

    repo = Repository()
    service = EvaluationService(repo, Catalog(comparison_contract(enabled=True)))
    with pytest.raises(APIError) as error:
        service.create_experiment(object(), {
            'kb_id': 'kb', 'eval_set_id': 'set', 'eval_set_version': 'v1',
            'config_id': 'comparison', 'config_version': 'r1', 'client_request_id': 'one',
        })
    assert error.value.status == 422
    assert error.value.code == 'comparison_admission_required'
    assert not repo.created


def test_git_evidence_timeout_fails_closed_before_slot(monkeypatch):
    import subprocess
    from app.infrastructure.providers import comparison_answer_048_risk as risk
    from tests.unit.test_comparison_answer_048_risk import comparison_contract

    def timed_out(*args, **kwargs):
        raise subprocess.TimeoutExpired(['git', 'show'], 10)

    monkeypatch.setattr(risk, 'validate_config', timed_out)
    repo = Repository()
    service = EvaluationService(repo, Catalog(comparison_contract(enabled=True)))
    with pytest.raises(APIError) as error:
        service.create_experiment(object(), {
            'kb_id': 'kb', 'eval_set_id': 'set', 'eval_set_version': 'v1',
            'config_id': 'comparison', 'config_version': 'r1', 'client_request_id': 'one',
        })
    assert error.value.status == 422
    assert error.value.code == 'comparison_admission_required'
    assert not repo.created
