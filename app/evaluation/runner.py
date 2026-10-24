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


def run_experiment(dataset, manifest, config, output, executor):
    rows = validate_dataset(dataset, manifest=manifest, minimum=1)
    frozen = json.loads(Path(manifest).read_text(encoding='utf-8'))
    check_split(config, frozen)
    selected = [row for row in rows if row['split'] == config['split']]
    if not selected: raise ValueError('选定划分没有题目')
    config = json.loads(json.dumps(config))
    digest = fingerprint(config)
    output = Path(output)
    with output_lock(output):
        report_path, attempts_path = output / 'manifest.json', output / 'attempts.jsonl'
        if report_path.exists():
            saved = json.loads(report_path.read_text(encoding='utf-8'))
            if saved['config_sha256'] != digest or saved['split_manifest_sha256'] != file_sha(manifest):
                raise ValueError('输出目录已属于其他参数/题集，须使用新实验目录')
        elif any(p.name != '.runner.lock' for p in output.iterdir()):
            raise ValueError('输出目录已有未知文件，拒绝覆盖')
        report = {'experiment_id': config['experiment_id'], 'dataset_sha256': frozen['dataset_sha256'],
                  'split_manifest_sha256': file_sha(manifest), 'config_sha256': digest, 'config': config,
                  'selected_ids': [r['id'] for r in selected], 'execution_mode': config['execution_mode'],
                  'status': 'running', 'notice': '辅助来源命中不等同人工答案正确；注入运行不是真实链路。'}
        atomic_json(report_path, report)
        by_id = {}
        if attempts_path.exists():
            for record in read_attempts(attempts_path):
                if record['config_sha256'] != digest or record['id'] not in report['selected_ids']:
                    raise ValueError('历史尝试不属于当前冻结实验')
                by_id[record['id']] = record
        for question in selected:
            qid = question['id']
            if by_id.get(qid, {}).get('status') == 'completed': continue
            started = time.perf_counter()
            record = {'id': qid, 'config_sha256': digest, 'category': question['category'],
                      'attempt': by_id.get(qid, {}).get('attempt', 0) + 1}
            try:
                result = executor(question)
                if not isinstance(result, dict) or not isinstance(result.get('answer'), str) or not isinstance(result.get('citations'), list):
                    raise ValueError('执行器响应格式错误')
                json.dumps(result, allow_nan=False)
                record.update(status='completed', result=result, metrics=evidence_metrics(question, result,
                    asset_equivalences=config.get('corpus', {}).get('asset_equivalences', [])))
            except Exception as exc:
                record.update(status='failed', error={'type': type(exc).__name__})
            record['seconds'] = time.perf_counter() - started
            with attempts_path.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + '\n')
                stream.flush(); os.fsync(stream.fileno())
            by_id[qid] = record
            results = [by_id[r['id']] for r in selected if r['id'] in by_id]
            save_results(output, results)
        results = [by_id[r['id']] for r in selected]
        # 尝试日志已落盘而汇总尚未替换时退出，也可无需重调模型重建结果。
        save_results(output, results)
        timings = [r['seconds'] for r in results if r['status'] == 'completed']
        report.update(status='completed' if len(timings) == len(selected) else 'incomplete', completed=len(timings),
                      failed=len(selected) - len(timings), p50_seconds=percentile(timings, .5), p95_seconds=percentile(timings, .95))
        atomic_json(report_path, report)
        return report


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
            report = run_experiment(args.dataset, args.manifest or args.dataset.with_name('split-manifest.json'), config, args.output, execute)
    except (ValueError, KeyError, OSError):
        parser.exit(1, '实验未完成：请检查本机报告、冻结划分和环境配置；不输出私有问题、路径或异常内容。\n')
    print(json.dumps({k: report[k] for k in ('experiment_id', 'status', 'completed', 'failed', 'p50_seconds', 'p95_seconds')}, ensure_ascii=False))
    if report['failed']: raise SystemExit(1)


if __name__ == '__main__':
    main()
