"""MinerU适配：分段、batch检查点、原页码恢复及显式降级，不导入旧初始化代码。"""
import json
import os
import time
import zipfile
from io import BytesIO
from pathlib import Path
from app.knowledge.models import SourceRef, stable_id, content_hash
from app.ingestion.models import Block, Page, ParsedDocument, ParsedImage
from app.ingestion.stages.pdf_segments import split_pdf, save_json


class ProviderError(RuntimeError):
    def __init__(self, message, *, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class ProviderTimeout(ProviderError):
    pass


def unpack_result(data,directory):
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    try:
        with zipfile.ZipFile(BytesIO(data)) as archive:
            if sum(info.file_size for info in archive.infolist())>512_000_000:
                raise ProviderError('解析结果解压体积超过上限')
            for item in archive.infolist():
                target=(directory/item.filename).resolve()
                if not target.is_relative_to(directory.resolve()): raise ProviderError('解析包含非法相对路径')
                if not item.is_dir():
                    target.parent.mkdir(parents=True,exist_ok=True)
                    target.write_bytes(archive.read(item))
        candidates=sorted(directory.rglob('*content_list.json'))
        if candidates:
            blocks=json.loads(candidates[0].read_text(encoding='utf-8'))
            if not isinstance(blocks,list) or not all(isinstance(b,dict) for b in blocks): raise ProviderError('解析结构非法')
            return {'blocks':blocks,'flags':[],'root':str(candidates[0].parent)}
        markdown=sorted(directory.rglob('*.md'))
        if not markdown: raise ProviderError('解析结果没有结构化内容或Markdown')
        return {'blocks':[{'type':'text','text':markdown[0].read_text(encoding='utf-8')}],
                'flags':['structure_repaired','missing_page_refs'],'root':str(markdown[0].parent)}
    except (zipfile.BadZipFile,ValueError,KeyError,OSError) as exc:
        raise ProviderError('解析结果不可读取') from None


class MinerUProvider:
    version='mineru-v4-vlm-1'
    def __init__(self,*,base_url=None,api_token=None,poll_timeout=None,poll_interval=2,session=None):
        import requests
        self.base_url=(base_url or os.getenv('MINERU_BASE_URL','')).rstrip('/')
        self.api_token=api_token or os.getenv('MINERU_API_TOKEN','')
        self.poll_timeout=poll_timeout if poll_timeout is not None else float(os.getenv('MINERU_POLL_TIMEOUT','600'))
        self.poll_interval=poll_interval
        self.session=session or requests.Session()

    def _json(self,method,url,**kwargs):
        try:
            response=self.session.request(method,url,headers={'Authorization':'Bearer '+self.api_token},timeout=30,**kwargs)
            if response.status_code!=200: raise ProviderError('MinerU HTTP请求失败', status_code=response.status_code)
            value=response.json()
            if value.get('code')!=0: raise ProviderError('MinerU返回业务错误')
            return value['data']
        except ProviderError: raise
        except Exception: raise ProviderError('MinerU请求失败，已隐藏响应和URL') from None

    def parse_segment(self,path,work):
        if not self.base_url or not self.api_token: raise ProviderError('缺MINERU_BASE_URL/MINERU_API_TOKEN，填写根目录.env')
        checkpoint=work/'provider.json'
        record=json.loads(checkpoint.read_text(encoding='utf-8')) if checkpoint.exists() else {}
        if record.get('failed'):
            # 仅供应商明确失败才新建批次；超时保留原batch继续轮询。
            record={'previous_batches':record.get('previous_batches',[])+[record['batch_id']]}
        if not record.get('batch_id'):
            value=self._json('POST',self.base_url+'/file-urls/batch',json={'files':[{'name':Path(path).name}],'model_version':'vlm'})
            record.update(batch_id=value['batch_id'],uploaded=False);save_json(checkpoint,record)
            # Signed URL不落日志/检查点；只在内存中用于上传。
            import requests
            try:
                with requests.Session() as upload:
                    upload.trust_env=False
                    with Path(path).open('rb') as stream:
                        response=upload.put(value['file_urls'][0],data=stream,timeout=120)
                if response.status_code not in (200,201): raise ProviderError('MinerU上传失败')
                record['uploaded']=True;save_json(checkpoint,record)
            except ProviderError: raise
            except Exception: raise ProviderError('MinerU上传中断，可核对已有batch后重试') from None
        started=time.monotonic()
        while time.monotonic()-started<self.poll_timeout:
            value=self._json('GET',self.base_url+'/extract-results/batch/'+record['batch_id'])
            results=value.get('extract_result',[])
            if results and results[0].get('state')=='done':
                try:
                    response=self.session.get(results[0]['full_zip_url'],timeout=120)
                    if response.status_code!=200: raise ProviderError('MinerU结果下载失败')
                    return unpack_result(response.content,work/'result')
                except ProviderError: raise
                except Exception: raise ProviderError('MinerU结果下载中断') from None
            if results and results[0].get('state')=='failed':
                record['failed']=True;save_json(checkpoint,record)
                raise ProviderError('MinerU解析失败，保留batch供核对，下一次可重新提交')
            time.sleep(self.poll_interval)
        raise ProviderTimeout('MinerU轮询超时，已保存batch以便恢复')


class MineruParser:
    def __init__(self,provider,work_dir,*,max_pages=None,max_bytes=None,allow_native_fallback=False):
        self.provider,self.work_dir=provider,Path(work_dir)
        self.max_pages=max_pages if max_pages is not None else int(os.getenv('MINERU_SEGMENT_MAX_PAGES','50'))
        self.max_bytes=max_bytes if max_bytes is not None else int(os.getenv('MINERU_SEGMENT_MAX_BYTES','100000000'))
        self.allow_native_fallback=allow_native_fallback
        self.version=f'{provider.version}+structure-6/pages={self.max_pages}/bytes={self.max_bytes}/native={allow_native_fallback}'

    def parse(self,path,*,document_id,revision_id):
        import fitz
        path=Path(path);digest=content_hash(path.read_bytes())
        from .table_sources import locate_rows, native_page
        from app.ingestion.stages.chunking import _TableReader
        with fitz.open(path) as original:
            native_pages=[native_page(p) for p in original]
        base=self.work_dir/stable_id('parse-cache',revision_id,[document_id,digest,self.provider.version,self.max_pages,self.max_bytes,self.allow_native_fallback])
        segments=split_pdf(path,base/'inputs',max_pages=self.max_pages,max_bytes=self.max_bytes)
        blocks,images,flags=[],[],[]
        headings={}
        for segment in segments:
            work=base/str(segment['segment_offset']);work.mkdir(parents=True,exist_ok=True)
            checkpoint=work/'segment.json'
            saved=json.loads(checkpoint.read_text(encoding='utf-8')) if checkpoint.exists() else {}
            result=saved.get('result')
            if result is not None and saved.get('result_sha256')!=content_hash(json.dumps(result,sort_keys=True,ensure_ascii=False).encode()):
                raise ValueError('解析检查点内容hash不符')
            if result is None:
                try:
                    result=self.provider.parse_segment(Path(segment['path']),work)
                except ProviderError as exc:
                    if not self.allow_native_fallback: raise
                    with fitz.open(segment['path']) as part:
                        result={'blocks':[{'type':'text','text':page.get_text(),'page_idx':i} for i,page in enumerate(part)],
                                'flags':['native_fallback','provider_timeout' if isinstance(exc,ProviderTimeout) else 'provider_error']}
                provider_file=work/'provider.json'
                provider_state=json.loads(provider_file.read_text(encoding='utf-8')) if provider_file.exists() else {}
                save_json(checkpoint,{**segment,'batch_id':provider_state.get('batch_id'),'parser_version':self.provider.version,
                                     'result':result,'result_sha256':content_hash(json.dumps(result,sort_keys=True,ensure_ascii=False).encode())})
            flags.extend(result.get('flags',[]))
            for index,item in enumerate(result['blocks']):
                local_page=item.get('page_idx')
                if local_page is not None and (not isinstance(local_page,int) or not 0<=local_page<segment['pages']):
                    raise ProviderError('解析页码超出分段范围')
                page=segment['segment_offset']+local_page+1 if local_page is not None else None
                if page is None: flags.append('missing_page_refs')
                ref=SourceRef(document_id=document_id,revision_id=revision_id,kind='pdf',page=page)
                bid=stable_id('block',revision_id,[segment['segment_offset'],index])
                kind=item.get('type','text')
                text=item.get('text','')
                # MinerU代码正文有独立字段，不能把有效命令静默变成空文本块。
                if kind=='code':
                    text=item.get('code_body','') or text
                    if not isinstance(text,str) or not text.strip():
                        raise ProviderError('代码块缺少正文，禁止发布不完整解析')
                    kind='steps'
                if kind=='table': text=item.get('table_body','') or text
                kind='heading' if kind=='text' and item.get('text_level') else kind
                if kind not in {'text','heading','table','image','warning','steps'}: kind='text'
                if kind=='heading':
                    level=item.get('text_level',1)
                    if not isinstance(level,int) or not 1<=level<=6:
                        level=1;flags.append('heading_level_repaired')
                    headings={n:title for n,title in headings.items() if n<level}
                    headings[level]=text
                heading_path=tuple(headings[n] for n in sorted(headings))
                ref=ref.model_copy(update={'section_path':heading_path})
                asset_ids=()
                if kind=='image' and item.get('img_path'):
                    root=Path(result.get('root',work/'result')).resolve()
                    image_path=(root/item['img_path']).resolve()
                    if not image_path.is_relative_to(root) or not image_path.is_file():
                        raise ProviderError('解析图片缺失或路径越界')
                    image_id=stable_id('image',revision_id,[bid])
                    asset_ids=(image_id,)
                    text=' '.join(item.get('image_caption',[])) or text
                    images.append(ParsedImage(image_id=image_id,local_path=str(image_path),context=' / '.join(heading_path)+'\n'+text,source_refs=(ref,)))
                row_refs=()
                if kind=='table' and '<table' in text.lower():
                    reader=_TableReader();reader.feed(text)
                    row_refs=locate_rows(reader.rows,native_pages,ref)
                    if any(any(r.page is None for r in refs) for refs in row_refs):flags.append('table_row_page_unresolved')
                blocks.append(Block(block_id=bid,kind=kind,text=text,heading_path=heading_path,source_refs=(ref,),asset_ids=asset_ids,row_source_refs=row_refs))
        with fitz.open(path) as pdf:
            pages=tuple(Page(number=i+1,width=p.rect.width,height=p.rect.height,rotation=p.rotation) for i,p in enumerate(pdf))
        return ParsedDocument(document_id=document_id,revision_id=revision_id,original_sha256=digest,parser='mineru',
                              parser_version=self.provider.version+'+structure-6',quality_flags=tuple(sorted(set(flags))),pages=pages,blocks=tuple(blocks),images=tuple(images))
