"""发布以单资料活动指针为事实；跨集合状态通过文档内outbox核对。"""
from io import BytesIO
from uuid import uuid4
from PIL import Image
from app.knowledge.models import Chunk,content_hash
from app.knowledge.repository import ConflictError,fingerprint


class RevisionPublisher:
    def __init__(self,repo,index,*,read_original,asset_store=None):
        self.repo,self.index,self.read_original,self.assets=repo,index,read_original,asset_store

    def inspect(self,revision):
        manifest=revision.get('stages',{}).get('indexed')
        if not manifest or manifest['collection']!=self.index.collection:raise ValueError('缺少当前集合索引清单')
        if content_hash(self.read_original(revision))!=revision['original_sha256']:raise ValueError('原件hash不符')
        rows=self.index.revision_rows(self.repo,revision['revision_id'],vectors=True)
        payloads={row['chunk_uid']:fingerprint(self.index.payload(row)) for row in rows}
        if len(rows)!=manifest['count'] or payloads!=manifest['payload_hashes'] or fingerprint(payloads)!=manifest['manifest_sha256']:
            raise ValueError('索引数量/完整载荷hash不符')
        assets=set()
        for row in rows:
            if content_hash(row['text'].encode())!=row['content_sha256']:raise ValueError('切片正文hash不符')
            self.index.validate_vectors(row['dense_vector'],row['sparse_vector'],self.index.dense_dim)
            chunk=Chunk(**{k:row[k] for k in ('chunk_uid','document_id','revision_id','ordinal','text')},**row['metadata'])
            if not chunk.source_refs:raise ValueError('缺少切片来源，不能发布')
            if any(s.document_id!=revision['document_id'] or s.revision_id!=revision['revision_id'] for s in chunk.source_refs):raise ValueError('来源跨修订')
            assets.update(chunk.asset_ids)
            assets.update(s.asset_id for s in chunk.source_refs if s.asset_id)
        asset_hashes={}
        for aid in assets:
            if self.assets is None:raise ValueError('图片资产校验器缺失')
            item,data=self.assets.read(aid)
            if content_hash(data)!=item['sha256']:raise ValueError('图片原件hash不符')
            if item['document_id']!=revision['document_id'] or item['revision_id']!=revision['revision_id']:raise ValueError('图片归属不符')
            if item['description_status'] not in ('completed','not_required'):raise ValueError('图片摘要尚未就绪')
            with Image.open(BytesIO(data)) as image:image.verify()
            with Image.open(BytesIO(data)) as image:image.load()
            asset_hashes[aid]=content_hash(data)
        return {'attempt':revision['attempt'],'manifest_sha256':manifest['manifest_sha256'],'assets':asset_hashes,'original_sha256':revision['original_sha256']}

    def validate(self,revision_id,*,attempt):
        r=self.repo.get_revision(revision_id)
        if r['attempt']!=attempt or r['status']!='staged':raise ConflictError('验证attempt过期或状态不允许')
        validation=self.inspect(r)
        result=self.repo.revisions.update_one(self.repo.scope|{'revision_id':revision_id,'attempt':attempt,'status':'staged','stages.indexed':r['stages']['indexed']},
            {'$set':{'status':'validated','validation':validation}})
        if not result.matched_count:raise ConflictError('验证期间修订已变化')
        return validation

    def publish(self,revision_id,*,expected_active,after_pointer=None):
        r=self.repo.get_revision(revision_id)
        if r['status'] not in ('validated','published') or r.get('validation')!=self.inspect(r):raise ConflictError('修订未验证或验证已失效')
        transition={'id':str(uuid4()),'revision_id':revision_id,'expected_active':expected_active,'validation':r['validation']}
        result=self.repo.documents.update_one(self.repo.scope|{'document_id':r['document_id'],'active_revision_id':expected_active},
            {'$set':{'active_revision_id':revision_id,'publish_outbox':transition},'$inc':{'active_generation':1}})
        if not result.matched_count:raise ConflictError('活动修订已变化，请重新读取')
        if after_pointer:after_pointer()
        self.reconcile(r['document_id'])
        return transition

    def reconcile(self,document_id):
        document=self.repo.get_document(document_id);event=document.get('publish_outbox')
        if not event:return
        rid=document['active_revision_id']
        if event['revision_id']!=rid:raise ConflictError('待核对事件与活动修订不符')
        r=self.repo.get_revision(rid)
        if r['document_id']!=document_id or r.get('validation')!=event['validation'] or self.inspect(r)!=event['validation']:
            raise ConflictError('活动修订校验不符，保留事件等待人工核对')
        self.repo.revisions.update_one(self.repo.scope|{'revision_id':rid,'attempt':event['validation']['attempt'],'status':{'$in':['validated','published']}},
            {'$set':{'status':'published'}})
        self.repo.documents.update_one(self.repo.scope|{'document_id':document_id,'publish_outbox.id':event['id']},{'$unset':{'publish_outbox':''}})
