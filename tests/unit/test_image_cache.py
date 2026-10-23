"""图摘要服务离线行为，缓存端口用内存实现；真实Mongo另测。"""
from threading import Lock
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest


class Cache:
    def __init__(self): self.rows={};self.lock=Lock()
    def get(self,key): return self.rows.get(key)
    def claim(self,key,owner):
        with self.lock:
            if self.rows.get(key,{}).get('status') not in (None,'failed'): return False
            self.rows[key]={'status':'pending','owner':owner};return True
    def complete(self,key,owner,text):
        self.rows[key]={'status':'completed','text':text};return True
    def fail(self,key,owner,error): self.rows[key]={'status':'failed','error_type':error}


def test_cache_key_is_context_model_and_prompt_sensitive_and_retry_free():
    from app.ingestion.stages.images import ImageSummaryService
    cache=Cache();calls=[]
    service=ImageSummaryService(cache,SimpleNamespace(acquire=lambda:None),lambda data,context:calls.append(context) or '拓扑说明')
    a=service.summarize(b'image','ctx','model','prompt1')
    assert service.summarize(b'image','ctx','model','prompt1')==a and len(calls)==1
    service.summarize(b'image','other','model','prompt1')
    service.summarize(b'image','ctx','new-model','prompt1')
    service.summarize(b'image','ctx','model','prompt2')
    assert len(calls)==4


def test_failure_is_persisted_and_can_recover_without_fake_summary():
    from app.ingestion.stages.images import ImageSummaryService
    cache=Cache()
    def failure(*a): raise TimeoutError('sensitive-url-marker')
    service=ImageSummaryService(cache,SimpleNamespace(acquire=lambda:None),failure)
    with pytest.raises(TimeoutError): service.summarize(b'i','c','m','p')
    assert next(iter(cache.rows.values()))=={'status':'failed','error_type':'TimeoutError'}
    service.describe=lambda *a:'恢复'
    assert service.summarize(b'i','c','m','p')[0]=='恢复'


def test_busy_cache_does_not_call_provider_and_nested_tags_are_stripped():
    from app.ingestion.stages.images import ImageSummaryService,SummaryBusy,summary_key
    cache=Cache();key=summary_key(b'i','c','m','p');cache.claim(key,'other')
    service=ImageSummaryService(cache,SimpleNamespace(acquire=lambda:None),lambda *a:pytest.fail('不得重复付费'))
    with pytest.raises(SummaryBusy): service.summarize(b'i','c','m','p')
    service=ImageSummaryService(Cache(),SimpleNamespace(acquire=lambda:None),lambda *a:'拓扑 ![嵌套](https://example.invalid/a.png) <img src="secret">说明')
    text,_=service.summarize(b'i','c','m','p')
    assert '![' not in text and '<img' not in text and 'https://' not in text


def test_shared_limiter_reserves_slots_across_instances():
    from app.infrastructure.rate_limits import SharedRateLimiter
    class Store:
        def __init__(self): self.next=0;self.lock=Lock()
        def reserve(self,key,now,interval):
            with self.lock:
                slot=max(now,self.next);self.next=slot+interval;return slot
    store=Store();delays=[]
    limits=[SharedRateLimiter(store,'supplier',requests_per_minute=60,clock=lambda:100,sleep=delays.append) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=4) as pool: list(pool.map(lambda i:limits[i%2].acquire(),range(4)))
    assert sorted(delays)==[1,2,3]


def test_processing_result_again_does_not_duplicate_derived_blocks(tmp_path):
    from app.ingestion.models import ParsedDocument,ParsedImage
    from app.knowledge.models import Asset
    from app.ingestion.stages.images import ImageSummaryService,process_images
    path=tmp_path/'image.png';path.write_bytes(b'fake-port-data')
    parsed=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='test',parser_version='1',
                          images=(ParsedImage(image_id='i',local_path=str(path)),))
    class Store:
        def put_image(self,image,**kwargs):
            return Asset(asset_id='i',document_id='d',revision_id='r',sha256='b'*64,object_key='o',media_type='image/png',description=kwargs['description'],description_status=kwargs['status'])
    service=ImageSummaryService(Cache(),SimpleNamespace(acquire=lambda:None),lambda *a:'说明')
    first,_=process_images(parsed,Store(),service,model='m',prompt_version='p')
    second,_=process_images(first,Store(),service,model='m',prompt_version='p')
    assert len(second.blocks)==1
