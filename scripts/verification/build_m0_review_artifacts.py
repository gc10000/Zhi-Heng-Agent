"""按显式提交规格和本轮实测证据生成独立快照；不覆盖旧提交或推断未运行的结果。"""
import argparse
import difflib
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / 'docs/development/evidence'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def make_manifest(spec, root=ROOT):
    live = read_json(root / spec['live_report'])
    tests = read_json(root / spec['validation_report'])['runs']
    for test in tests:
        assert sha(root / test['evidence']) == test['evidence_sha256'], '测试输出哈希不一致'
    todo = (root / 'docs/plans/DEVELOPMENT_TODO.md').read_text(encoding='utf-8')
    tasks = {task: flag == 'x' for flag, task in re.findall(r'- \[([ x])\] \*\*(M0-\d+)\*\*', todo)}
    review_text = (root / 'docs/development/REVIEW_STATUS.md').read_text(encoding='utf-8')
    review = re.search(r'\| M0 \| ([^|]+)\|', review_text)[1].strip()
    cold = read_json(root / spec['cold_start_report']) if spec.get('cold_start_report') else None
    questions_ok = {q['kind']: q.get('status') == 'completed' and bool(q.get('checks'))
                    and all(q['checks'].values()) for q in live['questions']}
    image = live.get('image_verification', {}).get('checks', {})
    image_ok = image.get('expected_topology_in_body') and image.get('expected_topology_in_final') and image.get('downloads_verified') and all(image.values())
    cold_ok = (cold is not None and cold.get('status') == 'passed' and cold.get('process_exit_code') == 0
               and cold.get('normal_configuration') is True and cold.get('prewarm_reranker') is False
               and cold.get('thread_overrides') == {} and cold.get('assistant_saved_count') == 1)
    evidence_complete = (all(questions_ok.get(kind) for kind in ('known', 'followup', 'image'))
                         and bool(image_ok) and bool(cold_ok)
                         and all(t['exit_code'] == 0 and t['passed'] is not None for t in tests))
    return {'stage': 'M0', 'revision': spec['revision'], 'record_date': spec['record_date'],
            'status': '已验收' if tasks and all(tasks.values()) and evidence_complete else '未完成',
            'review': review, 'task_status': tasks, 'evidence_complete': bool(evidence_complete),
            'selected_live_report': spec['live_report'], 'selected_validation_report': spec['validation_report'],
            'cold_start_report': spec.get('cold_start_report'), 'cold_start_verified': bool(cold_ok),
            'source_document': live['source_document'], 'source_chunk_ids': live['source_chunk_ids'],
            'source_content_sha256': live['source_hashes'], 'scope': live['scope'], 'objects': live['objects'],
            'models': live['models'], 'prompt_sha256': live['prompt_sha256'],
            'validation_config': {key: live.get(key) for key in ('validation_cpu_threads', 'prewarm_reranker', 'reranker_target_devices')},
            'questions': [{k: q[k] for k in ('kind', 'question', 'status', 'elapsed_seconds', 'checks', 'image_count')}
                          for q in live['questions']],
            'image_verification': live.get('image_verification'),
            'image_expectation': spec['image_expectation'], 'tests': tests,
            'limitations': spec['limitations'], 'evidence': spec['evidence'],
            'submission': spec['submission'], 'environment_evidence': 'docs/development/evidence/M0-01-environment.json'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True, help='显式指定本轮报告/输出/已知边界的 JSON')
    args = parser.parse_args()
    spec = read_json(args.spec)
    prefix = spec['artifact_prefix']
    assert re.fullmatch(r'M0-[A-Za-z0-9-]+', prefix)
    # 旧版备份与提交证据只读；每轮写独立 manifest、patch 和 inventory。
    originals = EVIDENCE / 'originals'
    for rel, expected in read_json(originals / 'manifest.json').items():
        assert sha(originals / rel) == expected, f'原始备份哈希改变：{rel}'
    backups = sorted(p for p in originals.rglob('*') if p.is_file() and p.name != 'manifest.json')
    patch, inventory = [], []
    for original in backups:
        rel = original.relative_to(originals)
        current = ROOT / rel
        assert current.is_file(), f'缺少待审查文件：{rel}'
        patch.extend(difflib.unified_diff(original.read_text(encoding='utf-8').splitlines(True),
                                         current.read_text(encoding='utf-8').splitlines(True),
                                         fromfile='a/' + rel.as_posix(), tofile='b/' + rel.as_posix()))
        inventory.append({'path': rel.as_posix(), 'kind': '已有文件修改', 'original_sha256': sha(original), 'sha256': sha(current)})
    new_paths = [ROOT / 'app/answering/context_budget.py', ROOT / 'app/answering/errors.py']
    new_paths += sorted(p for directory in ('tests', 'scripts/verification') for p in (ROOT / directory).rglob('*.py'))
    for current in new_paths:
        rel = current.relative_to(ROOT).as_posix()
        patch.extend(difflib.unified_diff([], current.read_text(encoding='utf-8').splitlines(True), fromfile='/dev/null', tofile='b/' + rel))
        inventory.append({'path': rel, 'kind': 'M0 新增文件', 'sha256': sha(current)})
    (EVIDENCE / f'{prefix}-diff.patch').write_text(''.join(patch), encoding='utf-8')
    manifest = make_manifest(spec)
    write_json(ROOT / spec['manifest_output'], manifest)
    docs = [ROOT / 'README.md', ROOT / 'docs/CONFIGURATION.md', args.spec.resolve(), ROOT / spec['manifest_output'], ROOT / spec['image_expectation']]
    docs += sorted(p for directory in ('docs/development', 'docs/plans') for p in (ROOT / directory).rglob('*.md') if 'evidence' not in p.parts)
    inventory += [{'path': p.relative_to(ROOT).as_posix(), 'kind': '审查文档快照（不表示均有改动）', 'sha256': sha(p)} for p in dict.fromkeys(docs)]
    write_json(EVIDENCE / f'{prefix}-file-inventory.json', inventory)
    print(json.dumps({'status': 'generated', 'code_files': len(backups) + len(new_paths), 'inventory_entries': len(inventory),
                      'baseline_status': manifest['status'], 'test_counts': [r['passed'] for r in manifest['tests']]}, ensure_ascii=True))


if __name__ == '__main__':
    main()
