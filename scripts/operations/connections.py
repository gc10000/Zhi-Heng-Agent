"""命令行静默消费显式服务配置；不枚举或打印凭据。"""
import os
from contextlib import contextmanager

from scripts.operations.snapshot import Namespace


def namespace():
    return Namespace(os.environ['M2_DB_NAME'], os.environ['M2_OBJECT_BUCKET'],
                     os.environ['M2_MILVUS_COLLECTION'], os.environ['M2_OBJECT_PREFIX'])


@contextmanager
def connections():
    from pymongo import MongoClient
    from minio import Minio
    from pymilvus import MilvusClient
    mongo = MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000, tz_aware=True)
    vectors = MilvusClient(uri=os.environ['MILVUS_URL'], timeout=10)
    objects = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'],
                    secret_key=os.environ['MINIO_SECRET_KEY'], secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
    try:
        yield mongo, objects, vectors
    finally:
        mongo.close()
        vectors.close()


def environment(path):
    if path:
        from dotenv import load_dotenv
        load_dotenv(path, override=True)
