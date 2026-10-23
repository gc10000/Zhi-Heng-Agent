"""阶段真实新资料贯通：新一页PDF用MinerU，新Markdown拓扑用真实视觉。"""
from pathlib import Path
from uuid import uuid4
from io import BytesIO
import json
import os
import pytest
from tests.integration.test_v2_index import v2_setup,real_embedder
from tests.integration.test_ingestion_pipeline import build_service

pytestmark=[pytest.mark.integration,pytest.mark.live_provider]


def test_real_new_pdf_and_image_document_to_published_retrieval(v2_setup,real_embedder):
    if os.getenv('M1_LIVE_PROVIDER')!='1':pytest.fail('需M1_LIVE_PROVIDER=1授权真实供应商小样')
    import fitz
    from PIL import Image,ImageDraw,ImageFont
    from openai import OpenAI
    from urllib.parse import urlparse
    from app.ingestion.parsers.mineru import MineruParser,MinerUProvider
    from app.ingestion.stages.images import VisionDescriber,process_images
    from app.ingestion.models import ParsedDocument
    from app.knowledge.models import content_hash
    repo,index=v2_setup;work=Path('output/m1-live-knowledge')/uuid4().hex;work.mkdir(parents=True)
    image=Image.new('RGB',(960,300),'white');draw=ImageDraw.Draw(image);font=ImageFont.load_default(size=22)
    draw.text((20,20),'Independent M1 network topology',fill='black',font=font)
    for x,label in [(30,'Gateway'),(350,'Controller'),(670,'Support PC')]:
        draw.rectangle((x,100,x+240,210),outline='navy',width=4);draw.text((x+30,140),label,fill='black',font=font)
    for x in (270,590):
        draw.line((x,155,x+80,155),fill='black',width=4);draw.polygon([(x+80,155),(x+64,145),(x+64,165)],fill='black')
    image_path=work/'topology.png';image.save(image_path)
    md=work/'support.md';md.write_text('# 设备技术支持\n\nGateway连接Controller，Controller连接Support PC。\n\n![网络拓扑](topology.png)\n\n使用display wlan ap检查连接状态。',encoding='utf-8')
    service=build_service(repo,index,real_embedder,work)
    client=OpenAI(api_key=os.environ['OPENAI_API_KEY'],base_url=os.environ['OPENAI_BASE_URL'],max_retries=0,timeout=90)
    model=os.environ['VL_MODEL'];host=urlparse(os.environ['OPENAI_BASE_URL']).hostname or ''
    provider=os.getenv('LLM_PROVIDER','auto')
    options={'extra_body':{'enable_thinking':False}} if provider=='dashscope' or (provider=='auto' and (host=='dashscope.aliyuncs.com' or host.endswith('.dashscope.aliyuncs.com'))) else {}
    describe=VisionDescriber(client,model,'用中文描述图中设备和连接关系，保留设备英文标签；只描述可见信息。',request_options=options)
    calls=[]
    def counted(data,context):
        calls.append(1)
        try:return describe(data,context)
        except Exception as exc:raise RuntimeError('视觉调用失败，类型='+type(exc).__name__) from None
    service.summary.describe=counted;service.model=model
    result=service.import_file(md,request_id='real-image',expected_active=None,purpose='technical',product_ids=('M1-test-device',))
    assert result['active'] and result['status']=='published' and calls==[1]
    description=next(row for row in result['chunks'] if row['metadata']['content_kind']=='image_description')
    aid=description['metadata']['asset_ids'][0];item,data=service.read_asset(result['revision_id'],aid)
    assert data==image_path.read_bytes() and content_hash(data)==item['sha256']
    with Image.open(BytesIO(data)) as decoded:decoded.load();assert decoded.size==(960,300)
    assert ('Gateway' in description['text'] or '网关' in description['text']) and ('Controller' in description['text'] or '控制器' in description['text'])
    assert description['metadata']['source_refs'][0]['kind']=='image_description'
    r=repo.get_revision(result['revision_id']);stage=r['stages']['parsed']
    parsed=ParsedDocument(**json.loads(service.originals.get(stage['object_key'],stage['sha256'])))
    service.summary.describe=lambda *a:pytest.fail('真实摘要缓存重试不应付费')
    _,cached=process_images(parsed,service.assets,service.summary,model=model,prompt_version='1')
    assert cached[0].description==item['description'] and calls==[1]
    hits=index.search(repo,'Gateway如何连接Controller',embedder=real_embedder,product_ids=('M1-test-device',),limit=10)
    assert any(h['entity']['revision_id']==result['revision_id'] for h in hits)
    assert service.read_original(result['revision_id'])==md.read_bytes()
    pdf=fitz.open();page=pdf.new_page();page.insert_text((50,50),'Independent M1 Support Manual',fontsize=18)
    page.insert_text((50,100),'Use display wlan ap to check the controller connection.');pdfpath=work/'manual.pdf';pdf.save(pdfpath);pdf.close()
    service.router.parsers['pdf']=MineruParser(MinerUProvider(),work/'pdf-cache',max_pages=1)
    pdfresult=service.import_file(pdfpath,request_id='real-pdf',expected_active=None,purpose='technical',product_ids=('M1-test-device',))
    assert pdfresult['active'] and not pdfresult['quality_flags']
    assert {ref['page'] for row in pdfresult['chunks'] for ref in row['metadata']['source_refs']}=={1}
    assert 'display wlan ap' in ' '.join(r['text'] for r in pdfresult['chunks']).lower()
    assert service.read_original(pdfresult['revision_id'])==pdfpath.read_bytes()
    report={'passed':True,'fake':False,'vision_calls':len(calls),'vision_cache_retry':True,'mineru_pages':1,
            'image_sha256':content_hash(data),'image_decoded_size':[960,300],'image_description':description['text'],
            'documents':[{'document_id':x['document_id'],'revision_id':x['revision_id'],'chunks':len(x['chunks']),'quality_flags':x['quality_flags']} for x in [result,pdfresult]],
            'active_snapshot':repo.get_active_revisions(),'collection':index.collection,'db':repo.db.name}
    (work/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    Path('docs/development/evidence/M1-11-live-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    client.close()
