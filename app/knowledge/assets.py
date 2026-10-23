"""图片原件和描述分别存储；构造时注入客户端，不建桶/改策略。"""
import time
from io import BytesIO
from PIL import Image
from pymongo.errors import DuplicateKeyError
from app.knowledge.models import Asset,content_hash,stable_id


class MongoSummaryCache:
    def __init__(self,db,*,lease_seconds=900,clock=time.time):
        self.collection=db['image_summary_cache'];self.lease_seconds=lease_seconds;self.clock=clock
    def get(self,key): return self.collection.find_one({'_id':key})
    def claim(self,key,owner):
        now=self.clock()
        try:
            result=self.collection.update_one({'_id':key,'$or':[{'status':'failed'},{'lease_until':{'$lt':now}}]},
                {'$set':{'status':'pending','owner':owner,'lease_until':now+self.lease_seconds}},upsert=True)
            return bool(result.matched_count or result.upserted_id)
        except DuplicateKeyError:return False
    def complete(self,key,owner,text):
        return bool(self.collection.update_one({'_id':key,'owner':owner,'status':'pending','lease_until':{'$gte':self.clock()}},
                    {'$set':{'status':'completed','text':text},'$unset':{'lease_until':'','error_type':''}}).matched_count)
    def fail(self,key,owner,error):
        self.collection.update_one({'_id':key,'owner':owner,'status':'pending'},{'$set':{'status':'failed','error_type':error}})


class AssetStore:
    def __init__(self,db,client,*,bucket,prefix='knowledge-v2/'):
        if not prefix or '..' in prefix or prefix.startswith('/'):
            raise ValueError('对象前缀非法')
        self.collection=db['knowledge_assets'];self.client,self.bucket,self.prefix=client,bucket,prefix.rstrip('/')+'/'
        self.collection.create_index('asset_id',unique=True)

    def put_image(self,image,*,document_id,revision_id,data,description=None,status='pending',cache_key=None):
        with Image.open(BytesIO(data)) as decoded:
            media=Image.MIME.get(decoded.format)
            decoded.verify()
        with Image.open(BytesIO(data)) as decoded:decoded.load()
        digest=content_hash(data)
        key=self.prefix+stable_id('asset-object',revision_id,[document_id,digest])
        asset=Asset(asset_id=image.image_id,document_id=document_id,revision_id=revision_id,sha256=digest,object_key=key,media_type=media,
                    source_refs=image.source_refs,description=description,description_status=status,description_cache_key=cache_key)
        existing=self.collection.find_one({'asset_id':asset.asset_id})
        if existing and any(existing[k]!=getattr(asset,k) for k in ('document_id','revision_id','sha256','object_key')):
            raise ValueError('资产身份内容冲突')
        # 上传前预留不可变身份，避免错误/并发请求先写出不属于此资产的对象。
        try:
            self.collection.update_one({'asset_id':asset.asset_id,'document_id':document_id,'revision_id':revision_id,'sha256':digest,'object_key':key},
                {'$setOnInsert':asset.model_dump(mode='json')},upsert=True)
        except DuplicateKeyError:raise ValueError('资产身份内容冲突') from None
        self.client.put_object(self.bucket,key,BytesIO(data),len(data),content_type=media,metadata={'sha256':digest})
        self.collection.update_one({'asset_id':asset.asset_id},{'$set':asset.model_dump(mode='json')},upsert=True)
        return asset

    def read(self,asset_id):
        item=self.collection.find_one({'asset_id':asset_id})
        if item is None:raise LookupError('图片资产缺失')
        response=self.client.get_object(self.bucket,item['object_key'])
        try:data=response.read()
        finally:response.close();response.release_conn()
        if content_hash(data)!=item['sha256']:raise ValueError('图片原件hash不符')
        return item,data
