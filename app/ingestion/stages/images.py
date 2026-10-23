"""联合缓存先领取再付费；失败保留状态，不生成伪摘要。"""
import base64
import json
import re
from pathlib import Path
from uuid import uuid4
from app.knowledge.models import content_hash,SourceRef
from app.ingestion.models import Block


class SummaryBusy(RuntimeError):pass


def summary_key(data,context,model,prompt_version):
    return content_hash(json.dumps([content_hash(data),content_hash(context.encode()),model,prompt_version],ensure_ascii=False).encode())


def plain_description(text):
    text=re.sub(r'!\[[^\]]*\]\([^)]*\)','',text)
    text=re.sub(r'<img\b[^>]*>','',text,flags=re.I)
    return text.split('![',1)[0].strip()


class ImageSummaryService:
    def __init__(self,cache,limiter,describe):self.cache,self.limiter,self.describe=cache,limiter,describe
    def summarize(self,data,context,model,prompt_version):
        key=summary_key(data,context,model,prompt_version)
        saved=self.cache.get(key)
        if saved and saved['status']=='completed':return saved['text'],key
        owner=str(uuid4())
        if not self.cache.claim(key,owner):raise SummaryBusy('图摘要已有活动领取者，请稍后恢复')
        try:
            self.limiter.acquire()
            text=plain_description(self.describe(data,context))
            if not text:raise ValueError('图摘要为空')
            if not self.cache.complete(key,owner,text):raise SummaryBusy('图摘要领取已过期')
            return text,key
        except Exception as exc:
            self.cache.fail(key,owner,type(exc).__name__)
            raise


class VisionDescriber:
    def __init__(self,client,model,prompt):self.client,self.model,self.prompt=client,model,prompt
    def __call__(self,data,context):
        from io import BytesIO
        from PIL import Image
        with Image.open(BytesIO(data)) as decoded:media=Image.MIME.get(decoded.format)
        response=self.client.chat.completions.create(model=self.model,messages=[{'role':'user','content':[
            {'type':'text','text':self.prompt+'\n上下文：'+context},
            {'type':'image_url','image_url':{'url':'data:'+media+';base64,'+base64.b64encode(data).decode()}}]}],temperature=0)
        return response.choices[0].message.content


def process_images(document,store,summary_service,*,model,prompt_version):
    # 仅替换本阶段生成的派生块，保留原文；重试不会累积重复摘要。
    derived_ids={'description-'+image.image_id for image in document.images}
    assets=[];blocks=[b for b in document.blocks if b.block_id not in derived_ids]
    flags=[f for f in document.quality_flags if f not in {'image_summary_pending','image_summary_failed'}]
    for image in document.images:
        data=Path(image.local_path).read_bytes();description=None;key=summary_key(data,image.context,model,prompt_version)
        try:description,key=summary_service.summarize(data,image.context,model,prompt_version);status='completed'
        except SummaryBusy:status='pending';flags.append('image_summary_pending')
        except Exception:status='failed';flags.append('image_summary_failed')
        asset=store.put_image(image,document_id=document.document_id,revision_id=document.revision_id,data=data,description=description,status=status,cache_key=key)
        assets.append(asset)
        if description:
            refs=tuple(SourceRef(**(r.model_dump()|{'kind':'image_description','asset_id':asset.asset_id})) for r in image.source_refs)
            blocks.append(Block(block_id='description-'+image.image_id,kind='image',description=description,source_refs=refs,asset_ids=(asset.asset_id,)))
    return document.model_copy(update={'blocks':tuple(blocks),'quality_flags':tuple(sorted(set(flags)))}),assets
