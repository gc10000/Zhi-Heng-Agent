"""核对M2实际证据并生成独立提交快照，保留旧阶段及旧失败输出。"""
import argparse
from collections import Counter
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from scripts.verification import build_m1_artifacts as audit

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / 'docs/development/reviews/M2-artifact-manifest.json'
SUMMARY = ROOT / 'docs/development/reviews/M2-validation-summary.json'
BASE = 'ea798d1f08326a7798c3ea12169f7276bf4aa4ad'


def verify_results():
    summary = json.loads(SUMMARY.read_text(encoding='utf-8'))
    for item in summary['raw_evidence']:
        if audit.sha(ROOT / item['path']) != item['sha256']:
            raise ValueError('原始证据hash变化：' + item['path'])
    stage = summary['stage']
    suite = ET.parse(ROOT / stage['junit']).getroot().find('testsuite')
    if any(int(suite.attrib[k]) for k in ('errors', 'failures', 'skipped')):
        raise ValueError('阶段实际结果存在未通过项')
    counts = dict(Counter(t.attrib['classname'].split('.')[1] for t in suite.findall('testcase')))
    if int(suite.attrib['tests']) != stage['passed'] or counts != stage['test_directory_counts']:
        raise ValueError('阶段摘要与实际JUnit数量不符')
    live = json.loads((ROOT / 'docs/development/evidence/M2-live-api-first.json').read_text(encoding='utf-8'))
    if not live['passed'] or not all(live['checks'].values()) or live['checks'] != summary['live_api']['checks']:
        raise ValueError('真实API报告没有完整通过')
    legacy = (ROOT / 'docs/development/evidence/M2-legacy-reimport-v2.txt').read_text(encoding='utf-8', errors='replace')
    if 'Ran ' + str(summary['legacy_reimport']['passed']) + ' tests' not in legacy or 'OK' not in legacy:
        raise ValueError('既有回归实际结果不匹配')
    if any(summary[k]['exit_code'] for k in ('stage', 'legacy_reimport', 'live_api')):
        raise ValueError('验收命令存在非零退出')
    from app.main import create_app
    if create_app().openapi() != json.loads((ROOT / 'docs/architecture/openapi-v1.json').read_text(encoding='utf-8')):
        raise ValueError('OpenAPI导出与当前工厂不一致')
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    summary = verify_results()
    audit.MANIFEST = MANIFEST
    if args.check:
        saved = json.loads(MANIFEST.read_text(encoding='utf-8'))
        paths = [f['path'] for f in saved['files']]
    else:
        if MANIFEST.exists():
            parser.error('快照已存在，禁止覆盖；复审须新建轮次文件')
        changed = audit.git('diff', '--name-only', BASE)
        new = [p for p in audit.git('ls-files', '--others', '--exclude-standard')
               if p.startswith(('app/', 'docs/', 'scripts/', 'tests/'))]
        paths = sorted(set(changed + new) - {MANIFEST.relative_to(ROOT).as_posix()})
        if any(p.startswith(('evals/', 'docs/development/evidence/')) or p == '.env' for p in paths):
            raise ValueError('候选快照包含未授权公开范围')
    files, links, python_count = audit.validate_files(paths)
    if args.check:
        if files != saved['files'] or links != saved['links']:
            raise ValueError('文件快照或链接与提交时点不一致')
    else:
        saved = {'notice': 'M2独立提交快照；原始证据留本机，脱敏摘要引用其hash。自身hash不循环记录。非总控通过结论。',
                 'baseline_commit': BASE, 'pre_submission_head': audit.git('rev-parse', 'HEAD')[0],
                 'file_count': len(files), 'python_syntax_files': python_count,
                 'checked_markdown_links': len(links), 'secret_scan': '未匹配本机敏感配置值',
                 'stage_passed': summary['stage']['passed'], 'files': files, 'links': links}
        MANIFEST.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'files': len(files), 'python_syntax': python_count,
                      'links': len(links), 'stage_passed': summary['stage']['passed'], 'secret_scan_passed': True}))


if __name__ == '__main__':
    main()
