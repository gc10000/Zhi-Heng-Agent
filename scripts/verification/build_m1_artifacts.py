"""M1源码快照与本机证据hash检查；结果数量来自实际摘要，不固化测试总数。"""
import argparse
import ast
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
MANIFEST=ROOT/'docs/development/reviews/M1-artifact-manifest.json'
SUMMARY=ROOT/'docs/development/reviews/M1-validation-summary.json'
BASE='0a409294c173601898c847ee962938b155f98d45'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,text=True,encoding='utf-8').splitlines()


def verify_results():
    import xml.etree.ElementTree as ET
    summary=json.loads(SUMMARY.read_text(encoding='utf-8'))
    for evidence in summary['raw_evidence']:
        if sha(ROOT/evidence['path'])!=evidence['sha256']:raise ValueError('原始证据hash变化：'+evidence['path'])
    suite=ET.parse(ROOT/summary['stage'].get('junit','docs/development/evidence/M1-stage-final.xml')).getroot().find('testsuite')
    if any(int(suite.attrib[k]) for k in ('errors','failures','skipped')):raise ValueError('阶段实际结果含未通过项')
    if int(suite.attrib['tests'])!=summary['stage']['passed']:raise ValueError('摘要与JUnit实际测试数不符')
    if any(summary[key]['exit_code'] for key in ('stage','legacy_reimport','live','current_code_live_recheck')):raise ValueError('存在非零退出')
    return summary


def validate_files(paths):
    files=[];links=[];python_count=0
    for name in paths:
        path=ROOT/name;data=path.read_bytes()
        files.append({'path':name,'sha256':sha(path),'bytes':len(data)})
        if path.suffix=='.py':ast.parse(data.decode('utf-8-sig'),filename=name);python_count+=1
        if path.suffix=='.md':
            for target in re.findall(r'\]\(([^)]+)\)',data.decode('utf-8-sig')):
                target=target.split('#')[0].strip('<>')
                if not target or target.startswith(('http:','https:','mailto:','app:')):continue
                destination=path.parent/target
                if destination.resolve()!=MANIFEST.resolve() and not destination.exists():raise ValueError('链接目标缺失：'+name+' -> '+target)
                links.append({'source':name,'target':target})
    from dotenv import dotenv_values
    for key,value in dotenv_values(ROOT/'.env').items():
        if not value or len(value)<9 or not any(t in key.upper() for t in ('API_KEY','SECRET','PASSWORD','TOKEN','PRIVATE_KEY')):continue
        if any(value.encode() in (ROOT/f['path']).read_bytes() for f in files):raise ValueError('候选文件含真实敏感值，变量名：'+key)
    return files,links,python_count


def main():
    global MANIFEST,SUMMARY,BASE
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--check',action='store_true')
    parser.add_argument('--manifest',type=Path,default=MANIFEST)
    parser.add_argument('--summary',type=Path,default=SUMMARY)
    parser.add_argument('--base',default=BASE)
    args=parser.parse_args()
    MANIFEST=ROOT/args.manifest;SUMMARY=ROOT/args.summary;BASE=args.base
    summary=verify_results()
    if args.check:
        saved=json.loads(MANIFEST.read_text(encoding='utf-8'));paths=[f['path'] for f in saved['files']]
    else:
        if MANIFEST.exists():parser.error('快照已存在，保留原文件；需要新审查轮次时建立新名称')
        changed=git('diff','--name-only',BASE)
        new=[p for p in git('ls-files','--others','--exclude-standard') if p.startswith(('app/','docs/','scripts/','tests/'))]
        paths=sorted(set(changed+new)-{MANIFEST.relative_to(ROOT).as_posix()})
    files,links,py=validate_files(paths)
    if args.check:
        if files!=saved['files']:raise ValueError('文件快照与工作区不一致')
    else:
        saved={'notice':'M1提交时点快照，仅相对源码路径/hash及脱敏检查；原始证据留本机，自身hash不循环记录。',
               'baseline_commit':BASE,'pre_submission_head':git('rev-parse','HEAD')[0],'file_count':len(files),'python_syntax_files':py,
               'checked_markdown_links':len(links),'secret_scan':'未匹配本机敏感配置值','files':files,'links':links}
        MANIFEST.write_text(json.dumps(saved,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':True,'files':len(files),'python_syntax':py,'links':len(links),'stage_passed':summary['stage']['passed'],'secret_scan_passed':True}))


if __name__=='__main__':main()
