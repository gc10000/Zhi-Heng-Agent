"""来源约束比较答复正式Run接线；仅使用随机隔离Mongo与合成模型。"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.evaluation.jobs import execute_job
from app.identity.models import Principal
from app.knowledge.api import ProductInput
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_split_ledger import formal_case
from tests.integration.test_combination_adapter import configure

pytestmark = pytest.mark.integration


def setup(ctx, tmp_path, monkeypatch, *, separate, raw=None, interrupted=False,
          question_text=None, no_evidence=False):
    cfg, _, resources, prompts, question, _ = ctx
    g = resources['knowledge']()
    user = Principal(user_id=cfg['target']['owner_id'], username='比较隔离验证',
        role='maintainer', kb_ids=(cfg['target']['kb_id'],))
    product = g.add_product(user, cfg['target']['kb_id'], ProductInput(
        kb_id=cfg['target']['kb_id'], model='BX'))

    combo = configure(ctx)
    products = sorted({*combo['scope']['product_ids'], product['product_id']})
    combo['scope']['product_ids'] = products
    cfg['parameters']['source_prerequisites']['scope']['product_ids'] = products
    snapshot = cfg['corpus']['snapshot']
    policy = dict(enabled=True, function_version='attributed_assertions_v1',
        scope=deepcopy(combo['scope']), corpus_snapshot_sha256=combo['corpus_snapshot_sha256'],
        documents=[{key: doc[key] for key in ('document_id','revision_id','original_sha256')}
            for doc in snapshot['documents']],
        products={p['product_id']: p['model'] for p in snapshot['products']})
    policy['source_relations'] = dict(enabled=True, function_version='source_relation_spans_v1',
        frozen_payloads={c['chunk_uid']: c['payload_sha256']
            for d in snapshot['documents'] for c in d['chunks']})
    policy['comparison_answer'] = dict(enabled=True, function_version='comparison_answer_v1')
    cfg['parameters']['evidence_attribution'] = policy

    from app.retrieval.adapters import score_record
    index = g.index_factory()
    ax_id = g.products.collection.find_one({'model':'AX'})['product_id']
    entity = index.search(None, None, branch_retention=True, product_ids=[ax_id])[0]['entity']

    class ComparisonIndex:
        collection = index.collection
        payload = staticmethod(index.payload)

        def search(self, repo, query, **kwargs):
            if no_evidence or kwargs['product_ids'] != [ax_id]:
                return []
            return [dict(entity=deepcopy(entity), retrieval_trace=[
                score_record('dense', 1, .8, 'inner_product'),
                score_record('learned_sparse', 1, .6, 'inner_product'),
                score_record('weighted_fusion', 1, 1.4, 'milvus_weighted_ip')])]

        def revision_rows(self, *args, **kwargs):
            return index.revision_rows(*args, **kwargs)

        def prerequisite_rows(self, *args, **kwargs):
            return index.prerequisite_rows(*args, **kwargs)

    g.index_factory = ComparisonIndex
    runner = resources['query_runner']
    runner.ranker = lambda _question, docs: [
        doc | {'score': 1.0 - i * .1} for i, doc in enumerate(docs)]
    embedding_calls = []
    def synthetic_embedder(texts):
        embedding_calls.append(len(texts))
        return {'dense': [[1.0, 0.0] for _ in texts], 'sparse': [{1: .5} for _ in texts]}
    runner.embedder = synthetic_embedder
    resources['synthetic_embedding_calls'] = embedding_calls

    question.update(question=question_text or '比较AX与BX的上联方式是否相同？请分别引用资料比较。',
        product_names=['AX', 'BX'])

    class Model:
        def stream(self, prompt, **kwargs):
            prompts.append(prompt)
            yield SimpleNamespace(content=raw or
                '{"schema_version":"comparison_frame_selection_v1","frames":[{"reference":1,"frame":0}]}',
                response_metadata={'finish_reason':'stop'})
            if interrupted:
                raise TimeoutError('synthetic comparison stream interruption')

    resources['query_runner'].llm_factory = Model
    case = formal_case(ctx, tmp_path, monkeypatch, separate=separate)
    # This suite exercises answer wiring with a synthetic model. The production
    # admission gate is covered separately; create only isolated synthetic jobs
    # through the repository so these wiring tests don't claim live admission.
    _, _, _, _, repo, service, _, _, catalog = case
    def create_synthetic_experiment(user, data):
        descriptor = repo.get_set(user, data['kb_id'], data['eval_set_id'], data['eval_set_version'])
        resolved = catalog.resolve(data['eval_set_id'], data['eval_set_version'],
            data['config_id'], data['config_version'], kb_id=data['kb_id'])
        return repo.create(user, data, descriptor=descriptor, resolved=resolved)
    monkeypatch.setattr(service, 'create_experiment', create_synthetic_experiment)
    return case


@pytest.mark.parametrize('separate', [False, True])
def test_formal_comparison_persists_complete_answer_and_reuses_one_selection(
        evaluation_context, tmp_path, monkeypatch, separate):
    cfg, resources, prompts, question, repo, service, user, data, catalog = setup(
        evaluation_context, tmp_path, monkeypatch, separate=separate)
    for key in ('first', 'reuse'):
        job = service.create_experiment(user, data | {'client_request_id': key})
        execute_job(repo, catalog, tmp_path / key, job['experiment_id'])
        assert repo.get_experiment(user, job['experiment_id'])['state'] == 'completed'
        result = repo.results.find_one({'experiment_id':job['experiment_id']})['result']
        assert result['comparison_summary']['comparison_status'] == 'insufficient_comparison'
        assert set(result['comparison_summary']) == {
            'function_version', 'comparison_target', 'comparison_status', 'answer_sha256'}
        assert '现有证据不足以判断' in result['answer']
        assert 'AX' in result['answer'] and 'BX' in result['answer']
        assert 'comparison_frame_selection_v1' not in result['answer']
    row = resources['db'].runs.find_one({})
    assert row['comparison_answer']['raw_selection'].startswith('{"schema_version"')
    assert row['comparison_target'] == 'device_uplink'
    assert len(prompts) == 1 and resources['db'].runs.count_documents({}) == 1
    assert resources['synthetic_embedding_calls'] == []
    events = list(resources['db'].run_events.find({'run_id':row['run_id']}, {'payload':1}))
    assert 'comparison_frame_selection_v1' not in str(events)
    if separate:
        assert repo.db.runs.count_documents({}) == repo.db.evaluation_execution_links.count_documents({}) == 0


@pytest.mark.parametrize('separate', [False, True])
def test_interrupted_comparison_selection_is_bounded_persisted_and_never_leaks(
        evaluation_context, tmp_path, monkeypatch, separate):
    cfg, resources, prompts, question, repo, service, user, data, catalog = setup(
        evaluation_context, tmp_path, monkeypatch, separate=separate,
        raw='{"schema_version":"comparison_frame_selection_v1",', interrupted=True)
    job = service.create_experiment(user, data)
    execute_job(repo, catalog, tmp_path / 'failed', job['experiment_id'])
    assert repo.get_experiment(user, job['experiment_id'])['state'] == 'failed'
    row = resources['db'].runs.find_one({})
    assert row['state'] == 'failed'
    assert row['comparison_answer_failure']['raw_selection'] == '{"schema_version":"comparison_frame_selection_v1",'
    assert row['comparison_answer_failure']['failure_code'] == 'answer_generation_interrupted'
    assert row['telemetry']['token_usage'] == {'input': None, 'output': None}
    assert not row.get('answer') and not row.get('completion_snapshot')
    assert resources['db'].evaluation_outcomes.count_documents({}) == 0
    events = list(resources['db'].run_events.find({'run_id':row['run_id']}, {'payload':1}))
    assert 'comparison_frame_selection_v1' not in str(events)
    assert len(prompts) == 1


def test_unresolved_comparison_target_returns_clarification_without_generation(
        evaluation_context, tmp_path, monkeypatch):
    cfg, resources, prompts, question, repo, service, user, data, catalog = setup(
        evaluation_context, tmp_path, monkeypatch, separate=False,
        question_text='比较AX与BX的功能差异')
    job = service.create_experiment(user, data)
    execute_job(repo, catalog, tmp_path / 'clarification', job['experiment_id'])
    assert repo.get_experiment(user, job['experiment_id'])['state'] == 'completed'
    result = repo.results.find_one({'experiment_id':job['experiment_id']})['result']
    assert result['answer'] == '请明确需要比较两台设备的哪一项信息。'
    assert prompts == [] and resources['synthetic_embedding_calls'] == []
    run = resources['db'].runs.find_one({})
    assert run['comparison_target'] is None
    assert run['comparison_target_reason'] == 'unsupported_or_missing_target'
    assert not run.get('comparison_answer')


def test_empty_frame_catalog_returns_cited_insufficiency_without_generation(
        evaluation_context, tmp_path, monkeypatch):
    cfg, resources, prompts, question, repo, service, user, data, catalog = setup(
        evaluation_context, tmp_path, monkeypatch, separate=False, no_evidence=True)
    job = service.create_experiment(user, data)
    execute_job(repo, catalog, tmp_path / 'empty', job['experiment_id'])
    assert repo.get_experiment(user, job['experiment_id'])['state'] == 'completed'
    result = repo.results.find_one({'experiment_id':job['experiment_id']})['result']
    assert result['comparison_summary']['comparison_status'] == 'insufficient_comparison'
    assert 'AX' in result['answer'] and 'BX' in result['answer']
    assert result['citations'] == [] and prompts == []
    run = resources['db'].runs.find_one({})
    assert run['comparison_answer']['selected_frames'] == []
    assert resources['synthetic_embedding_calls'] == []


def test_invalid_complete_selection_fails_without_answer_delta_or_outcome(
        evaluation_context, tmp_path, monkeypatch):
    cfg, resources, prompts, question, repo, service, user, data, catalog = setup(
        evaluation_context, tmp_path, monkeypatch, separate=False, raw='not-json')
    job = service.create_experiment(user, data)
    execute_job(repo, catalog, tmp_path / 'invalid', job['experiment_id'])
    assert repo.get_experiment(user, job['experiment_id'])['state'] == 'failed'
    run = resources['db'].runs.find_one({})
    assert run['error']['code'] == 'comparison_selection_invalid'
    assert run['comparison_answer_failure']['raw_selection'] == 'not-json'
    assert not run.get('answer') and not run.get('completion_snapshot')
    assert resources['db'].evaluation_outcomes.count_documents({}) == 0
    events = list(resources['db'].run_events.find({'run_id':run['run_id']}, {'payload':1}))
    assert 'not-json' not in str(events) and len(prompts) == 1
