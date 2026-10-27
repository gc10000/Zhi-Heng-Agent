"""显式选择本轮摘要/快照；只核对文件、原证据、语法及实际计数，不读取私有账号。"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET
from scripts.verification import build_m1_artifacts as audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--create', action='store_true')
    args = parser.parse_args()
    summary_path, manifest_path = audit.ROOT / args.summary, audit.ROOT / args.manifest
    audit.MANIFEST = manifest_path
    summary = json.loads(summary_path.read_text('utf-8'))
    for item in summary['raw_evidence']:
        assert audit.sha(audit.ROOT/item['path']) == item['sha256'], item['path']
    for item in summary['pytest_reports']:
        suites = list(ET.parse(audit.ROOT/item['path']).getroot().iter('testsuite'))
        counts = {key: sum(int(s.attrib.get(key, 0)) for s in suites)
                  for key in ('tests', 'failures', 'errors', 'skipped')}
        assert counts == item['counts'], item['path']
    commands = json.loads((audit.ROOT/summary['stage_commands']).read_text('utf-8'))
    assert commands['passed'] and all(c['exit_code'] == 0 for c in commands['checks'])
    if args.create:
        if manifest_path.exists():
            parser.error('保留原快照，请显式选择全新名称')
        paths = summary['snapshot_paths']
    else:
        saved = json.loads(manifest_path.read_text('utf-8'))
        paths = [row['path'] for row in saved['files']]
    files, links, syntax = audit.validate_files(paths)
    if args.create:
        manifest_path.write_text(json.dumps(dict(
            notice='M6局部补修快照；不表示人工校准、答案质量或阶段验收通过。',
            summary=args.summary.as_posix(), baseline_commit=summary['baseline_commit'],
            file_count=len(files), python_syntax_files=syntax, checked_markdown_links=len(links),
            files=files, links=links), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    else:
        assert saved['files'] == files
        assert saved['links'] == links
    print(json.dumps(dict(passed=True,files=len(files),python_syntax=syntax,links=len(links),
        evidence_hashes=len(summary['raw_evidence']),stage_passed=summary['stage']['passed'],
        human_writes=summary['human_writes'],model_calls=summary['model_calls'])))


if __name__ == '__main__':
    main()
