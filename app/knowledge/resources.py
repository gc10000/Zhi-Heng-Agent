"""按需建立知识服务客户端，读取目录不要求模型或对象存储在线。"""
import os
import threading
from app.api.errors import APIError
from app.knowledge.gateway import KnowledgeGateway
from app.knowledge.originals import OriginalStore


def missing(names, purpose):
    raise APIError(503, 'configuration_missing', '请在根目录.env填写' + '、'.join(names) + '，用于' + purpose + '。')


class KnowledgeResources:
    def __init__(self, db, settings):
        self.db, self.settings = db, settings
        self.lock, self.gateway, self.milvus = threading.RLock(), None, None

    def get(self):
        with self.lock:
            if self.gateway is None:
                if not self.settings.knowledge_owner_id:
                    missing(['M2_KNOWLEDGE_OWNER_ID'], '共享知识归属')
                self.gateway = KnowledgeGateway(self.db, LazyOriginalStore(self.settings),
                    owner_id=self.settings.knowledge_owner_id, index_factory=self.index,
                    max_upload_bytes=self.settings.upload_max_bytes)
            return self.gateway

    def index(self):
        with self.lock:
            if not self.settings.milvus_collection or not os.getenv('MILVUS_URL'):
                missing(['M2_MILVUS_COLLECTION', 'MILVUS_URL'], '知识索引与修订发布')
            if self.settings.milvus_collection == os.getenv('CHUNKS_COLLECTION'):
                raise APIError(503, 'unsafe_collection', 'M2_MILVUS_COLLECTION必须与原课程集合分开。')
            from app.knowledge.index import V2Index
            from pymilvus import MilvusClient
            if self.milvus is None:
                self.milvus = MilvusClient(uri=os.environ['MILVUS_URL'])
            return V2Index(self.milvus, self.settings.milvus_collection)

    def close(self):
        if self.milvus is not None:
            self.milvus.close()


class LazyOriginalStore:
    def __init__(self, settings):
        self.settings, self.lock, self.instance = settings, threading.RLock(), None

    @property
    def prefix(self):
        prefix = self.settings.object_prefix
        if not prefix:
            missing(['M2_OBJECT_PREFIX'], '新知识对象隔离前缀')
        if prefix.startswith('/') or any(p in prefix for p in ('..', '\\', '//', '%')):
            raise APIError(503, 'unsafe_object_prefix', 'M2_OBJECT_PREFIX必须是规范相对对象前缀。')
        return prefix.rstrip('/') + '/'

    def _get(self):
        with self.lock:
            if self.instance is None:
                names = [n for n in ('MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY') if not os.getenv(n)]
                if not self.settings.object_bucket:
                    names.append('M2_OBJECT_BUCKET')
                if names:
                    missing(names, '上传原件与受控资产读取')
                from minio import Minio
                client = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'], secret_key=os.environ['MINIO_SECRET_KEY'],
                               secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
                self.instance = OriginalStore(client, bucket=self.settings.object_bucket, prefix=self.prefix)
            return self.instance

    def __getattr__(self, name):
        if name.startswith('_'):
            raise AttributeError(name)
        return getattr(self._get(), name)
