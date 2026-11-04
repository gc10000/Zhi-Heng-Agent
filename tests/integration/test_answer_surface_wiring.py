"""来源关系回答的正式失败/恢复出口；模型合成，不评真实质量。"""
from types import SimpleNamespace

import pytest

from app.evaluation.jobs import execute_job
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_split_ledger import formal_case
from tests.integration.test_source_relation_wiring import configure
from tests.integration.test_candidate_evidence_quality_fix import attribution_config

pytestmark = pytest.mark.integration


def test_frozen_clarification_roundtrips_through_mongo_and_rejects_body_drift(mongo_db):
    from app.evaluation.repository import EvaluationRepository
    from app.evaluation.result_presentation import clarification_presentation_snapshot

    repo = EvaluationRepository(mongo_db)
    candidates = [dict(product_id='p', model='合成型号')]
    snapshot = clarification_presentation_snapshot(candidates,
        [dict(product_id='p', model='合成型号', series='合成系列')])
    repo.save_results('synthetic-presentation', 1,
        [dict(id='q', category='clarification', question='合成问题')],
        [dict(id='q', status='completed', result=dict(
            state='awaiting_input', behavior='clarify', candidates=candidates,
            presentation_snapshot=snapshot))])
    page = repo.results_page('synthetic-presentation', attempt=1)
    assert page['items'][0]['result']['presentation_snapshot'] == snapshot
    mongo_db.evaluation_results.update_one({'experiment_id': 'synthetic-presentation'},
        {'$set': {'result.presentation_snapshot.review.body': '合成篡改'}})
    with pytest.raises(ValueError, match='澄清呈现快照哈希不匹配'):
        repo.results_page('synthetic-presentation', attempt=1)


@pytest.mark.parametrize('separate', [False, True])
def test_internal_rule_leak_fails_without_visible_answer_and_recovery_never_regenerates(
        evaluation_context, tmp_path, monkeypatch, separate):
    configure(evaluation_context, monkeypatch, attribution_config)
    cfg, resources, prompts, question, repo, service, user, data, catalog = formal_case(
        evaluation_context, tmp_path, monkeypatch, separate=separate)

    class Model:
        def stream(self, prompt, **kwargs):
            prompts.append(prompt)
            yield SimpleNamespace(content='根据合同第', response_metadata={})
            yield SimpleNamespace(content='7条，不能判断现场。', response_metadata={'finish_reason': 'stop'})

    resources['query_runner'].llm_factory = lambda: resources['provider_counts'].wrap(Model())
    for request in ('first', 'observe'):
        job = service.create_experiment(user, data | dict(client_request_id=request))
        execute_job(repo, catalog, tmp_path/request, job['experiment_id'])
        assert repo.get_experiment(user, job['experiment_id'])['state'] == 'failed'

    row = resources['db'].runs.find_one({})
    assert row['state'] == 'failed' and row['error']['code'] == 'answer_internal_rule_leak'
    assert row['error'].get('retryable') is not True
    assert row['answer_surface_failure']['failure_code'] == 'internal_rule_leak'
    assert '合同第7条' not in str(row['answer_surface_failure'])
    assert not row.get('answer') and not row.get('completion_snapshot')
    events = list(resources['db'].run_events.find({'run_id': row['run_id']}))
    assert not any(event.get('type') == 'answer.delta' for event in events)
    assert len(prompts) == 1 and resources['db'].runs.count_documents({}) == 1
    assert resources['db'].evaluation_outcomes.count_documents({}) == 0
