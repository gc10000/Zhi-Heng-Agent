"""M1同步领域导入入口，接线已批准能力；M2再建立任务/API。"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from app.ingestion.models import ParsedDocument
from app.ingestion.parsers.router import detect_format,UnsupportedFormatError
from app.ingestion.stages.images import process_images
from app.ingestion.stages.chunking import chunk_document
from app.knowledge.models import content_hash
from app.knowledge.repository import ConflictError,fingerprint
from app.knowledge.publishing import RevisionPublisher


class IngestionService:
    def __init__(self,repo,router,index,originals,assets,summary_service,*,embedder,model,prompt_version,max_chars=2000):
        self.repo,self.router,self.index,self.originals,self.assets=repo,router,index,originals,assets
        self.summary,self.embedder,self.model,self.prompt_version,self.max_chars=summary_service,embedder,model,prompt_version,max_chars
        self.publisher=RevisionPublisher(repo,index,read_original=originals.read,asset_store=assets)

    def result(self,rid):
        r=self.repo.get_revision(rid);d=self.repo.get_document(r['document_id'])
        return {'document_id':d['document_id'],'revision_id':rid,'status':r['status'],'active':d['active_revision_id']==rid,
                'quality_flags':r.get('quality_flags',[]),'chunks':self.index.revision_rows(self.repo,rid)}

    def import_file(self,path,*,request_id,expected_active,document_id=None,name=None,product_ids=(),purpose='unknown'):
        path=Path(path);kind=detect_format(path)
        if kind not in self.router.parsers:raise UnsupportedFormatError('该格式解析器尚未配置')
        if document_id is None:
            document=self.repo.register_document(request_id,name=name or path.name,product_ids=product_ids,purpose=purpose)
            document_id=document.document_id
        d=self.repo.get_document(document_id)
        data=path.read_bytes();digest=content_hash(data);key=self.originals.key(document_id,digest)
        r=self.repo.create_revision(document_id,request_id,original_sha256=digest,object_key=key,parser_version='m1-pipeline-1')
        current=self.repo.get_revision(r.revision_id)
        # 请求身份绑定处理配置，重试不能悄悄更换模型/预算/解析实现。
        adapter=self.router.parsers[kind]
        signature=fingerprint({'pipeline':'1','format':kind,'adapter':type(adapter).__name__,'parser_version':getattr(adapter,'version','1'),
                               'max_chars':self.max_chars,'model':self.model,'prompt_version':self.prompt_version})
        reserved=self.repo.revisions.update_one(self.repo.scope|{'revision_id':r.revision_id,
            '$or':[{'pipeline_identity':{'$exists':False}},{'pipeline_identity':signature}]},{'$set':{'pipeline_identity':signature}})
        if not reserved.matched_count:raise ConflictError('同修订处理配置变化，必须新建修订')
        if current['status']=='published':return self.result(r.revision_id)
        if current['status']=='validated':
            if d['active_revision_id']==r.revision_id:self.publisher.reconcile(document_id)
            else:self.publisher.publish(r.revision_id,expected_active=expected_active)
            return self.result(r.revision_id)
        attempt=self.repo.claim_attempt(r.revision_id,expected_attempt=current['attempt'])
        try:
            self.originals.put(key,data)
            parsed_stage=current.get('stages',{}).get('parsed')
            parsed=None
            if parsed_stage:
                raw=self.originals.get(parsed_stage['object_key'],parsed_stage['sha256'])
                parsed=ParsedDocument(**json.loads(raw))
                if not parsed_stage.get('images') and any(not Path(i.local_path).is_file() for i in parsed.images):parsed=None
            if parsed is None:
                parsed=self.router.parse(path,document_id=document_id,revision_id=r.revision_id)
                if parsed.original_sha256!=digest or parsed.document_id!=document_id or parsed.revision_id!=r.revision_id:raise ValueError('解析结果原件/身份不符')
                image_bytes={i.image_id:Path(i.local_path).read_bytes() for i in parsed.images}
                image_identity=fingerprint({iid:content_hash(raw) for iid,raw in image_bytes.items()})
                frozen=self.repo.revisions.update_one(self.repo.scope|{'revision_id':r.revision_id,'attempt':attempt,'status':'staged',
                    '$or':[{'source_image_identity':{'$exists':False}},{'source_image_identity':image_identity}]},{'$set':{'source_image_identity':image_identity}})
                if not frozen.matched_count:raise ConflictError('修订原始图片已变化，必须新建修订')
                parsed_stage=self.originals.put_parsed(r.revision_id,parsed.model_dump_json().encode())
                parsed_stage['images']={iid:self.originals.put_image_source(r.revision_id,iid,raw) for iid,raw in image_bytes.items()}
                self.repo.save_stage(r.revision_id,attempt=attempt,stage='parsed',manifest=parsed_stage)
            if parsed.original_sha256!=digest or parsed.document_id!=document_id or parsed.revision_id!=r.revision_id:raise ValueError('解析缓存身份不符')
            if parsed.purpose!='unknown' and d['purpose']=='unknown':
                self.repo.documents.update_one(self.repo.scope|{'document_id':document_id,'purpose':'unknown'},{'$set':{'purpose':parsed.purpose}})
            if any(f in parsed.quality_flags for f in ('missing_image','external_image_unresolved')):raise ValueError('图片未解析，不能发布；需提供本地原图')
            with TemporaryDirectory(prefix='m1-images-') as image_dir:
                restored=[]
                for image in parsed.images:
                    saved=parsed_stage.get('images',{}).get(image.image_id)
                    if saved:
                        image_path=Path(image_dir)/(content_hash(image.image_id.encode())+'.image')
                        image_path.write_bytes(self.originals.get(saved['object_key'],saved['sha256']))
                        image=image.model_copy(update={'local_path':str(image_path)})
                    restored.append(image)
                parsed=parsed.model_copy(update={'images':tuple(restored)})
                parsed,_=process_images(parsed,self.assets,self.summary,model=self.model,prompt_version=self.prompt_version)
            self.repo.revisions.update_one(self.repo.scope|{'revision_id':r.revision_id,'attempt':attempt,'status':'staged'},
                {'$set':{'quality_flags':list(parsed.quality_flags),'parser_version':parsed.parser_version}})
            if any(f in parsed.quality_flags for f in ('image_summary_failed','image_summary_pending')):raise ValueError('图片摘要未就绪，可使用原请求重试')
            chunks=chunk_document(parsed,max_chars=self.max_chars,default_product_ids=d['product_ids'])
            self.index.write_revision(self.repo,r.revision_id,chunks,attempt=attempt,embedder=self.embedder)
            self.publisher.validate(r.revision_id,attempt=attempt)
            self.publisher.publish(r.revision_id,expected_active=expected_active)
            return self.result(r.revision_id)
        except Exception as exc:
            # 仅标记当前staged attempt；已经验证/切换的状态交发布核对恢复。
            self.repo.revisions.update_one(self.repo.scope|{'revision_id':r.revision_id,'attempt':attempt,'status':'staged'},
                {'$set':{'status':'failed','failure':{'type':type(exc).__name__}}})
            raise

    def read_original(self,revision_id):return self.originals.read(self.repo.get_revision(revision_id))

    def read_chunk(self,revision_id,chunk_uid):
        rows=self.index.revision_rows(self.repo,revision_id)
        for row in rows:
            if row['chunk_uid']==chunk_uid:return row
        raise LookupError('修订中无此切片')

    def read_asset(self,revision_id,asset_id):
        r=self.repo.get_revision(revision_id)
        item=self.assets.collection.find_one({'asset_id':asset_id,'document_id':r['document_id'],'revision_id':revision_id})
        if item is None:raise LookupError('资产不在当前修订范围')
        return self.assets.read(asset_id)
