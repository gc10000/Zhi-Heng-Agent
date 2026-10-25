"""显式选择M5摘要和快照，核对真实JUnit及产物hash；禁止覆盖已有快照。"""
import argparse
import json
from pathlib import Path


def main():
    from scripts.verification.build_m4_artifacts import verify_summary, relative_path
    from scripts.verification import build_m1_artifacts as audit
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--base',required=True)
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    root=Path(__file__).resolve().parents[2]
    summary=verify_summary(args.summary,root=root)
    if summary.get('stage')!='M5' or summary.get('review_status')!='待审查':
        raise ValueError('只能建立M5待审查执行快照，不能自标总控通过')
    evidence={relative_path(root,row['path']) for row in summary['raw_evidence']}
    for report_name in summary['command_ledgers']:
        report_path=relative_path(root,report_name)
        if report_path not in evidence:
            raise ValueError('逐命令账本未绑定原件hash')
        report=json.loads(report_path.read_text('utf-8'))
        if not report['passed'] or any(row['exit_code']!=0 for row in report['checks']):
            raise ValueError('逐命令账本存在未通过项')
    frontend=summary['frontend']
    for key in ('unit_report','browser_report'):
        if relative_path(root,frontend[key]) not in evidence:
            raise ValueError('前端报告未绑定原件hash')
    unit=json.loads(relative_path(root,frontend['unit_report']).read_text('utf-8'))
    browser=json.loads(relative_path(root,frontend['browser_report']).read_text('utf-8'))['stats']
    if (unit['numPassedTests']!=frontend['unit_passed'] or unit['numFailedTests'] or unit['numPendingTests']
            or browser['expected']!=frontend['browser_passed']
            or any(browser[key] for key in ('skipped','unexpected','flaky'))):
        raise ValueError('前端摘要与实际结果不符或存在未通过项')
    target=relative_path(root,args.manifest)
    if not target.is_relative_to(root/'docs/development/reviews'):
        parser.error('快照仅能写入reviews目录')
    audit.MANIFEST=target
    if args.check:
        saved=json.loads(target.read_text('utf-8'))
        if saved['summary']!=args.summary.as_posix() or saved['baseline_commit']!=args.base:
            raise ValueError('快照与显式摘要/基线不匹配')
        paths=[row['path'] for row in saved['files']]
    else:
        if target.exists():
            parser.error('快照已存在，必须选择新路径，禁止覆盖')
        names=audit.git('diff','--name-only',args.base)+audit.git('ls-files','--others','--exclude-standard')
        paths=sorted({name for name in names if (name.startswith(('app/','tests/','scripts/','docs/','frontend/'))
                      or name in {'README.md','.env.example','.gitignore','THIRD_PARTY_NOTICES.md'})
                      and name!=args.manifest.as_posix() and (root/name).is_file()})
    if any(name.startswith(('evals/','output/','docs/development/evidence/','frontend/test-results/','frontend/node_modules/','frontend/dist/')) for name in paths):
        raise ValueError('提交范围包含私有原始产物或构建目录')
    files,links,syntax=audit.validate_files(paths)
    if args.check:
        if saved['files']!=files or saved['links']!=links:
            raise ValueError('源码/文档与提交快照不符')
    else:
        saved={'notice':'M5执行提交快照，不代表总控通过；原始证据仅留本机。',
               'summary':args.summary.as_posix(),'baseline_commit':args.base,'pre_submission_head':audit.git('rev-parse','HEAD')[0],
               'file_count':len(files),'python_syntax_files':syntax,'checked_markdown_links':len(links),
               'files':files,'links':links,'secret_scan':'未匹配本机敏感配置值'}
        with target.open('x',encoding='utf-8') as output:
            json.dump(saved,output,ensure_ascii=False,indent=2)
    print(json.dumps({'passed':True,'files':len(files),'python_syntax':syntax,'links':len(links),
                      'stage_passed':summary['tests'][0]['passed'],'private_evidence_hashed':len(summary['raw_evidence'])}))


if __name__=='__main__':
    main()
