"""按显式规格检查本轮哈希、实际测试输出、状态及链接；不固化旧测试数或失败状态。"""
import argparse
import ast
import json
from pathlib import Path
import re

from build_m0_review_artifacts import ROOT, make_manifest, read_json, sha


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--spec', type=Path, required=True)
    args = parser.parse_args()
    spec = read_json(args.spec)
    manifest = read_json(ROOT / spec['manifest_output'])
    assert manifest == make_manifest(spec), '快照与当前选定证据/清单不一致'
    for test in manifest['tests']:
        text = (ROOT / test['evidence']).read_text(encoding='utf-8-sig')
        if test['exit_code'] == 0:
            pattern = r'(\d+) passed' if test['label'] == 'pytest' else r'Ran (\d+) tests?'
            match = re.search(pattern, text)
            assert match and int(match[1]) == test['passed'], '实际数量不一致'
            if test['label'] == 'reimport':
                assert 'OK' in text
    for path in manifest['evidence']:
        assert (ROOT / path).is_file(), path
    inventory = read_json(ROOT / f'docs/development/evidence/{spec["artifact_prefix"]}-file-inventory.json')
    code_count = 0
    for item in inventory:
        path = ROOT / item['path']
        assert sha(path) == item['sha256'], item['path']
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8'), filename=item['path'])
            code_count += 1
    submission = ROOT / spec['submission']
    links = re.findall(r'\]\(([^)]+)\)', submission.read_text(encoding='utf-8'))
    for link in links:
        if not link.startswith(('https://', 'http://')):
            assert (submission.parent / link).resolve().exists(), link
    print(json.dumps({'status': 'passed', 'scope': 'artifact_only', 'python_files_parsed': code_count,
                      'hashes_verified': len(inventory), 'submission_links_checked': len(links),
                      'M0_09': manifest['task_status'].get('M0-09'),
                      'test_counts': [r['passed'] for r in manifest['tests']], 'review': manifest['review']}, ensure_ascii=True))


if __name__ == '__main__':
    main()
