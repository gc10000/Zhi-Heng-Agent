"""M6-02确定性离线检索指标与报告回归。"""
import copy
import importlib
import importlib.util
import json
import math

import pytest

from app.evaluation.validate_dataset import fingerprint
from tests.unit.test_evaluation_dataset import case, freeze


def metrics_api():
    spec = importlib.util.find_spec('app.evaluation.metrics')
    assert spec is not None, 'M6-02应提供使用允许证据计算排名指标的模块'
    return importlib.import_module('app.evaluation.metrics')


def reviewed(row):
    result = copy.deepcopy(row)
    result['annotation'] = {
        'method': 'independent_assistant_review', 'status': 'reviewed', 'reviewer': 'synthetic-reviewer',
        'review': {'artifact': 'docs/development/reviews/synthetic-review.md', 'artifact_sha256': 'b' * 64,
                   'commit': 'c' * 40, 'method': 'independent_source_audit',
                   'subject_sha256': fingerprint({key: value for key, value in result.items() if key != 'annotation'})}}
    return result


def candidate(name, *sources):
    return {'candidate_id': name, 'sources': list(sources)}


def source(page, document='a' * 64, asset=None):
    value = {'document_sha256': document, 'page': page}
    if asset is not None:
        value['asset_sha256'] = asset
    return value


def gold(page, document='a' * 64, asset=None):
    return dict(source(page, document, asset), quote='允许证据合成引文')


def test_group_recall_mrr_and_group_ndcg_use_required_groups_and_or_alternatives():
    row = case()
    row['allowed_evidence'] = [
        [gold(2), gold(3)],  # 组内是替代来源，不是两个独立目标
        [gold(4, document='d' * 64)],
    ]
    row['source_scope'].append('d' * 64)
    row = reviewed(row)
    result = metrics_api().retrieval_metrics(
        row,
        [candidate('noise', source(8)), candidate('first-group', source(3)),
         candidate('alternative-again', source(2)), candidate('second-group', source(4, document='d' * 64))],
        k_values=(1, 2, 3, 4),
    )

    assert result['label_eligible'] is True
    assert result['recall_at_k'] == {'1': 0.0, '2': 0.5, '3': 0.5, '4': 1.0}
    assert result['mrr'] == 0.5
    assert result['ndcg_at_k']['4'] == pytest.approx(
        (1 / math.log2(3) + 1 / math.log2(5)) / 2)
    assert result['human_answer_correctness'] is None
    single_chunk = metrics_api().retrieval_metrics(
        row, [candidate('covers-both', source(3), source(4, document='d' * 64))], k_values=(1,))
    assert single_chunk['recall_at_k']['1'] == 1.0
    assert single_chunk['mrr'] == 1.0
    assert single_chunk['ndcg_at_k']['1'] == 1.0


def test_unreviewed_candidates_and_no_evidence_questions_do_not_enter_gold_metrics():
    draft = case()
    draft_result = metrics_api().retrieval_metrics(draft, [candidate('hit', source(2))])
    assert draft_result['label_eligible'] is False
    assert draft_result['recall_at_k'] == {'1': None, '5': None, '10': None}
    assert draft_result['mrr'] is None

    no_evidence = case()
    no_evidence['expected']['behavior'] = 'insufficient'
    no_evidence['allowed_evidence'] = []
    no_evidence = reviewed(no_evidence)
    no_evidence_result = metrics_api().retrieval_metrics(no_evidence, [candidate('anything', source(2))])
    assert no_evidence_result['label_eligible'] is True
    assert no_evidence_result['evidence_applicable'] is False
    assert no_evidence_result['recall_at_k'] == {'1': None, '5': None, '10': None}
    assert no_evidence_result['mrr'] is None


def test_ranked_candidate_identity_must_be_unique_and_asset_equivalence_is_exact():
    row = case()
    row['allowed_evidence'] = [[gold(2, asset='b' * 64)]]
    row = reviewed(row)
    api = metrics_api()
    wrong_asset = api.retrieval_metrics(row, [candidate('chunk-a', source(2, asset='c' * 64))])
    assert wrong_asset['recall_at_k']['1'] == 0.0
    mapped_asset = api.retrieval_metrics(
        row, [candidate('chunk-b', source(2, asset='c' * 64))],
        asset_equivalences=[{'document_sha256': 'a' * 64, 'page': 2,
                             'asset_sha256': 'c' * 64, 'expected_asset_sha256': 'b' * 64}],
    )
    assert mapped_asset['recall_at_k']['1'] == 1.0
    with pytest.raises(ValueError, match='身份重复'):
        api.retrieval_metrics(row, [candidate('same', source(9)), candidate('same', source(2))])


def test_runner_persists_seed_and_complete_reproducibility_hashes(tmp_path):
    from app.evaluation.runner import run_experiment

    row = reviewed(case())
    data, manifest, config = freeze(tmp_path, [row])
    config.update(metric_schema_version=1, seed=41, metric_k_values=[1, 2])
    citation = source(2)
    calls = []
    def execute(_):
        calls.append(1)
        return {'answer': '24 V', 'citations': [citation],
                'retrieval_candidates': {
                    'candidates': [candidate('noise', source(8)),
                                   candidate('chunk-1', citation) | {'text': '候选正文不应由指标接线重复持久化'}],
                    'reranked': [candidate('chunk-1', citation)],
                    'context': [candidate('chunk-1', citation)],
                }}

    report = run_experiment(
        data, manifest, config, tmp_path / 'run',
        execute,
    )
    saved = json.loads((tmp_path / 'run' / 'manifest.json').read_text(encoding='utf-8'))

    assert report['status'] == 'completed'
    assert saved['reproducibility']['seed'] == 41
    assert saved['reproducibility']['dataset_sha256'] == config['dataset_sha256']
    assert saved['reproducibility']['split_manifest_sha256'] == saved['split_manifest_sha256']
    assert saved['reproducibility']['config_sha256'] == saved['config_sha256']
    assert saved['reproducibility']['strategy_sha256']
    assert saved['reproducibility']['versions'] == config['versions']
    assert saved['reproducibility_sha256'] == fingerprint(saved['reproducibility'])
    record = json.loads((tmp_path / 'run' / 'results.jsonl').read_text(encoding='utf-8'))
    assert record['metrics']['retrieval']['candidates']['recall_at_k'] == {'1': 0.0, '2': 1.0}
    assert record['metrics']['retrieval']['reranked']['mrr'] == 1.0
    assert record['result']['retrieval_candidates']['candidates'][1] == {
        'candidate_id': 'chunk-1', 'sources': [citation]}
    assert 'text' not in record['result']['retrieval_candidates']['candidates'][1]
    assert report['summary']['retrieval_metric_means']['candidates']['mrr'] == 0.5
    run_experiment(data, manifest, config, tmp_path / 'run', execute)
    assert len(calls) == 1, '成功检查点恢复不能重复执行或重复产生调用'

    saved['reproducibility']['seed'] = 42
    (tmp_path / 'run' / 'manifest.json').write_text(json.dumps(saved), encoding='utf-8')
    with pytest.raises(ValueError, match='复现清单'):
        run_experiment(data, manifest, config, tmp_path / 'run', execute)


def test_m6_runner_rejects_missing_or_invalid_seed_without_breaking_legacy_configs(tmp_path):
    from app.evaluation.runner import check_split

    _, manifest_path, config = freeze(tmp_path, [case()])
    frozen = json.loads(manifest_path.read_text(encoding='utf-8'))
    m6_config = dict(config, metric_schema_version=1)
    with pytest.raises(ValueError, match='seed'):
        check_split(m6_config, frozen)
    with pytest.raises(ValueError, match='seed'):
        check_split(dict(m6_config, seed=True), frozen)
    check_split(config, frozen)  # M4既有配置保持兼容，不能伪造默认seed。


def test_runner_persists_safe_failure_stage_without_exception_message(tmp_path):
    from app.evaluation.runner import run_experiment

    row = reviewed(case())
    data, manifest, config = freeze(tmp_path, [row])
    config.update(metric_schema_version=1, seed=7)

    class RetrievalFailure(RuntimeError):
        stage = 'retrieval'

    def fail(_):
        raise RetrievalFailure('private query, signed URL, and credential must not be persisted')

    report = run_experiment(data, manifest, config, tmp_path / 'failed-run', fail)
    record = json.loads((tmp_path / 'failed-run' / 'results.jsonl').read_text(encoding='utf-8'))
    assert report['summary']['by_failure_stage'] == {'retrieval': 1}
    assert record['failure_stage'] == 'retrieval'
    assert record['error'] == {'type': 'RetrievalFailure', 'code': 'provider_unknown_error', 'retryable': False}
    assert 'private' not in json.dumps(record)


def test_report_summarizes_by_category_failure_stage_and_unknown_cost_separately():
    retrieval = {'label_eligible': True, 'evidence_applicable': True, 'mrr': 1.0,
                 'recall_at_k': {'1': 1.0}, 'ndcg_at_k': {'1': 1.0}}
    summary = metrics_api().summarize_experiment(
        records=[
            {'id': 'q1', 'status': 'completed', 'category': 'parameter',
             'result': {'logical_provider_calls': {'embed': 0, 'rerank': 1},
                        'token_usage': {'input': 0, 'output': 12}},
             'metrics': {'retrieval': retrieval}},
            {'id': 'q2', 'status': 'failed', 'category': 'diagram',
             'failure_stage': 'retrieval', 'error': {'type': 'TimeoutError'},
             'result': {'logical_provider_calls': {}, 'token_usage': {'input': 0, 'output': 0}}},
            {'id': 'q3', 'status': 'failed', 'category': 'parameter',
             'error': {'type': 'RuntimeError'},
             'result': {'logical_provider_calls': {}, 'token_usage': {'input': 0, 'output': 0}}},
        ],
        questions=[case('q1'), dict(case('q2'), category='diagram'), case('q3')],
    )
    assert summary['by_category']['parameter']['selected'] == 2
    assert summary['by_category']['diagram']['failed'] == 1
    assert summary['by_failure_stage'] == {'retrieval': 1, 'unknown': 1}
    assert summary['by_category']['diagram']['accounting']['exact_cost'] is None
    assert summary['accounting']['logical_provider_calls'] == {'embed': 0, 'rerank': 1}
    assert summary['accounting']['input_tokens'] == 0
    assert summary['accounting']['output_tokens'] == 12
    assert summary['accounting']['exact_sdk_http_calls'] is None
    assert summary['accounting']['exact_cost'] is None
    assert summary['retrieval_metric_means']['retrieval']['recall_at_k@1'] == 1.0
    assert summary['by_category']['parameter']['accounting']['logical_provider_calls'] == {
        'embed': 0, 'rerank': 1}

    measured_zero = metrics_api().summarize_experiment(
        records=[{'id': 'q1', 'status': 'completed', 'result': {
            'logical_provider_calls': {'answer': 0}, 'token_usage': {'input': 0, 'output': 0},
            'exact_sdk_http_calls': 0, 'exact_cost': 0, 'currency': 'USD'}}],
        questions=[case('q1')],
    )
    assert measured_zero['accounting']['logical_provider_calls'] == {'answer': 0}
    assert measured_zero['accounting']['input_tokens'] == 0
    assert measured_zero['accounting']['exact_sdk_http_calls'] == 0
    assert measured_zero['accounting']['exact_cost'] == 0


def test_invalid_rank_parameters_fail_closed():
    row = reviewed(case())
    with pytest.raises(ValueError, match='k'):
        metrics_api().retrieval_metrics(row, [], k_values=(1, 1))
    with pytest.raises(ValueError, match='候选'):
        metrics_api().retrieval_metrics(row, [{'candidate_id': 'bad', 'sources': 'not-a-list'}])
    with pytest.raises(ValueError, match='图像对应'):
        metrics_api().retrieval_metrics(row, [], asset_equivalences=['bad-map'])


def test_retrieval_grid_exports_ranked_chunk_identity_and_authorized_source_refs():
    from app.evaluation import retrieval_grid

    class Hit:
        def __init__(self, chunk_uid, page):
            self.document_id = 'doc-1'
            self.revision_id = 'rev-1'
            self.chunk_uid = chunk_uid
            self.metadata = {'source_refs': [{'page': page}], 'asset_ids': []}
            self.identity = (self.document_id, self.revision_id, self.chunk_uid)

    documents = {'doc-1': {'revision_id': 'rev-1', 'original_sha256': 'a' * 64}}
    ranked = retrieval_grid.ranked_source_candidates(
        [Hit('chunk-2', 2), Hit('chunk-1', 1)], documents, {})
    assert ranked == [
        {'candidate_id': '["doc-1","rev-1","chunk-2"]',
         'sources': [{'document_sha256': 'a' * 64, 'page': 2}]},
        {'candidate_id': '["doc-1","rev-1","chunk-1"]',
         'sources': [{'document_sha256': 'a' * 64, 'page': 1}]},
    ]
