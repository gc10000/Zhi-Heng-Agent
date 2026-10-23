"""Mongo standalone注册表：单文档原子幂等/CAS，不依赖跨集合事务。"""
from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError
from app.knowledge.models import Document, Revision, stable_id, content_hash
import json


class ConflictError(RuntimeError):
    pass


class ScopeError(LookupError):
    pass


def fingerprint(value):
    return content_hash(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode())


class KnowledgeRepository:
    def __init__(self, db, *, kb_id: str, owner_id: str):
        if not kb_id or not owner_id:
            raise ValueError('仓储必须明确知识库与归属范围')
        self.db,self.kb_id,self.owner_id=db,kb_id,owner_id
        self.scope={'kb_id':kb_id,'owner_id':owner_id}
        self.documents=db['knowledge_documents']
        self.revisions=db['knowledge_revisions']
        self.documents.create_index([('kb_id',1),('owner_id',1),('request_id',1)],unique=True)
        self.documents.create_index('document_id',unique=True)
        self.revisions.create_index([('document_id',1),('request_id',1)],unique=True)
        self.revisions.create_index('revision_id',unique=True)

    @staticmethod
    def _insert_once(collection, key, data):
        try:
            collection.update_one(key,{'$setOnInsert':data},upsert=True)
        except DuplicateKeyError:
            # 并发upsert竞争后读取唯一胜者，不能覆盖其内容。
            pass
        saved=collection.find_one(key)
        if saved is None or saved['request_fingerprint']!=data['request_fingerprint']:
            raise ConflictError('同一幂等键内容冲突')
        return saved

    def register_document(self, request_id: str, *, name: str, product_ids=(), purpose='unknown') -> Document:
        if not request_id:
            raise ValueError('注册必须提供幂等键')
        fields=dict(name=name,product_ids=tuple(product_ids),purpose=purpose)
        d=Document(**self.scope,document_id=stable_id('document',self.kb_id,[self.owner_id,request_id]),**fields)
        data=d.model_dump(mode='json') | {'request_id':request_id,'request_fingerprint':fingerprint(fields)}
        saved=self._insert_once(self.documents,self.scope|{'request_id':request_id},data)
        return Document(**{key:saved[key] for key in Document.model_fields})

    def get_document(self, document_id):
        value=self.documents.find_one(self.scope|{'document_id':document_id})
        if value is None:
            raise ScopeError('资料不存在或不在授权范围')
        return value

    def create_revision(self, document_id, request_id, *, original_sha256, object_key, parser_version='unparsed') -> Revision:
        self.get_document(document_id)
        if not request_id:
            raise ValueError('修订必须提供幂等键')
        r=Revision(**self.scope,document_id=document_id,revision_id=stable_id('revision',document_id,[request_id]),
                   original_sha256=original_sha256,object_key=object_key,parser_version=parser_version)
        data=r.model_dump(mode='json')
        data.update(request_id=request_id,request_fingerprint=fingerprint(data),stages={})
        saved=self._insert_once(self.revisions,self.scope|{'document_id':document_id,'request_id':request_id},data)
        return Revision(**{key:saved[key] for key in Revision.model_fields})

    def get_revision(self, revision_id):
        value=self.revisions.find_one(self.scope|{'revision_id':revision_id})
        if value is None:
            raise ScopeError('修订不存在或不在授权范围')
        return value

    def claim_attempt(self, revision_id, *, expected_attempt):
        value=self.revisions.find_one_and_update(self.scope|{'revision_id':revision_id,'attempt':expected_attempt,'status':{'$in':['staged','failed']}},
            {'$inc':{'attempt':1},'$set':{'status':'staged'}},return_document=ReturnDocument.AFTER)
        if value is None:
            raise ConflictError('处理attempt已过期或修订不可重试')
        return value['attempt']

    def save_stage(self, revision_id, *, attempt, stage, manifest):
        if not stage or any(c in stage for c in '.$'):
            raise ValueError('非法阶段名称')
        result=self.revisions.update_one(self.scope|{'revision_id':revision_id,'attempt':attempt,'status':'staged'},
            {'$set':{'stages.'+stage:manifest}})
        if not result.matched_count:
            raise ConflictError('过期attempt不可写入阶段')

    def get_active_revisions(self):
        return [{key:d[key] for key in ('document_id','active_revision_id')}
                for d in self.documents.find(self.scope|{'active_revision_id':{'$ne':None}})]

    def reconcile(self):
        """只核对不静默修复；后续发布依据活动指针恢复状态，失败不删除原修订。"""
        problems=[]
        for d in self.documents.find(self.scope):
            rid=d.get('active_revision_id')
            if rid and not self.revisions.find_one(self.scope|{'document_id':d['document_id'],'revision_id':rid}):
                problems.append({'code':'missing_active_revision','document_id':d['document_id'],'revision_id':rid})
        return problems
