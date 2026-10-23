"""真实M1领域接线；此文件无付费供应商调用，原生PDF降级显式标记。"""
from pathlib import Path
from uuid import uuid4
import os
import pytest
from tests.integration.test_v2_index import v2_setup,real_embedder

pytestmark=pytest.mark.integration


def build_service(repo,index,real_embedder,work,*,describe=None):
    from minio import Minio
    from app.knowledge.originals import OriginalStore
    from app.knowledge.assets import AssetStore,MongoSummaryCache
    from app.infrastructure.rate_limits import MongoRateStore,SharedRateLimiter
    from app.ingestion.stages.images import ImageSummaryService
    from app.ingestion.parsers.router import ParserRouter
    from app.ingestion.parsers.markdown import MarkdownParser
    from app.ingestion.parsers.excel import ExcelParser
    from app.ingestion.parsers.mineru import MineruParser,ProviderTimeout
    from app.ingestion.service import IngestionService
    class NativeOnly:
        version='test-explicit-native'
        def parse_segment(self,*a):raise ProviderTimeout('显式测试原生降级，不调用真实MinerU')
    objects=Minio(os.environ['MINIO_ENDPOINT'],access_key=os.environ['MINIO_ACCESS_KEY'],secret_key=os.environ['MINIO_SECRET_KEY'],secure=os.getenv('MINIO_SECURE','').lower()=='true')
    prefix='m1-test/'+repo.db.name+'/'+uuid4().hex+'/'
    originals=OriginalStore(objects,bucket=os.environ['MINIO_BUCKET_NAME'],prefix=prefix)
    assets=AssetStore(repo.db,objects,bucket=os.environ['MINIO_BUCKET_NAME'],prefix=prefix+'assets/')
    router=ParserRouter({'md':MarkdownParser(),'xlsx':ExcelParser(),
                         'pdf':MineruParser(NativeOnly(),work/'pdf-cache',max_pages=1,allow_native_fallback=True)})
    if describe is None:
        def describe(*a):raise AssertionError('无图片测试不应调用摘要')
    summary=ImageSummaryService(MongoSummaryCache(repo.db),SharedRateLimiter(MongoRateStore(repo.db),'m1-tests-shared',requests_per_minute=30),describe)
    return IngestionService(repo,router,index,originals,assets,summary,embedder=real_embedder,model='explicit-test-no-live',prompt_version='1')


def test_new_document_registration_to_search_and_original_with_retry(v2_setup,real_embedder,tmp_path):
    from app.knowledge.repository import ConflictError
    repo,index=v2_setup;service=build_service(repo,index,real_embedder,tmp_path)
    path=tmp_path/'manual.md';path.write_text('# 配置\n\nLA2608使用display wlan ap检查控制器连接状态。',encoding='utf-8')
    result=service.import_file(path,request_id='request',expected_active=None,purpose='technical',product_ids=('LA2608',))
    assert result['active'] and result['status']=='published'
    uid=result['chunks'][-1]['chunk_uid'];rid=result['revision_id']
    assert service.read_original(rid)==path.read_bytes()
    assert service.read_chunk(rid,uid)['metadata']['source_refs'][0]['line_start']==3
    service.embedder=lambda *a:pytest.fail('完成请求不应重新编码')
    service.router.parse=lambda *a,**kw:pytest.fail('完成请求不应重新解析')
    assert service.import_file(path,request_id='request',expected_active=None,purpose='technical',product_ids=('LA2608',))['revision_id']==rid
    # 仍用真实BGE搜索，命中活动修订并带来源。
    hits=index.search(repo,'LA2608如何检查控制器',embedder=real_embedder,product_ids=('LA2608',))
    assert hits and all(h['entity']['revision_id']==rid for h in hits)
    path.write_text('# 配置\n\n不同正文',encoding='utf-8')
    with pytest.raises(ConflictError):service.import_file(path,request_id='request',expected_active=None,purpose='technical',product_ids=('LA2608',))
    assert service.read_original(rid)!=path.read_bytes()


def test_pdf_excel_source_audit_and_same_name(v2_setup,real_embedder,tmp_path):
    import fitz
    from tests.unit.test_tabular_sources import make_workbook
    repo,index=v2_setup;service=build_service(repo,index,real_embedder,tmp_path)
    pdfpath=tmp_path/'sample.pdf';pdf=fitz.open()
    for i in range(2):pdf.new_page().insert_text((60,60),'Device controller parameter page '+str(i+1))
    pdf.save(pdfpath);pdf.close()
    pdfresult=service.import_file(pdfpath,request_id='pdf',expected_active=None,name='同名')
    assert 'native_fallback' in pdfresult['quality_flags'] and 'provider_timeout' in pdfresult['quality_flags']
    assert {ref['page'] for row in pdfresult['chunks'] for ref in row['metadata']['source_refs']}=={1,2}
    xlsx=tmp_path/'sample.xlsx';make_workbook(xlsx)
    result=service.import_file(xlsx,request_id='xlsx',expected_active=None,name='同名')
    assert result['document_id']!=pdfresult['document_id'] and service.read_original(result['revision_id'])==xlsx.read_bytes()
    refs=[ref for row in result['chunks'] for ref in row['metadata']['source_refs']]
    assert len({r['sheet'] for r in refs})==2 and all(r['page'] is None for r in refs)
    assert repo.get_document(result['document_id'])['purpose']=='project_plan'
    missing=tmp_path/'missing.md';missing.write_text('![未找到](missing.png)',encoding='utf-8')
    with pytest.raises(ValueError,match='图片'):service.import_file(missing,request_id='missing',expected_active=None)


def test_image_failure_propagates_and_retry_uses_cache_and_keeps_old_version(v2_setup,real_embedder,tmp_path):
    from PIL import Image
    from app.knowledge.repository import KnowledgeRepository,ScopeError
    repo,index=v2_setup
    service=build_service(repo,index,real_embedder,tmp_path,describe=lambda *a:(_ for _ in ()).throw(TimeoutError('合成视觉失败')))
    path=tmp_path/'manual.md';path.write_text('# 原版\n\n控制器连接检查。',encoding='utf-8')
    first=service.import_file(path,request_id='old',expected_active=None)
    Image.new('RGB',(10,10),'green').save(tmp_path/'diagram.png')
    path.write_text('# 新版\n\n![拓扑 '+first['document_id']+'](diagram.png)\n\n无线设备连接控制器。',encoding='utf-8')
    with pytest.raises(ValueError,match='图片摘要'):service.import_file(path,request_id='new',document_id=first['document_id'],expected_active=first['revision_id'])
    failed=repo.revisions.find_one(repo.scope|{'request_id':'new'})
    assert failed['status']=='failed' and failed['failure']['type']=='ValueError'
    assert repo.get_document(first['document_id'])['active_revision_id']==first['revision_id']
    original_image=(tmp_path/'diagram.png').read_bytes()
    # 已快照的修订不能在重试时被同路径替换图悄悄改变。
    Image.new('RGB',(10,10),'red').save(tmp_path/'diagram.png')
    calls=[];service.summary.describe=lambda *a:calls.append(1) or '合成端口摘要：设备连接控制器'
    result=service.import_file(path,request_id='new',document_id=first['document_id'],expected_active=first['revision_id'])
    assert result['active'] and len(calls)==1
    rows=result['chunks'];asset_id=next(r['metadata']['asset_ids'][0] for r in rows if r['metadata']['asset_ids'])
    item,data=service.read_asset(result['revision_id'],asset_id)
    assert data==original_image and data!=(tmp_path/'diagram.png').read_bytes() and item['description_status']=='completed'
    assert any(r['metadata']['content_kind']=='image_description' for r in rows)
    assert 'failed' not in ' '.join(result['quality_flags'])
    with pytest.raises(LookupError):service.read_asset(first['revision_id'],asset_id)
    other=KnowledgeRepository(repo.db,kb_id=repo.kb_id,owner_id='other')
    service.repo=other
    with pytest.raises(ScopeError):service.read_original(result['revision_id'])
    service.repo=repo
    service.publisher.publish(first['revision_id'],expected_active=result['revision_id'])
    assert service.result(first['revision_id'])['active']
    assert not service.result(result['revision_id'])['active']
