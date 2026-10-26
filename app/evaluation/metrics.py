"""M6可追溯检索指标与分层汇总；来源命中不代表答案正确。"""
from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Mapping, Sequence

from .datasets import is_label_eligible


DEFAULT_K = (1, 5, 10)


def _validate_k_values(k_values: Sequence[int]) -> tuple[int, ...]:
    if (not isinstance(k_values, Sequence) or isinstance(k_values, (str, bytes)) or not k_values or
            any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in k_values) or
            len(set(k_values)) != len(k_values)):
        raise ValueError('k必须是非空且不重复的正整数序列')
    return tuple(sorted(k_values))


def _source_matches(expected: Mapping, actual: Mapping, asset_equivalences: Sequence[Mapping]) -> bool:
    if (actual.get('document_sha256') != expected.get('document_sha256') or
            actual.get('page') != expected.get('page')):
        return False
    expected_asset = expected.get('asset_sha256')
    if expected_asset is None or actual.get('asset_sha256') == expected_asset:
        return True
    return any(
        equivalence.get('document_sha256') == expected.get('document_sha256') and
        equivalence.get('page') == expected.get('page') and
        equivalence.get('expected_asset_sha256') == expected_asset and
        equivalence.get('asset_sha256') == actual.get('asset_sha256')
        for equivalence in asset_equivalences
    )


def _candidate_sources(candidate: Mapping) -> tuple[str, list[Mapping]]:
    if not isinstance(candidate, Mapping):
        raise ValueError('检索候选必须为对象')
    identity = candidate.get('candidate_id')
    sources = candidate.get('sources')
    if not isinstance(identity, str) or not identity.strip():
        raise ValueError('检索候选缺少稳定身份')
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
        raise ValueError('检索候选来源必须为列表')
    if any(not isinstance(source, Mapping) for source in sources):
        raise ValueError('检索候选来源项必须为对象')
    return identity, list(sources)


def retrieval_metrics(question: Mapping, ranked_candidates: Sequence[Mapping], *,
                      k_values: Sequence[int] = DEFAULT_K,
                      asset_equivalences: Sequence[Mapping] = ()) -> dict:
    """按允许证据计算来源组覆盖和排序指标。

    外层证据组是全部必需目标，组内是可替代来源。Recall@k按覆盖目标组计数；
    MRR是首个命中目标组的候选倒数排名；组级nDCG对每个目标组的首次命中排名
    做折扣，IDCG假设每个目标组均可在rank 1命中。无证据题和未审核草稿不打分。
    来源按原件hash/物理页/图像hash核对；指标不评价引文语义或答案正确性。
    """
    ks = _validate_k_values(k_values)
    if not isinstance(question, Mapping):
        raise ValueError('题目必须为对象')
    if not isinstance(ranked_candidates, Sequence) or isinstance(ranked_candidates, (str, bytes)):
        raise ValueError('检索候选必须为有序列表')
    if not isinstance(asset_equivalences, Sequence) or isinstance(asset_equivalences, (str, bytes)):
        raise ValueError('图像对应表必须为列表')
    if any(not isinstance(row, Mapping) for row in asset_equivalences):
        raise ValueError('图像对应项必须为对象')
    groups = question.get('allowed_evidence')
    if not isinstance(groups, Sequence) or isinstance(groups, (str, bytes)):
        raise ValueError('允许证据必须是分组列表')
    if any(not isinstance(group, Sequence) or isinstance(group, (str, bytes)) or not group or
           any(not isinstance(item, Mapping) for item in group) for group in groups):
        raise ValueError('每个必需证据组都须包含至少一个来源备选项')

    eligible = is_label_eligible(question)
    output = {
        'label_eligible': eligible,
        'evidence_applicable': bool(groups),
        'recall_at_k': {str(k): None for k in ks},
        'mrr': None,
        'ndcg_at_k': {str(k): None for k in ks},
        'human_answer_correctness': None,
    }
    identities = set()
    normalized = []
    for candidate in ranked_candidates:
        identity, sources = _candidate_sources(candidate)
        if identity in identities:
            raise ValueError('检索候选身份重复，排名不得重复计分')
        identities.add(identity)
        normalized.append(sources)

    if not eligible or not groups:
        return output

    first_group_ranks: list[int | None] = [None] * len(groups)
    rank_gains = [0] * len(normalized)
    for rank, sources in enumerate(normalized, 1):
        for group_index, group in enumerate(groups):
            if first_group_ranks[group_index] is not None:
                continue
            if any(_source_matches(expected, actual, asset_equivalences)
                   for expected in group for actual in sources):
                first_group_ranks[group_index] = rank
                rank_gains[rank - 1] += 1

    first_relevant_rank = min((rank for rank in first_group_ranks if rank is not None), default=None)
    output['mrr'] = 1 / first_relevant_rank if first_relevant_rank is not None else 0.0
    group_count = len(groups)
    for k in ks:
        satisfied = sum(rank is not None and rank <= k for rank in first_group_ranks)
        output['recall_at_k'][str(k)] = satisfied / group_count
        dcg = sum(gain / math.log2(rank + 1)
                  for rank, gain in enumerate(rank_gains[:k], 1) if gain)
        # 目标单位是必需证据组；理想值是每组均在rank 1命中，多个组可由同一
        # 候选的多个来源共同满足。外层组完整度另由Recall@k明确呈现。
        output['ndcg_at_k'][str(k)] = dcg / group_count
    return output


def _mean(values: Sequence[float]) -> float | None:
    return sum(values) / len(values) if values else None


def _metric_means(records: Sequence[Mapping]) -> dict:
    by_stage: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    def add_metric(stage: str, metric: Mapping) -> None:
        if not metric.get('label_eligible') or not metric.get('evidence_applicable'):
            return
        values = [('mrr', metric.get('mrr'))]
        values.extend((f'recall_at_k@{k}', value) for k, value in metric.get('recall_at_k', {}).items())
        values.extend((f'ndcg_at_k@{k}', value) for k, value in metric.get('ndcg_at_k', {}).items())
        for name, value in values:
            if value is None:
                continue
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError('检索汇总指标必须为有限0..1值')
            by_stage[stage][name].append(float(value))

    for row in records:
        row_metrics = row.get('metrics') if isinstance(row.get('metrics'), Mapping) else {}
        retrieval = row_metrics.get('retrieval') or {}
        if isinstance(retrieval, Mapping) and 'label_eligible' in retrieval:
            add_metric('retrieval', retrieval)
        elif isinstance(retrieval, Mapping):
            for stage, metric in retrieval.items():
                if isinstance(stage, str) and isinstance(metric, Mapping):
                    add_metric(stage, metric)
    return {stage: {name: _mean(values) for name, values in sorted(metrics.items())}
            for stage, metrics in sorted(by_stage.items())}


def _accounting_summary(records: Sequence[Mapping], *, expected_count: int) -> dict:
    calls: dict[str, int] = defaultdict(int)
    input_tokens = output_tokens = 0
    has_calls = has_input = has_output = False
    costs, http_calls = [], []
    for row in records:
        result = row.get('result') if isinstance(row.get('result'), Mapping) else {}
        call_counts = result.get('logical_provider_calls')
        if isinstance(call_counts, Mapping):
            has_calls = True
            for name, count in call_counts.items():
                if (not isinstance(name, str) or not name or isinstance(count, bool) or
                        not isinstance(count, int) or count < 0):
                    raise ValueError('逻辑调用统计必须是非负整数')
                calls[name] += count
        token_usage = result.get('token_usage')
        if isinstance(token_usage, Mapping):
            for key, label in (('input', 'input'), ('output', 'output')):
                value = token_usage.get(key)
                if value is None:
                    continue
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise ValueError('token用量必须是非负整数')
                if label == 'input':
                    input_tokens += value
                    has_input = True
                else:
                    output_tokens += value
                    has_output = True
        if result.get('exact_cost') is not None:
            value = result['exact_cost']
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError('精确费用必须是非负数')
            costs.append((float(value), result.get('currency')))
        if result.get('exact_sdk_http_calls') is not None:
            value = result['exact_sdk_http_calls']
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError('精确HTTP调用数必须为非负整数')
            http_calls.append(value)

    currencies = {currency for _, currency in costs}
    cost_complete = (len(records) == expected_count and len(costs) == expected_count and
                     len(currencies) == 1 and None not in currencies)
    calls_complete = (len(records) == expected_count and
                      all(isinstance(row.get('result'), Mapping) and
                          isinstance(row['result'].get('logical_provider_calls'), Mapping) for row in records))
    input_complete = (len(records) == expected_count and
                      all(isinstance(row.get('result'), Mapping) and
                          isinstance(row['result'].get('token_usage'), Mapping) and
                          row['result']['token_usage'].get('input') is not None for row in records))
    output_complete = (len(records) == expected_count and
                       all(isinstance(row.get('result'), Mapping) and
                           isinstance(row['result'].get('token_usage'), Mapping) and
                           row['result']['token_usage'].get('output') is not None for row in records))
    http_complete = len(records) == expected_count and len(http_calls) == expected_count
    return {
        'logical_provider_calls': dict(sorted(calls.items())) if calls_complete else None,
        'logical_provider_calls_complete': calls_complete,
        'observed_logical_provider_calls': dict(sorted(calls.items())) if has_calls else None,
        'input_tokens': input_tokens if input_complete else None,
        'output_tokens': output_tokens if output_complete else None,
        'exact_sdk_http_calls': sum(http_calls) if http_complete else None,
        'exact_cost': sum(value for value, _ in costs) if cost_complete else None,
        'currency': next(iter(currencies)) if cost_complete else None,
    }


def summarize_experiment(records: Sequence[Mapping], questions: Sequence[Mapping]) -> dict:
    """按题型/失败阶段汇总；未采集成本保持null，不能伪装为0。"""
    if not isinstance(records, Sequence) or isinstance(records, (str, bytes)):
        raise ValueError('实验记录必须为列表')
    if not isinstance(questions, Sequence) or isinstance(questions, (str, bytes)):
        raise ValueError('实验题目必须为列表')
    question_by_id = {row.get('id'): row for row in questions if isinstance(row, Mapping)}
    if len(question_by_id) != len(questions) or any(not isinstance(qid, str) or not qid for qid in question_by_id):
        raise ValueError('实验题目身份缺失或重复')
    record_by_id = {}
    for row in records:
        if not isinstance(row, Mapping) or row.get('id') not in question_by_id:
            raise ValueError('实验结果引用未知题目')
        if row['id'] in record_by_id:
            raise ValueError('实验结果题目身份重复')
        if row.get('status') not in {'completed', 'failed'}:
            raise ValueError('实验结果状态必须明确为completed或failed')
        record_by_id[row['id']] = row

    questions_by_category: dict[str, list[str]] = defaultdict(list)
    for qid, question in question_by_id.items():
        questions_by_category[question['category']].append(qid)
    failures: dict[str, int] = defaultdict(int)
    for qid, row in record_by_id.items():
        if row.get('status') == 'failed':
            stage = row.get('failure_stage')
            safe_stages = {'validation', 'planning', 'retrieval', 'rerank', 'generation', 'persistence'}
            failures[stage if isinstance(stage, str) and stage in safe_stages else 'unknown'] += 1

    by_category = {}
    for category, qids in sorted(questions_by_category.items()):
        selected = [record_by_id[qid] for qid in qids if qid in record_by_id]
        completed = [row for row in selected if row.get('status') == 'completed']
        failed = [row for row in selected if row.get('status') == 'failed']
        by_category[category] = {
            'selected': len(qids), 'completed': len(completed), 'failed': len(failed),
            'missing': len(qids) - len(selected),
            'retrieval_metric_means': _metric_means(completed),
            'accounting': _accounting_summary(selected, expected_count=len(qids)),
        }
    return {
        'selected': len(question_by_id),
        'completed': sum(row.get('status') == 'completed' for row in record_by_id.values()),
        'failed': sum(row.get('status') == 'failed' for row in record_by_id.values()),
        'missing_results': len(question_by_id) - len(record_by_id),
        'by_category': by_category,
        'by_failure_stage': dict(sorted(failures.items())),
        'retrieval_metric_means': _metric_means(list(record_by_id.values())),
        'accounting': _accounting_summary(list(record_by_id.values()), expected_count=len(question_by_id)),
    }
