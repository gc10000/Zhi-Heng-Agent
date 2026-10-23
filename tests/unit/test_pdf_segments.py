"""合成150页PDF与可控供应商；验证正常恢复、真实偏移和降级边界。"""
from pathlib import Path
import json
import pytest


def make_pdf(path,count):
    import fitz
    with fitz.open() as pdf:
        for n in range(count): pdf.new_page().insert_text((30,30),f'Physical page {n+1}')
        pdf.save(path)


def test_150_pages_preserve_offsets_and_reuse_successful_segments(tmp_path):
    from app.ingestion.parsers.mineru import MineruParser, ProviderTimeout
    path=tmp_path/'long.pdf';make_pdf(path,150)
    class Provider:
        version='fake-v1'
        calls=[]
        fail=True
        def parse_segment(self,path,work):
            self.calls.append(path.name)
            if len(self.calls)==2 and self.fail: raise ProviderTimeout('timeout')
            import fitz
            with fitz.open(path) as pdf:
                return {'blocks':[{'type':'text','text':p.get_text(),'page_idx':i} for i,p in enumerate(pdf)],'flags':[]}
    provider=Provider();parser=MineruParser(provider,tmp_path/'cache',max_pages=50)
    with pytest.raises(ProviderTimeout): parser.parse(path,document_id='d',revision_id='r')
    first=provider.calls[0]
    result=parser.parse(path,document_id='d',revision_id='r')
    assert provider.calls.count(first)==1
    assert [b.source_refs[0].page for b in result.blocks]==list(range(1,151))
    assert 'Physical page 51' in result.blocks[50].text
    before=len(provider.calls)
    assert parser.parse(path,document_id='d',revision_id='r')==result
    assert len(provider.calls)==before
    checkpoints=list((tmp_path/'cache').rglob('segment.json'))
    assert len(checkpoints)==3
    assert sorted(json.loads(p.read_text())['segment_offset'] for p in checkpoints)==[0,50,100]


def test_timeout_native_fallback_is_explicit_not_silent_success(tmp_path):
    from app.ingestion.parsers.mineru import MineruParser, ProviderTimeout
    path=tmp_path/'manual.pdf';make_pdf(path,1)
    class Provider:
        version='fake'
        def parse_segment(self,*a): raise ProviderTimeout('no private response')
    result=MineruParser(Provider(),tmp_path/'cache',allow_native_fallback=True).parse(path,document_id='d',revision_id='r')
    assert {'native_fallback','provider_timeout'} <= set(result.quality_flags)
    assert result.blocks[0].source_refs[0].page==1


def test_segment_hash_and_byte_limit_and_corrupt_cached_result(tmp_path):
    from app.ingestion.stages.pdf_segments import split_pdf
    path=tmp_path/'m.pdf';make_pdf(path,3)
    with pytest.raises(ValueError): split_pdf(path,tmp_path/'segments',max_pages=2,max_bytes=10)
    segments=split_pdf(path,tmp_path/'ok',max_pages=2,max_bytes=10_000_000)
    assert [s['segment_offset'] for s in segments]==[0,2]
    assert all(len(s['sha256'])==64 and s['bytes']<=10_000_000 for s in segments)


def test_mineru_archive_rejects_traversal_and_marks_structure_repair(tmp_path):
    from io import BytesIO
    import zipfile
    from app.ingestion.parsers.mineru import unpack_result, ProviderError
    raw=BytesIO()
    with zipfile.ZipFile(raw,'w') as z: z.writestr('../escape.md','bad')
    with pytest.raises(ProviderError): unpack_result(raw.getvalue(),tmp_path/'bad')
    raw=BytesIO()
    with zipfile.ZipFile(raw,'w') as z: z.writestr('full.md','# 原文无页码')
    result=unpack_result(raw.getvalue(),tmp_path/'good')
    assert result['flags']==['structure_repaired','missing_page_refs']
    assert result['blocks'][0].get('page_idx') is None


def test_native_fallback_cache_cannot_bypass_next_call_opt_in(tmp_path):
    from app.ingestion.parsers.mineru import MineruParser, ProviderTimeout
    path=tmp_path/'manual.pdf';make_pdf(path,1)
    class Provider:
        version='fake'
        def parse_segment(self,*a): raise ProviderTimeout('synthetic')
    MineruParser(Provider(),tmp_path/'cache',allow_native_fallback=True).parse(path,document_id='d',revision_id='r')
    with pytest.raises(ProviderTimeout):
        MineruParser(Provider(),tmp_path/'cache',allow_native_fallback=False).parse(path,document_id='d',revision_id='r')


def test_corrupted_cached_result_is_rejected(tmp_path):
    from app.ingestion.parsers.mineru import MineruParser
    path=tmp_path/'manual.pdf';make_pdf(path,1)
    class Provider:
        version='fake'
        def parse_segment(self,*a): return {'blocks':[{'type':'text','text':'original','page_idx':0}],'flags':[]}
    parser=MineruParser(Provider(),tmp_path/'cache')
    parser.parse(path,document_id='d',revision_id='r')
    checkpoint=next((tmp_path/'cache').rglob('segment.json'))
    value=json.loads(checkpoint.read_text());value['result']['blocks'][0]['text']='corrupt'
    checkpoint.write_text(json.dumps(value))
    with pytest.raises(ValueError,match='hash'):
        parser.parse(path,document_id='d',revision_id='r')


def test_failed_batch_can_retry_without_discarding_old_batch_evidence(tmp_path,monkeypatch):
    from app.ingestion.parsers.mineru import MinerUProvider,ProviderError
    from io import BytesIO
    from types import SimpleNamespace
    import requests,zipfile
    raw=BytesIO()
    with zipfile.ZipFile(raw,'w') as z: z.writestr('content_list.json',json.dumps([{'type':'text','text':'ok','page_idx':0}]))
    class Session:
        def __enter__(self): return self
        def __exit__(self,*args): pass
        def put(self,*a,**kw): return SimpleNamespace(status_code=200)
        def get(self,*a,**kw): return SimpleNamespace(status_code=200,content=raw.getvalue())
    monkeypatch.setattr(requests,'Session',Session)
    provider=MinerUProvider(base_url='https://example.invalid',api_token='fake',session=Session())
    calls=[]
    def request(method,url,**kwargs):
        calls.append(method)
        if method=='POST': return {'batch_id':'good','file_urls':['https://example.invalid/upload']}
        return {'extract_result':[{'state':'failed'} if url.endswith('bad') else {'state':'done','full_zip_url':'https://example.invalid/result'}]}
    monkeypatch.setattr(provider,'_json',request)
    work=tmp_path/'work';work.mkdir();(work/'provider.json').write_text(json.dumps({'batch_id':'bad','uploaded':True}))
    path=tmp_path/'input.pdf';path.write_bytes(b'synthetic')
    with pytest.raises(ProviderError): provider.parse_segment(path,work)
    assert provider.parse_segment(path,work)['blocks'][0]['text']=='ok'
    assert calls.count('POST')==1
    assert json.loads((work/'provider.json').read_text())['previous_batches']==['bad']
