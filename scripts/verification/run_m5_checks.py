"""逐命令保存退出码及原始输出，不让后一条命令掩盖失败；不覆盖旧目录。"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--group', choices=['backend','frontend','all'], default='all')
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists() or not output.is_relative_to(ROOT / 'output'):
        parser.error('必须选择output下不存在的新目录')
    output.mkdir(parents=True)
    env = dict(os.environ)
    for key in ('M3_LIVE_CONFIG','M5_LIVE_CONFIG','M5_UI_BASE'):
        env.pop(key, None)
    env['M1_TEST_DB'] = 'm1_test_m4_m5_stage_' + uuid4().hex[:8]
    env['PLAYWRIGHT_JSON_OUTPUT_NAME'] = str(output / 'browser.json')
    pnpm = shutil.which('pnpm')
    commands = []
    if args.group in {'all','backend'}:
        commands.extend([
            ('backend', [sys.executable, '-m', 'pytest', 'tests/unit','tests/contract','tests/integration',
                         '-m', 'not live_provider','-q','--tb=short','--junitxml='+str(output/'backend.xml')]),
            ('reimport',[sys.executable,'-m','unittest','discover','-s','test','-p','test_document_reimport.py','-v'])])
    if args.group in {'all','frontend'}:
        commands.extend([
            ('typecheck',[pnpm,'-C','frontend','typecheck']),
            ('unit',[pnpm,'-C','frontend','exec','vitest','run','--reporter=json','--outputFile='+str(output/'unit.json')]),
            ('build',[pnpm,'-C','frontend','build']),
            ('browser',[pnpm,'-C','frontend','exec','playwright','test','--reporter=list,json','--output='+str(output/'browser-artifacts')])])
    report = {'checks': [], 'database_prefix': env['M1_TEST_DB'], 'passed': False}
    for name, command in commands:
        began = time.monotonic()
        with (output / (name+'.txt')).open('xb') as log:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
        report['checks'].append({'name':name,'command':command,'exit_code':result.returncode,'seconds':round(time.monotonic()-began,3)})
        (output/'commands.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'name':name,'exit_code':result.returncode}),flush=True)
    report['passed'] = all(row['exit_code']==0 for row in report['checks'])
    (output/'commands.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
