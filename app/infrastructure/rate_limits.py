"""使用Mongo原子预约全任务共享供应商限流，M1不提前接Redis。"""
import time
from pymongo.errors import DuplicateKeyError


class MongoRateStore:
    def __init__(self,db): self.collection=db['provider_rate_limits']
    def reserve(self,key,now,interval):
        try: self.collection.update_one({'_id':key},{'$setOnInsert':{'version':0,'next_at':0}},upsert=True)
        except DuplicateKeyError: pass
        for _ in range(100):
            current=self.collection.find_one({'_id':key});slot=max(now,current['next_at'])
            result=self.collection.update_one({'_id':key,'version':current['version']},{'$set':{'next_at':slot+interval},'$inc':{'version':1}})
            if result.matched_count:return slot
        raise RuntimeError('供应商限流预约竞争过高，请重试')


class SharedRateLimiter:
    def __init__(self,store,key,*,requests_per_minute=30,clock=time.time,sleep=time.sleep):
        if requests_per_minute<=0:raise ValueError('供应商限额必须大于0')
        self.store,self.key,self.interval,self.clock,self.sleep=store,key,60/requests_per_minute,clock,sleep
    def acquire(self):
        now=self.clock();slot=self.store.reserve(self.key,now,self.interval)
        remaining=slot-self.clock()
        if remaining>0:self.sleep(remaining)
