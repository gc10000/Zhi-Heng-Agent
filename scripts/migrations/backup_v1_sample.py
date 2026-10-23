"""显式隔离小样的备份/恢复演练入口；所有快照仅保存在本机。"""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    backup=sub.add_parser('backup');backup.add_argument('--manifest',type=Path,required=True)
    backup.add_argument('--source-db',required=True);backup.add_argument('--mongo-collection',required=True);backup.add_argument('--milvus-collection',required=True)
    backup.add_argument('--active-snapshot',type=Path,required=True);backup.add_argument('--directory',type=Path,required=True)
    restore=sub.add_parser('restore');restore.add_argument('--snapshot',type=Path,required=True)
    restore.add_argument('--target-db',required=True);restore.add_argument('--milvus-collection',required=True);restore.add_argument('--prefix',required=True)
    args=parser.parse_args(argv)
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2]/'.env')
    from pymongo import MongoClient
    from pymilvus import MilvusClient
    from minio import Minio
    from app.knowledge.migration import backup_selection,restore_sample,plan_migration
    if args.command=='backup' and not args.source_db.startswith('m1_test_'):parser.error('当前只验收隔离源，禁止读全课程库')
    if args.command=='restore' and (not args.target_db.startswith('m1_test_') or not args.milvus_collection.startswith('m1_test_')):parser.error('恢复目标必须m1_test_')
    mongo=MongoClient(os.environ['MONGO_URL']);milvus=MilvusClient(uri=os.environ['MILVUS_URL'])
    objects=Minio(os.environ['MINIO_ENDPOINT'],access_key=os.environ['MINIO_ACCESS_KEY'],secret_key=os.environ['MINIO_SECRET_KEY'],secure=os.getenv('MINIO_SECURE','').lower()=='true')
    try:
        if args.command=='backup':
            records=json.loads(args.manifest.read_text(encoding='utf-8'))
            if not plan_migration(records,owner_id='backup',kb_id='backup')['ready']:parser.error('清单有缺失或碰撞')
            if not 1<=len(records)<=3:parser.error('本阶段仅1至3份小样')
            report=backup_selection(records,mongo_collection=mongo[args.source_db][args.mongo_collection],milvus=milvus,collection=args.milvus_collection,
                objects=objects,bucket=os.environ['MINIO_BUCKET_NAME'],directory=args.directory,active_snapshot=json.loads(args.active_snapshot.read_text(encoding='utf-8')))
            print(json.dumps({'snapshot_sha256':report['snapshot_sha256'],'documents':len(records)}))
        else:
            snapshot=json.loads(args.snapshot.read_text(encoding='utf-8'))
            report=restore_sample(snapshot,directory=args.snapshot.parent,mongo_collection=mongo[args.target_db]['legacy_restore'],milvus=milvus,index=args.milvus_collection,
                objects=objects,bucket=os.environ['MINIO_BUCKET_NAME'],prefix=args.prefix)
            print(json.dumps({k:report[k] for k in ('verified','snapshot_sha256','documents','vectors','objects')}))
    finally:mongo.close();milvus.close()
    return 0


if __name__=='__main__':raise SystemExit(main())
