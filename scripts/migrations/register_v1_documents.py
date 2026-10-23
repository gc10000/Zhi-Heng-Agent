"""只读迁移清点；清单来自人工核对的旧源身份，绝不按文件名合并。"""
import argparse
import json
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from app.knowledge.migration import plan_migration


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run',action='store_true',required=True)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--owner-id',default='migration-review')
    parser.add_argument('--kb-id',default='migration-review')
    parser.add_argument('--output',type=Path)
    args=parser.parse_args(argv)
    if args.manifest is None:
        report={'ready':False,'writes':0,'missing':['--manifest：旧源身份、原件key/hash、chunk_ids清单；详见迁移runbook']}
    else:
        records=json.loads(args.manifest.read_text(encoding='utf-8'))
        report=plan_migration(records,owner_id=args.owner_id,kb_id=args.kb_id)
    text=json.dumps(report,ensure_ascii=False,indent=2)
    if args.output:args.output.write_text(text,encoding='utf-8')
    print(text)
    return 0 if report['ready'] else 2


if __name__=='__main__':raise SystemExit(main())
