"""显式M6部分/最终报告快照，按原始结果复核，拒绝覆盖历史快照。"""
import argparse
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET

from scripts.verification.build_m4_artifacts import relative_path, verify_hashes


def verify_summary(path, root):
    summary = json.loads(relative_path(root, path).read_text('utf-8'))
    if summary['stage'] != 'M6' or summary['review_status'] not in {'未提交', '待审查'}:
        raise ValueError('只检查M6执行材料，不能自标总控通过')
    if summary['review_status'] == '待审查' and (summary['incomplete'] or not summary['human_acceptance_complete']):
        raise ValueError('真实验收不足时只能保存未提交的部分接续材料')
    evidence = verify_hashes(summary['raw_evidence'], root)
    def bound(name):
        report = relative_path(root, name)
        if report not in evidence:
            raise ValueError('结果未绑定原件hash：'+name)
        return report
    for entry in summary['tests']:
        suites = ET.parse(bound(entry['junit'])).getroot()
        suites = [suites] if suites.tag == 'testsuite' else list(suites.iter('testsuite'))
        cases = [c for s in suites for c in s.findall('testcase')]
        if (entry['exit_code'] != 0 or len(cases) != entry['passed'] or
                sum(int(s.get('tests', 0)) for s in suites) != len(cases) or
                any(int(s.get(k, 0)) for s in suites for k in ('errors', 'failures', 'skipped'))):
            raise ValueError('测试摘要与原始JUnit不一致')
        actual = {}
        for case in cases:
            group = case.attrib['classname'].split('.')[1]
            actual[group] = actual.get(group, 0)+1
        if actual != entry['by_directory']:
            raise ValueError('测试类型数量与原始JUnit不一致')
    ledgers = [json.loads(bound(name).read_text('utf-8')) for name in summary['command_ledgers']]
    if any(not ledger['passed'] or any(c['exit_code'] != 0 for c in ledger['checks']) for ledger in ledgers):
        raise ValueError('逐命令退出码存在失败')
    frontend = summary['frontend']
    unit = json.loads(bound(frontend['unit_report']).read_text('utf-8'))
    browser = json.loads(bound(frontend['browser_report']).read_text('utf-8'))['stats']
    if (unit['numPassedTests'] != frontend['unit_passed'] or unit['numFailedTests'] or unit['numPendingTests'] or
            browser['expected'] != frontend['browser_passed'] or any(browser[k] for k in ('unexpected', 'skipped', 'flaky'))):
        raise ValueError('前端实际结果不符或存在未通过项')
    legacy = bound(summary['legacy_reimport']['report']).read_text('utf-8')
    match = re.search(r'Ran (\d+) tests', legacy)
    if not match or int(match[1]) != summary['legacy_reimport']['passed'] or not re.search(r'^OK\s*$', legacy, re.M):
        raise ValueError('既有重导入实际结果不一致')
    live = json.loads(bound(summary['real_sample']['report']).read_text('utf-8'))
    replay = json.loads(bound(summary['checkpoint_replay']['report']).read_text('utf-8'))
    if (not live['passed'] or not all(live['checks'].values()) or
            sum(live['checks'].values()) != summary['real_sample']['checks_passed'] or
            live['logical_provider_calls'] != summary['real_sample']['logical_provider_calls'] or
            not replay['passed'] or any(replay['logical_provider_calls'].values()) or
            not replay['actual_results_equal'] or replay['independent_new_generation'] is not False):
        raise ValueError('真实小样/检查点复验不符')
    verify_hashes(live['raw_evidence'], root)
    verify_hashes(replay['raw_evidence'], root)
    if not summary['human_acceptance_complete'] and summary['human_quality_passed'] is not None:
        raise ValueError('未完成人工验收不能宣称质量通过')
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
    summary = verify_summary(args.summary, root)
    target = relative_path(root, args.manifest)
    if not target.is_relative_to(root/'docs/development/reviews'):
        parser.error('快照须写入reviews')
    audit.MANIFEST = target
    if args.check:
        saved = json.loads(target.read_text('utf-8'))
        if saved['summary'] != args.summary.as_posix() or saved['baseline_commit'] != args.base:
            raise ValueError('快照与显式报告/基线不符')
        paths = [r['path'] for r in saved['files']]
    else:
        if target.exists():
            parser.error('快照已存在，请使用新路径')
        paths = sorted({name for name in audit.git('diff', '--name-only', args.base) +
            audit.git('ls-files', '--others', '--exclude-standard') if
            (name.startswith(('app/', 'tests/', 'scripts/', 'docs/', 'frontend/')) or name in {
                '.env.example', '.gitignore', 'README.md', 'THIRD_PARTY_NOTICES.md'}) and
            name != args.manifest.as_posix() and (root/name).is_file()})
    if any(name.startswith(('evals/', 'output/', 'tmp/', 'docs/development/evidence/',
                            'frontend/test-results/', 'frontend/node_modules/', 'frontend/dist/')) for name in paths):
        raise ValueError('快照包含本机私有产物或构建目录')
    files, links, syntax = audit.validate_files(paths)
    if args.check:
        if files != saved['files'] or links != saved['links']:
            raise ValueError('当前文件/链接与所选快照不符')
    else:
        saved = dict(notice='M6执行接续快照，不代表阶段验收或总控通过；原始材料仅本机。',
            summary=args.summary.as_posix(), baseline_commit=args.base,
            pre_submission_head=audit.git('rev-parse', 'HEAD')[0],file_count=len(files),
            python_syntax_files=syntax,checked_markdown_links=len(links),files=files,links=links)
        with target.open('x', encoding='utf-8') as stream:
            json.dump(saved, stream, ensure_ascii=False, indent=2)
    print(json.dumps(dict(passed=True,files=len(files),python_syntax=syntax,links=len(links),
        tests=[t['passed'] for t in summary['tests']],review_status=summary['review_status'])))


if __name__ == '__main__':
    main()
