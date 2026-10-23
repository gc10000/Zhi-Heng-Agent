"""隔离小样迁移入口；不读取全课程库，不创建公开发布或服务器任务。"""
import argparse
import json
import os
import sys
from io import BytesIO
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from app.knowledge.migration import migrate_batch,read_object


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--snapshot',type=Path,required=True)
    parser.add_argument('--recovery-report',type=Path,required=True)
    parser.add_argument('--target-db',required=True)
    parser.add_argument('--collection',required=True)
    parser.add_argument('--owner-id',required=True)
    parser.add_argument('--kb-id',required=True)
    parser.add_argument('--apply',action='store_true',required=True)
    args=parser.parse_args(argv)
    if not args.target_db.startswith('m1_test_') or not args.collection.startswith('m1_test_'):parser.error('本阶段只允许m1_test_独立目标')
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2]/'.env')
    from pymongo import MongoClient
    from pymilvus import MilvusClient
    from minio import Minio
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.index import V2Index
    from app.knowledge.assets import AssetStore
    from app.knowledge.publishing import RevisionPublisher
    # 必须本地已有模型，不自动下载或升级。
    os.environ.update(HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',LOG_CONSOLE_ENABLE='False',LOG_FILE_ENABLE='False')
    from app.lm.embedding_utils import generate_embeddings
    snapshot=json.loads(args.snapshot.read_text(encoding='utf-8'));recovery=json.loads(args.recovery_report.read_text(encoding='utf-8'))
    from app.knowledge.migration import require_recovery,verify_snapshot
    require_recovery(snapshot,recovery);verify_snapshot(snapshot,args.snapshot.parent)
    mongo=MongoClient(os.environ['MONGO_URL']);milvus=MilvusClient(uri=os.environ['MILVUS_URL'])
    try:
        repo=KnowledgeRepository(mongo[args.target_db],kb_id=args.kb_id,owner_id=args.owner_id)
        index=V2Index(milvus,args.collection);index.ensure_collection()
        objects=Minio(os.environ['MINIO_ENDPOINT'],access_key=os.environ['MINIO_ACCESS_KEY'],secret_key=os.environ['MINIO_SECRET_KEY'],secure=os.getenv('MINIO_SECURE','').lower()=='true')
        bucket=os.environ['MINIO_BUCKET_NAME'];prefix='m1-test/'+args.target_db+'/'
        assets=AssetStore(repo.db,objects,bucket=bucket,prefix=prefix+'assets/')
        def write_original(did,digest,data):
            key=prefix+'originals/'+did+'/'+digest;objects.put_object(bucket,key,BytesIO(data),len(data));return key
        publisher=RevisionPublisher(repo,index,read_original=lambda r:read_object(objects,bucket,r['object_key']),asset_store=assets)
        result=migrate_batch(snapshot,recovery,directory=args.snapshot.parent,repo=repo,index=index,asset_store=assets,
                             write_original=write_original,publisher=publisher,embedder=generate_embeddings)
        print(json.dumps({'completed':len(result),'documents':[{'document_id':r['document_id'],'revision_id':r['revision_id']} for r in result]},ensure_ascii=False))
    finally:mongo.close();milvus.close()
    return 0


if __name__=='__main__':raise SystemExit(main())
