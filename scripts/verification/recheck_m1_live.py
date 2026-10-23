"""只读复核已有真实M1发布产物；不调用模型或供应商，不覆盖原报告。"""
import argparse
import json
import os
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--report',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():parser.error('输出已存在，保留历史使用新路径')
    source=json.loads(args.report.read_text(encoding='utf-8'))
    if not source['passed'] or not source['db'].startswith('m1_test_') or not source['collection'].startswith('m1_test_'):parser.error('只接受已保存的隔离真实报告')
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2]/'.env')
    from pymongo import MongoClient
    from pymilvus import MilvusClient
    from minio import Minio
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.index import V2Index
    from app.knowledge.originals import OriginalStore
    from app.knowledge.assets import AssetStore
    from app.knowledge.publishing import RevisionPublisher
    from app.knowledge.models import content_hash
    mongo=MongoClient(os.environ['MONGO_URL']);milvus=MilvusClient(uri=os.environ['MILVUS_URL'])
    objects=Minio(os.environ['MINIO_ENDPOINT'],access_key=os.environ['MINIO_ACCESS_KEY'],secret_key=os.environ['MINIO_SECRET_KEY'],secure=os.getenv('MINIO_SECURE','').lower()=='true')
    checks=[]
    try:
        db=mongo[source['db']];first=db.knowledge_revisions.find_one({'revision_id':source['documents'][0]['revision_id']})
        repo=KnowledgeRepository(db,kb_id=first['kb_id'],owner_id=first['owner_id'])
        index=V2Index(milvus,source['collection'])
        prefix=first['object_key'].split('originals/')[0]
        originals=OriginalStore(objects,bucket=os.environ['MINIO_BUCKET_NAME'],prefix=prefix)
        assets=AssetStore(db,objects,bucket=os.environ['MINIO_BUCKET_NAME'],prefix=prefix+'assets/')
        publisher=RevisionPublisher(repo,index,read_original=originals.read,asset_store=assets)
        for item in source['documents']:
            r=repo.get_revision(item['revision_id'])
            assert r['status']=='published' and repo.get_document(r['document_id'])['active_revision_id']==r['revision_id']
            assert publisher.inspect(r)==r['validation']
            rows=index.revision_rows(repo,r['revision_id']);assert len(rows)==item['chunks']
            checks.append({'revision_id':r['revision_id'],'original_hash':True,'vectors_and_sources':True,'chunks':len(rows)})
            if any(row['metadata']['asset_ids'] for row in rows):
                aid=next(row['metadata']['asset_ids'][0] for row in rows if row['metadata']['asset_ids'])
                asset,data=assets.read(aid);assert content_hash(data)==source['image_sha256']
                assert asset['description']==source['image_description']
                assert db.image_summary_cache.find_one({'_id':asset['description_cache_key'],'status':'completed'})['text']==asset['description']
        report={'passed':True,'read_only_business_data':True,'provider_calls':0,'checks':checks,'image_hash_decode_description_link':True,
                'source_report_sha256':content_hash(args.report.read_bytes())}
        args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(report,ensure_ascii=True))
    finally:mongo.close();milvus.close()


if __name__=='__main__':main()
