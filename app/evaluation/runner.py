"""固定划分、失败可恢复的最小运行器；原始问答只写本机输出。"""
import argparse
from contextlib import contextmanager
import json
import math
import os
from pathlib import Path
import time
from uuid import uuid4

from .validate_dataset import validate_dataset, fingerprint, file_sha


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid4().hex + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, path)


def save_results(output, results):
    temporary = output / ('results.' + uuid4().hex + '.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        stream.write(''.join(json.dumps(r, ensure_ascii=False, allow_nan=False) + '\n' for r in results))
        stream.flush(); os.fsync(stream.fileno())
    os.replace(temporary, output / 'results.jsonl')


@contextmanager
def output_lock(output):
    output.mkdir(parents=True, exist_ok=True)
    lock = output / '.runner.lock'
    try:
        stream = lock.open('x', encoding='utf-8')
    except FileExistsError:
        raise ValueError('输出目录已有执行占用，不能并发覆盖；异常退出须按恢复手册核对占用') from None
    try:
        with stream:
            stream.write(json.dumps({'pid': os.getpid(), 'started_at': time.time()}))
            stream.flush()
            yield
    finally:
        lock.unlink()


def strategy_fingerprint(config):
    return fingerprint({k: config.get(k, {}) for k in ('strategy', 'parameters', 'versions')})


def reproducibility_metadata(config, *, dataset_sha256, split_manifest_sha256, config_sha256):
    """生成M6清单必须保存的完整、可校验复现身份。"""
    return {
        'metric_schema_version': config['metric_schema_version'],
        'dataset_sha256': dataset_sha256,
        'split_manifest_sha256': split_manifest_sha256,
        'config_sha256': config_sha256,
        'strategy_sha256': strategy_fingerprint(config),
        'strategy': config['strategy'],
        'parameters': config.get('parameters', {}),
        'versions': {key: config['versions'][key] for key in ('code', 'model', 'prompt')},
        'seed': config['seed'],
    }


def check_split(config, manifest):
    if config.get('split') not in {'dev', 'heldout'} or config.get('phase') not in {'development', 'final'}:
        raise ValueError('必须明确开发或最终评价阶段与划分')
    if config['dataset_sha256'] != manifest['dataset_sha256']:
        raise ValueError('实验没有绑定当前冻结题集')
    if config['split'] == 'heldout':
        if config['phase'] != 'final' or not config.get('selection'):
            raise ValueError('heldout仅在策略冻结后用于最终评价')
        selected = json.loads(Path(config['selection']).read_text(encoding='utf-8'))
        if (not isinstance(selected['strategy_sha256'], list)
            or selected['dataset_sha256'] != manifest['dataset_sha256']
            or strategy_fingerprint(config) not in selected['strategy_sha256']
            or file_sha(selected['development_report']) != selected['development_report_sha256']):
            raise ValueError('最终策略或开发报告与选择记录不一致')
    elif config['phase'] != 'development':
        raise ValueError('开发题只用于开发阶段，避免阶段误标')
    if config.get('execution_mode') not in {'unit_injection', 'real_query_runner', 'real_retrieval_grid'}:
        raise ValueError('须显式区分单元注入与真实QueryRunner执行')
    if not all(config.get('versions', {}).get(k) for k in ('code', 'model', 'prompt')):
        raise ValueError('缺少代码/模型/prompt版本')
    # M4旧实验保持原配置兼容；M6显式采用新指标契约后必须冻结随机种子。
    if 'metric_schema_version' in config:
        version = config['metric_schema_version']
        if isinstance(version, bool) or not isinstance(version, int) or version != 1:
            raise ValueError('不支持的评测指标契约版本')
        seed = config.get('seed')
        if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
            raise ValueError('M6实验必须记录非负整数seed')
        if not config.get('strategy'):
            raise ValueError('M6实验必须记录策略身份')
        ks = config.get('metric_k_values', (1, 5, 10))
        if (not isinstance(ks, (list, tuple)) or not ks or
                any(isinstance(value, bool) or not isinstance(value, int) or value < 1 for value in ks) or
                len(set(ks)) != len(ks)):
            raise ValueError('metric_k_values必须是唯一正整数列表')


def evidence_metrics(question, result, *, asset_equivalences=()):
    # 原文页/资产匹配只证明允许来源命中，不等同人工答案正确性。
    citations = result.get('citations', [])
    def matches(expected, cited):
        if cited.get('document_sha256') != expected['document_sha256'] or cited.get('page') != expected['page']:
            return False
        if not expected.get('asset_sha256') or cited.get('asset_sha256') == expected['asset_sha256']:
            return True
        # 原PDF裁图与解析裁图可有不同字节；仅按冻结的精确对应计分，不改写真实引用hash。
        return any(m['document_sha256'] == expected['document_sha256'] and m['page'] == expected['page']
                   and m['asset_sha256'] == cited.get('asset_sha256')
                   and m['expected_asset_sha256'] == expected['asset_sha256'] for m in asset_equivalences)
    groups = question['allowed_evidence']
    matched = sum(any(matches(e, c) for e in g for c in citations) for g in groups)
    return {'allowed_evidence_group_recall': matched / len(groups) if groups else None,
            'behavior_matches': result.get('behavior') == question['expected']['behavior'],
            'human_answer_correctness': None}


def percentile(values, p):
    if not values: return None
    ordered = sorted(values); index = (len(ordered) - 1) * p
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def read_attempts(path):
    """只恢复未以换行提交的尾部；中部损坏拒绝执行，原始残片另存。"""
    raw = path.read_bytes()
    committed = raw.rfind(b'\n') + 1
    if committed < len(raw):
        fragment = raw[committed:]
        # 完整JSON只缺换行也视作尚未提交；真实执行器另有持久run检查点。
        backup = path.with_name('attempts-torn-' + uuid4().hex + '.bin')
        with backup.open('xb') as stream:
            stream.write(fragment); stream.flush(); os.fsync(stream.fileno())
        with path.open('r+b') as stream:
            stream.truncate(committed); stream.flush(); os.fsync(stream.fileno())
    return [json.loads(line) for line in raw[:committed].splitlines()]


def run_experiment(dataset, manifest, config, output, executor, *, should_cancel=None, verify_checkpoint=None):
    rows = validate_dataset(dataset, manifest=manifest, minimum=1)
    frozen = json.loads(Path(manifest).read_text(encoding='utf-8'))
    check_split(config, frozen)
    selected = select_questions(rows, config)
    if not selected: raise ValueError('选定划分没有题目')
    config = json.loads(json.dumps(config))
    digest = fingerprint(config)
    output = Path(output)
    with output_lock(output):
        report_path, attempts_path = output / 'manifest.json', output / 'attempts.jsonl'
        split_manifest_sha256 = file_sha(manifest)
        m6_reproducibility = None
        if config.get('metric_schema_version') == 1:
            m6_reproducibility = reproducibility_metadata(
                config, dataset_sha256=frozen['dataset_sha256'],
                split_manifest_sha256=split_manifest_sha256, config_sha256=digest)
        if report_path.exists():
            saved = json.loads(report_path.read_text(encoding='utf-8'))
            if saved['config_sha256'] != digest or saved['split_manifest_sha256'] != split_manifest_sha256:
                raise ValueError('输出目录已属于其他参数/题集，须使用新实验目录')
            if m6_reproducibility is not None:
                if (saved.get('manifest_schema_version') != 1 or
                        saved.get('reproducibility') != m6_reproducibility or
                        saved.get('reproducibility_sha256') != fingerprint(m6_reproducibility)):
                    raise ValueError('M6实验复现清单缺失、损坏或与当前seed不一致')
        elif any(p.name != '.runner.lock' for p in output.iterdir()):
            raise ValueError('输出目录已有未知文件，拒绝覆盖')
        report = {'experiment_id': config['experiment_id'], 'dataset_sha256': frozen['dataset_sha256'],
                  'split_manifest_sha256': file_sha(manifest), 'config_sha256': digest, 'config': config,
                  'selected_ids': [r['id'] for r in selected], 'execution_mode': config['execution_mode'],
                  'status': 'running', 'notice': '辅助来源命中不等同人工答案正确；注入运行不是真实链路。'}
        if m6_reproducibility is not None:
            report['manifest_schema_version'] = 1
            report['reproducibility'] = m6_reproducibility
            report['reproducibility_sha256'] = fingerprint(m6_reproducibility)
        atomic_json(report_path, report)
        by_id = {}
        cancelled = False
        if attempts_path.exists():
            for record in read_attempts(attempts_path):
                if record['config_sha256'] != digest or record['id'] not in report['selected_ids']:
                    raise ValueError('历史尝试不属于当前冻结实验')
                by_id[record['id']] = record
        for question in selected:
            qid = question['id']
            if by_id.get(qid, {}).get('status') == 'completed':
                if verify_checkpoint:
                    verify_checkpoint(question, by_id[qid])
                continue
            if should_cancel is not None and should_cancel():
                cancelled = True
                break
            started = time.perf_counter()
            record = {'id': qid, 'config_sha256': digest, 'category': question['category'],
                      'attempt': by_id.get(qid, {}).get('attempt', 0) + 1}
            try:
                result = executor(question)
                if not isinstance(result, dict) or not isinstance(result.get('answer'), str) or not isinstance(result.get('citations'), list):
                    raise ValueError('执行器响应格式错误')
                json.dumps(result, allow_nan=False)
                if config.get('metric_schema_version') == 1:
                    retrieval_candidates = result.pop('retrieval_candidates', None)
                else:
                    retrieval_candidates = None
                metric_row = evidence_metrics(question, result,
                    asset_equivalences=config.get('corpus', {}).get('asset_equivalences', []))
                if retrieval_candidates is not None and config.get('metric_schema_version') == 1:
                    from .metrics import retrieval_metrics
                    equivalences = config.get('corpus', {}).get('asset_equivalences', [])
                    k_values = config.get('metric_k_values', (1, 5, 10))
                    if isinstance(retrieval_candidates, dict):
                        retrieval = {stage: retrieval_metrics(question, candidates,
                            k_values=k_values, asset_equivalences=equivalences)
                            for stage, candidates in retrieval_candidates.items()}
                    else:
                        retrieval = retrieval_metrics(question, retrieval_candidates,
                            k_values=k_values, asset_equivalences=equivalences)
                    metric_row['retrieval'] = retrieval
                    # 保留可复核的候选身份/来源，不持久化完整候选文本或其他调试字段。
                    if isinstance(retrieval_candidates, dict):
                        result['retrieval_candidates'] = {stage: [
                            {'candidate_id': candidate['candidate_id'], 'sources': candidate['sources']}
                            for candidate in candidates]
                            for stage, candidates in retrieval_candidates.items()}
                    else:
                        result['retrieval_candidates'] = [
                            {'candidate_id': candidate['candidate_id'], 'sources': candidate['sources']}
                            for candidate in retrieval_candidates]
                if config.get('metric_schema_version') == 1:
                    from .datasets import is_label_eligible
                    record['label_eligible'] = is_label_eligible(question)
                record.update(status='completed', result=result, metrics=metric_row)
            except Exception as exc:
                record.update(status='failed', error={'type': type(exc).__name__})
                if config.get('metric_schema_version') == 1:
                    from app.infrastructure.providers.policy import classify
                    code, retryable = classify(exc)
                    record['error'].update(code=code, retryable=retryable)
                    stage = getattr(exc, 'stage', getattr(exc, 'failure_stage', None))
                    safe_stages = {'validation', 'planning', 'retrieval', 'rerank', 'generation', 'persistence'}
                    if not isinstance(stage, str) or stage not in safe_stages:
                        stage = 'unknown'
                    from .datasets import is_label_eligible
                    record.update(label_eligible=is_label_eligible(question), failure_stage=stage)
            record['seconds'] = time.perf_counter() - started
            with attempts_path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush(); os.fsync(stream.fileno())
            by_id[qid] = record
            results = [by_id[r['id']] for r in selected if r['id'] in by_id]
            save_results(output, results)
        results = [by_id[r['id']] for r in selected if r['id'] in by_id]
        # 尝试日志已落盘而汇总尚未替换时退出，也可无需重调模型重建结果。
        save_results(output, results)
        timings = [r['seconds'] for r in results if r['status'] == 'completed']
        failed = sum(row.get('status') == 'failed' for row in results)
        if should_cancel is not None and should_cancel():
            cancelled = True
        report.update(status='cancelled' if cancelled else 'completed' if len(results) == len(selected) and not failed else 'incomplete',
                      completed=sum(row.get('status') == 'completed' for row in results),
                      failed=failed, p50_seconds=percentile(timings, .5), p95_seconds=percentile(timings, .95))
        if config.get('metric_schema_version') == 1:
            from .metrics import summarize_experiment
            report['summary'] = summarize_experiment(results, selected)
        atomic_json(report_path, report)
        return report


def select_questions(rows, config):
    selected = [row for row in rows if row['split'] == config['split']]
    if 'question_ids' not in config:
        return selected
    ids = config['question_ids']
    if (config['split'] != 'dev' or not isinstance(ids, list) or not ids or
            any(not isinstance(q, str) or not q for q in ids) or len(ids) != len(set(ids)) or
            not set(ids) <= {r['id'] for r in selected}):
        raise ValueError('受影响题子集只允许冻结开发集内非空且不重复的题目')
    return [r for r in selected if r['id'] in ids]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--manifest', type=Path)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        import yaml
        config = yaml.safe_load(args.config.read_text(encoding='utf-8'))
        manifest = args.manifest or args.dataset.with_name('split-manifest.json')
        validate_dataset(args.dataset, manifest=manifest)
        check_split(config, json.loads(manifest.read_text(encoding='utf-8')))
        if config['execution_mode'] != 'real_query_runner':
            raise ValueError('CLI仅执行真实链路，单元注入不能作为真实基线')
        from .query_adapter import RealQueryExecutor
        with RealQueryExecutor(config) as execute:
            try:
                report = run_experiment(args.dataset, args.manifest or args.dataset.with_name('split-manifest.json'), config, args.output, execute)
            finally:
                counts=execute.resources.get('provider_counts')
                if counts is not None:
                    args.output.mkdir(parents=True,exist_ok=True)
                    with (args.output/('provider-counts-'+uuid4().hex+'.json')).open('x',encoding='utf-8') as stream:
                        json.dump(dict(config_sha256=fingerprint(config),logical_calls=counts.snapshot(),exact_sdk_http_calls=None,exact_cost=None),stream,indent=2)
    except (ValueError, KeyError, OSError):
        parser.exit(1, '实验未完成：请检查本机报告、冻结划分和环境配置；不输出私有问题、路径或异常内容。\n')
    print(json.dumps({k: report[k] for k in ('experiment_id', 'status', 'completed', 'failed', 'p50_seconds', 'p95_seconds')}, ensure_ascii=False))
    if report['failed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
