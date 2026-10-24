"""显式选择M4本轮摘要与独立快照；原始证据留本机，禁止覆盖快照。"""
import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def relative_path(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError('检查路径超出项目范围')
    return path


def verify_hashes(rows, root):
    paths = set()
    for row in rows:
        path = relative_path(root, row['path'])
        if path in paths or hashlib.sha256(path.read_bytes()).hexdigest() != row['sha256']:
            raise ValueError('证据重复或哈希不一致：' + row['path'])
        paths.add(path)
    return paths


def verify_summary(summary_path, *, root):
    root = Path(root)
    summary = json.loads(relative_path(root, summary_path).read_text('utf-8'))
    paths = verify_hashes(summary['raw_evidence'], root)
    if not summary['tests']:
        raise ValueError('缺少本轮实际验证结果')
    for item in summary['tests']:
        junit = relative_path(root, item['junit'])
        if junit not in paths or item['exit_code'] != 0:
            raise ValueError('验证没有成功退出或未绑定JUnit')
        suites = ET.parse(junit).getroot()
        suites = [suites] if suites.tag == 'testsuite' else list(suites.iter('testsuite'))
        cases = [c for suite in suites for c in suite.findall('testcase')]
        if (not suites or sum(int(s.get('tests', 0)) for s in suites) != len(cases)
                or any(int(s.get(k, 0)) for s in suites for k in ('errors', 'failures', 'skipped'))
                or any(c.find(k) is not None for c in cases for k in ('error', 'failure', 'skipped'))
                or len(cases) != item['passed']):
            raise ValueError('摘要与实际JUnit不一致或存在未通过项')
    report_path = relative_path(root, summary['real_baseline']['report'])
    if report_path not in paths:
        raise ValueError('真实基线报告未绑定hash')
    live = json.loads(report_path.read_text('utf-8'))
    if live.get('passed') is not True:
        raise ValueError('本轮真实基线复核未通过')
    # 完整语料/结果原件的哈希也要复核，不能只信一份脱敏报告的passed字段。
    verify_hashes(live.get('raw_evidence', []), root)
    return summary


def main():
    from scripts.verification import build_m1_artifacts as audit
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    summary = verify_summary(args.summary, root=root)
    target = relative_path(root, args.manifest)
    if not target.is_relative_to(root / 'docs/development/reviews'):
        parser.error('快照须在reviews目录')
    audit.MANIFEST = target
    if args.check:
        saved = json.loads(target.read_text('utf-8'))
        if saved['summary'] != args.summary.as_posix() or saved['baseline_commit'] != args.base:
            raise ValueError('摘要或基线提交与选定快照不一致')
        paths = [r['path'] for r in saved['files']]
    else:
        if target.exists():
            parser.error('快照已存在，请选择新的本轮路径，禁止覆盖')
        names = audit.git('diff', '--name-only', args.base) + audit.git('ls-files', '--others', '--exclude-standard')
        paths = sorted({p for p in names if p.startswith(('app/', 'tests/', 'scripts/', 'docs/'))
            or p in {'.env.example', '.gitignore', 'README.md', 'THIRD_PARTY_NOTICES.md'}})
        paths = [p for p in paths if p != args.manifest.as_posix() and (root / p).is_file()]
    if any(p.startswith(('evals/', 'output/', 'docs/development/evidence/')) for p in paths):
        raise ValueError('提交快照包含本机私有材料')
    files, links, syntax = audit.validate_files(paths)
    if args.check:
        if files != saved['files'] or links != saved['links']:
            raise ValueError('源码或链接已偏离所选快照')
    else:
        saved = {'notice': 'M4执行接续快照，非总控通过；原始证据留本机。自身hash不循环记录。',
            'baseline_commit': args.base, 'pre_submission_head': audit.git('rev-parse', 'HEAD')[0],
            'summary': args.summary.as_posix(), 'file_count': len(files), 'python_syntax_files': syntax,
            'checked_markdown_links': len(links), 'files': files, 'links': links}
        with target.open('x', encoding='utf-8') as stream:
            json.dump(saved, stream, ensure_ascii=False, indent=2)
    print(json.dumps({'passed': True, 'files': len(files), 'python_syntax': syntax,
        'links': len(links), 'tests': [r['passed'] for r in summary['tests']]}))


if __name__ == '__main__':
    main()
