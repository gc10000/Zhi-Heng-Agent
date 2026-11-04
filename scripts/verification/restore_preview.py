"""实际预览停写备份、独立恢复、API绑定切换与回切；只操作随机合成项目。"""
import argparse
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
ROOT = Path(__file__).resolve().parents[2]


def run(env_file, runtime_env, browser_file, output):
    from scripts.operations.connections import environment, namespace
    from scripts.verification.load_support import login
    environment(env_file)
    source = namespace()
    project = os.environ['M7_PROJECT_NAME']
    if not re.fullmatch(r'zh-m7-[a-f0-9]{6}', project) or os.environ['M7_GENERATION_ENABLED'] != 'false':
        raise ValueError('只能切换本轮随机合成项目')
    from dotenv import dotenv_values
    runtime = dotenv_values(runtime_env)
    if any(runtime.get(k) != os.environ.get(k) for k in ('M7_PROJECT_NAME', 'M2_DB_NAME', 'M2_OBJECT_BUCKET', 'M2_MILVUS_COLLECTION')):
        raise ValueError('host/runtime绑定不符')
    browser = json.loads(Path(browser_file).read_text(encoding='utf-8'))
    assert browser['synthetic'] is True
    out = Path(output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    suffix = secrets.token_hex(3)
    target = dict(database='m1_test_m4_res_' + suffix, bucket='zh-restore-' + suffix,
                  collection='m1_test_m4_res_' + suffix + '_v2', prefix=source.prefix)
    base = ['docker', 'compose', '--env-file', str(Path(runtime_env).resolve()), '-f', 'compose.delivery.yaml', '-p', project]
    def command(args):
        result = subprocess.run(args, cwd=ROOT, text=True, capture_output=True, timeout=120)
        with (out / 'commands.log').open('a', encoding='utf-8') as log:
            log.write(' '.join(args) + '\n' + result.stdout + result.stderr + '\nexit=' + str(result.returncode) + '\n')
        result.check_returncode()
        return result.stdout
    def check():
        import requests
        with requests.Session() as probe:
            probe.trust_env = False
            status = None
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                try:
                    status = probe.get(browser['base_url'] + '/health/ready', timeout=12).status_code
                    if status == 200: break
                except requests.RequestException:
                    pass
                time.sleep(.5)
            assert status == 200
        session = login(browser['base_url'], browser['username'], browser['password'])
        try:
            path = '/api/v1/runs/' + browser['run_id'] + '/citations/engineering-source'
            citation = session.get(browser['base_url'] + path, timeout=15)
            assert citation.status_code == 200
            original = session.get(browser['base_url'] + citation.json()['original']['url'], headers={'Range': 'bytes=0-4'}, timeout=15)
            assert original.status_code == 206 and original.content == b'%PDF-'
            assert session.get(browser['base_url'] + '/api/v1/documents?kb_id=preview-kb', timeout=15).status_code == 200
        finally:
            session.close()
    command(base + ['stop', 'api', 'worker', 'dispatcher'])
    try:
        revision = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()
        receipt = json.loads(command([sys.executable, 'scripts/operations/backup.py', '--env-file', env_file,
                                      '--output', str(out / 'snapshot'), '--source-commit', revision]))
        restored = json.loads(command([sys.executable, 'scripts/operations/restore.py', '--env-file', env_file,
            '--input', str(out / 'snapshot'), '--manifest-sha256', receipt['manifest_sha256'],
            '--target-database', target['database'], '--target-bucket', target['bucket'],
            '--target-collection', target['collection'], '--prefix', target['prefix']]))
        override = out / 'restore-binding.json'
        override.write_text(json.dumps({'services': {'api': {'environment': {'M2_DB_NAME': target['database'],
            'M2_OBJECT_BUCKET': target['bucket'], 'M2_MILVUS_COLLECTION': target['collection']}}}}), encoding='utf-8')
        command(base + ['-f', str(override), 'up', '-d', '--no-deps', 'api'])
        check()
        command(base + ['up', '-d', '--no-deps', '--force-recreate', 'api'])
        check()
        result = dict(passed=True, backup=receipt, restored=restored, actual_api_target_read=True,
            actual_api_source_rollback_read=True, pdf_range_and_citation=True, model_calls=0,
            real_question_answer='not_executed', sessions_restored=False, source_data_not_overwritten=True)
        (out / 'result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
        return result
    finally:
        command(base + ['up', '-d', '--no-deps', 'api', 'worker', 'dispatcher'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('env-file', 'runtime-env', 'browser-file', 'output'):
        p.add_argument('--' + name, required=True)
    args = p.parse_args()
    print(json.dumps(run(args.env_file, args.runtime_env, args.browser_file, args.output), ensure_ascii=False))
