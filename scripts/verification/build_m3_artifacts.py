"""按显式本轮摘要核对真实报告并保存M3源码快照；禁止覆盖已有快照。"""
import argparse
from collections import Counter
import json
from pathlib import Path
import re
import xml.etree.ElementTree as ET
from zipfile import ZipFile
from scripts.verification import build_m1_artifacts as audit

ROOT = Path(__file__).resolve().parents[2]


def verify(summary):
    for row in summary['raw_evidence']:
        if audit.sha(ROOT / row['path']) != row['sha256']:
            raise ValueError('证据哈希不一致：' + row['path'])
    stage = summary['backend']
    suite = ET.parse(ROOT / stage['junit']).getroot().find('testsuite')
    if any(int(suite.get(k, 0)) for k in ('errors', 'failures', 'skipped')):
        raise ValueError('后端回归存在未通过项')
    counts = dict(Counter(t.attrib['classname'].split('.')[1] for t in suite.findall('testcase')))
    if int(suite.attrib['tests']) != stage['passed'] or counts != stage['test_directory_counts']:
        raise ValueError('后端实际JUnit数量与摘要不一致')
    for key in ('browser_offline', 'browser_live', 'browser_login'):
        item = summary[key]
        report = json.loads((ROOT / item['report']).read_text(encoding='utf-8'))
        stats = report['stats']
        if any(stats[k] for k in ('unexpected', 'flaky', 'skipped')) or stats['expected'] != item['passed']:
            raise ValueError('浏览器结果未完整通过：' + key)
    unit = summary['frontend_unit']
    log = (ROOT / unit['report']).read_text(encoding='utf-8-sig')
    found = re.search(r'Tests\s+(\d+) passed \((\d+)\)', log)
    if not found or int(found[1]) != unit['passed'] or found[1] != found[2]:
        raise ValueError('前端单元结果不一致')
    live = json.loads((ROOT / summary['live_readonly']['report']).read_text(encoding='utf-8'))
    flow = json.loads((ROOT / summary['browser_live']['flow']).read_text(encoding='utf-8'))
    if not live['passed'] or not all(live['checks'].values()) or not flow['passed'] or not all(flow['checks'].values()):
        raise ValueError('真实UI或只读复核未通过')
    if live['source_flow_sha256'] != audit.sha(ROOT / summary['browser_live']['flow']):
        raise ValueError('只读复核不是选定的UI产物')
    legacy = summary['legacy_reimport']
    text = (ROOT / legacy['report']).read_text(encoding='utf-8-sig')
    if not re.search(r'Ran ' + str(legacy['passed']) + r' tests', text) or '\nOK' not in text:
        raise ValueError('既有重导入未完整通过')
    for key in ('backend', 'frontend_unit', 'browser_offline', 'browser_live', 'browser_login', 'legacy_reimport', 'live_readonly', 'install', 'typecheck', 'build'):
        if summary[key]['exit_code'] != 0:
            raise ValueError('命令退出非零：' + key)
    build = (ROOT / summary['build']['report']).read_text(encoding='utf-8-sig')
    if not re.search(r'built in ', build):
        raise ValueError('缺少实际构建完成输出')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--base', required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    summary = json.loads((ROOT / args.summary).read_text(encoding='utf-8'))
    verify(summary)
    target = ROOT / args.manifest
    audit.MANIFEST = target
    if args.check:
        saved = json.loads(target.read_text(encoding='utf-8'))
        paths = [f['path'] for f in saved['files']]
    else:
        if target.exists():
            parser.error('快照已存在，请使用新轮次路径')
        names = audit.git('diff', '--name-only', args.base) + audit.git('ls-files', '--others', '--exclude-standard')
        paths = sorted({p for p in names if p.startswith(('frontend/', 'app/', 'tests/', 'scripts/', 'docs/')) or p in {'.gitignore', '.env.example', 'README.md', 'THIRD_PARTY_NOTICES.md'}})
        paths = [p for p in paths if p != args.manifest.as_posix() and (ROOT / p).is_file()]
    if any(p.startswith(('evals/', 'docs/development/evidence/')) or '/node_modules/' in p for p in paths):
        raise ValueError('快照含禁止上传范围')
    files, links, py = audit.validate_files(paths)
    # 构建产物单独扫描，只有结果与hash进入摘要，产物不上传。
    bundle = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'frontend/dist').rglob('*') if p.suffix in {'.js', '.mjs', '.html', '.css'}]
    if not bundle:
        raise ValueError('缺少实际构建产物')
    audit.validate_files(bundle)
    from dotenv import dotenv_values
    values = [v.encode() for k, v in dotenv_values(ROOT / '.env').items() if v and len(v) >= 9 and any(t in k.upper() for t in ('API_KEY', 'SECRET', 'PASSWORD', 'TOKEN', 'PRIVATE_KEY'))]
    trace = ROOT / summary['browser_live']['trace']
    with ZipFile(trace) as archive:
        for name in archive.namelist():
            data = archive.read(name)
            if any(value in data for value in values):
                raise ValueError('真实浏览器trace含本机后端敏感配置值，不输出内容')
    if args.check:
        if files != saved['files'] or links != saved['links']:
            raise ValueError('源码或链接已偏离选定提交快照')
    else:
        saved = {'notice': 'M3执行提交快照，非总控通过；原证据仅本机保留。自身hash不循环记录。',
                 'baseline_commit': args.base, 'pre_submission_head': audit.git('rev-parse', 'HEAD')[0],
                 'summary': args.summary.as_posix(), 'file_count': len(files), 'python_syntax_files': py,
                 'typescript_vue_files': sum(Path(p).suffix in {'.ts', '.vue'} for p in paths),
                 'checked_markdown_links': len(links), 'bundle_secret_scan_files': len(bundle),
                 'secret_scan': '未匹配本机敏感配置值；浏览器真实外部供应商请求为0', 'files': files, 'links': links}
        target.write_text(json.dumps(saved, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({'passed': True, 'files': len(files), 'python_syntax': py, 'links': len(links),
                      'bundle_secret_scan_files': len(bundle), 'backend_passed': summary['backend']['passed'],
                      'frontend_unit_passed': summary['frontend_unit']['passed'], 'browser_offline_passed': summary['browser_offline']['passed']}))


if __name__ == '__main__':
    main()
