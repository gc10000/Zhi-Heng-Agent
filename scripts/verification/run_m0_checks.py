"""保存实际退出码和动态测试数量，为每轮审查生成独立证据，不覆盖旧轮次。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prefix', required=True, help='本轮新证据前缀，如 M0-r2')
    args = parser.parse_args()
    if not re.fullmatch(r'M0-[a-zA-Z0-9-]+', args.prefix):
        parser.error('必须使用独立的 M0 证据前缀')
    evidence = ROOT / 'docs/development/evidence'
    summary_path = evidence / f'{args.prefix}-validation.json'
    if summary_path.exists():
        parser.error('该轮验证已存在，请使用新前缀，保留原结果')
    env = {**os.environ, 'LOG_CONSOLE_ENABLE': 'False', 'LOG_FILE_ENABLE': 'False',
           'PYTHONIOENCODING': 'utf-8'}
    results = []
    commands = [('pytest', ['-m', 'pytest', 'tests/unit', 'tests/contract', '-q']),
                ('reimport', ['-m', 'unittest', 'discover', '-s', 'test', '-p', 'test_document_reimport.py', '-q'])]
    for label, params in commands:
        path = evidence / f'{args.prefix}-{label}.txt'
        if path.exists():
            parser.error('输出证据已存在，请使用新前缀')
        command = [sys.executable, *params]
        result = subprocess.run(command, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        path.write_bytes(result.stdout)
        output = result.stdout.decode('utf-8', errors='replace')
        match = re.search(r'(\d+) passed', output) if label == 'pytest' else re.search(r'Ran (\d+) tests?', output)
        record = {'label': label, 'command': ['.venv/Scripts/python.exe', *params],
                  'env_overrides': {k: env[k] for k in ('LOG_CONSOLE_ENABLE', 'LOG_FILE_ENABLE', 'PYTHONIOENCODING')},
                  'exit_code': result.returncode, 'passed': int(match[1]) if match else None,
                  'evidence': path.relative_to(ROOT).as_posix(),
                  'evidence_sha256': hashlib.sha256(result.stdout).hexdigest(), 'fake_io': True}
        results.append(record)
        summary_path.write_text(json.dumps({'runs': results}, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps(record, ensure_ascii=True), flush=True)
    return 0 if all(r['exit_code'] == 0 and r['passed'] is not None for r in results) else 1


if __name__ == '__main__':
    raise SystemExit(main())
