"""评测语料只读资源；不构造带create_index副作用的业务仓储。"""
from contextlib import contextmanager
import os
from types import SimpleNamespace
from .query_adapter import validate_target
from .validate_dataset import fingerprint, file_sha


@contextmanager
def open_frozen_corpus(config):
    validate_target(config)
    from dotenv import load_dotenv
    load_dotenv()
    from .versions import runtime_versions
    if config['versions'] != runtime_versions():
        raise ValueError('实际代码、模型或prompt与本轮配置不一致')
    if not config.get('dataset_acceptance') or any(file_sha(r['path']) != r['sha256'] for r in config['dataset_acceptance']):
        raise ValueError('题集接受结论缺失或变动')
    from pymongo import MongoClient
    from pymilvus import MilvusClient
    from minio import Minio
    from app.knowledge.index import V2Index
    from app.knowledge.originals import OriginalStore
    from .corpus import corpus_snapshot, validate_asset_equivalences
    t = config['target']
    mongo = MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000, tz_aware=True)
    milvus = None
    try:
        milvus = MilvusClient(uri=os.environ['MILVUS_URL'])
        db = mongo[t['database']]
        scope = dict(owner_id=t['owner_id'], kb_id=t['kb_id'])
        class Repo:
            owner_id, kb_id = t['owner_id'], t['kb_id']
            def get_revision(self, rid):
                row = db.knowledge_revisions.find_one(scope | dict(revision_id=rid))
                if not row or row['status'] != 'published': raise ValueError('修订不在已发布授权范围')
                return row
            def get_active_revisions(self):
                return [dict(document_id=d['document_id'], active_revision_id=d['active_revision_id'])
                    for d in db.knowledge_documents.find(scope) if d.get('active_revision_id')]
        repo = Repo()
        index = V2Index(milvus, t['collection'])
        objects = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'],
            secret_key=os.environ['MINIO_SECRET_KEY'], secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
        g = SimpleNamespace(db=db, owner_id=t['owner_id'], repo=lambda kb: repo, index=lambda: index,
            products=SimpleNamespace(collection=db.knowledge_products), product_kbs=db.knowledge_product_kbs,
            originals=OriginalStore(objects, bucket=t['bucket'], prefix=t['object_prefix']))
        expected = {(d['document_id'], d['revision_id']) for d in config['corpus']['documents']}
        def verify():
            if expected != {(d['document_id'], d['active_revision_id']) for d in repo.get_active_revisions()}:
                raise ValueError('活动修订已漂移')
            actual = corpus_snapshot(g, t, config['corpus']['documents'], expected=config['corpus']['snapshot'])
            if fingerprint(actual) != fingerprint(config['corpus']['snapshot']): raise ValueError('完整语料快照漂移')
            validate_asset_equivalences(actual, config['corpus'].get('asset_equivalences', []))
            return fingerprint(actual)
        g.verify = verify
        g.corpus_sha256 = verify()
        yield g
        verify()
    finally:
        if milvus is not None: milvus.close()
        mongo.close()
