"""只缓存查询向量；范围完整绑定、TTL/LRU有界、退出代际保护，不缓存答案或检索正文。"""
import copy
import hashlib
import json
import threading
import time
from collections import OrderedDict
from concurrent.futures import Future

REQUIRED_SCOPE={'user_id','permissions','owner_id','kb_id','products','revisions','model','strategy'}


class ScopedEmbeddingCache:
    def __init__(self, *, clock=time.monotonic):
        self.clock=clock;self.lock=threading.Lock();self.entries=OrderedDict();self.inflight={};self.epochs={}

    def invalidate(self,user_id):
        with self.lock:
            self.epochs[user_id]=self.epochs.get(user_id,0)+1
            for key in [k for k,v in self.entries.items() if v[1]==user_id]:self.entries.pop(key)

    def get_or_compute(self,scope,texts,compute,policy):
        if not policy.cache_enabled:return compute(texts)
        if set(scope)!=REQUIRED_SCOPE:raise ValueError('查询缓存缺少完整授权/产品/修订/模型/策略范围')
        user=scope['user_id']
        with self.lock:
            epoch=self.epochs.get(user,0)
            raw=json.dumps([scope,texts,epoch,policy.model_dump()],sort_keys=True,ensure_ascii=False,separators=(',',':'))
            key=hashlib.sha256(raw.encode('utf-8')).hexdigest()
            now=self.clock()
            for expired in [k for k,v in self.entries.items() if v[0]<=now]:self.entries.pop(expired)
            if key in self.entries:
                value=self.entries.pop(key);self.entries[key]=value
                return copy.deepcopy(value[2])
            pending=self.inflight.get(key)
            creator=pending is None
            if creator:pending=Future();self.inflight[key]=pending
        if not creator:return copy.deepcopy(pending.result())
        try:
            value=compute(texts)
            stored=copy.deepcopy(value)
            with self.lock:
                if self.epochs.get(user,0)==epoch:
                    self.entries[key]=(self.clock()+policy.cache_ttl_seconds,user,stored)
                    while len(self.entries)>policy.cache_max_entries:self.entries.popitem(last=False)
                self.inflight.pop(key,None)
            pending.set_result(stored)
            return copy.deepcopy(stored)
        except BaseException as exc:
            with self.lock:self.inflight.pop(key,None)
            pending.set_exception(exc)
            raise


QUERY_EMBEDDINGS=ScopedEmbeddingCache()


def configured_model_identity():
    from app.conf.embedding_config import embedding_config
    import os
    # 只持久不可逆指纹；权重不是热替换资源，改模型/权重必须重启宿主。
    values=dict(path=embedding_config.bge_m3_path,device=embedding_config.bge_device,
        fp16=embedding_config.bge_fp16,host=os.getenv('MODEL_HOST_URL'),input_type='query')
    return hashlib.sha256(json.dumps(values,sort_keys=True).encode()).hexdigest()
