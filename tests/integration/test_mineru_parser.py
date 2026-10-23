"""显式付费供应商小样；只上传新建两页样本，不读取课程原件。"""
import os
from pathlib import Path
from uuid import uuid4
import pytest

pytestmark=[pytest.mark.integration,pytest.mark.live_provider]


def test_real_mineru_preserves_pages_and_cached_retry():
    if os.getenv('M1_LIVE_PROVIDER')!='1': pytest.fail('需显式M1_LIVE_PROVIDER=1才调用供应商，不自动skip')
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2]/'.env')
    from app.ingestion.parsers.mineru import MinerUProvider,MineruParser
    from app.ingestion.stages.pdf_segments import save_json
    import fitz
    work=Path('output/m1-live-pdf')/uuid4().hex;work.mkdir(parents=True)
    source=work/'manual.pdf'
    with fitz.open() as pdf:
        for n in range(2):
            page=pdf.new_page()
            page.insert_text((50,50),f'LA2608 Test Manual - physical page {n+1}',fontsize=16)
            page.insert_text((50,100),'Use display wlan ap to check the controller connection. R/M means Run/Master.')
        pdf.save(source)
    parser=MineruParser(MinerUProvider(),work/'cache',max_pages=1)
    result=parser.parse(source,document_id='synthetic-m1',revision_id='r1')
    assert len(result.pages)==2
    assert {ref.page for b in result.blocks for ref in b.source_refs}=={1,2}
    assert 'display wlan ap' in '\n'.join(b.text for b in result.blocks).lower()
    assert not result.quality_flags
    result_path=work/'parsed.json';save_json(result_path,result.model_dump(mode='json'))
    class NoProviderCalls:
        version=MinerUProvider.version
        def parse_segment(self,*a): raise AssertionError('成功段不应再次调用供应商')
    assert MineruParser(NoProviderCalls(),work/'cache',max_pages=1).parse(source,document_id='synthetic-m1',revision_id='r1')==result
    save_json(Path('docs/development/evidence/M1-04-live-summary.json'),{'status':'passed','fake':False,'pages':2,'segments':2,'pages_seen':[1,2],
              'cache_retry_without_provider':True,'artifact_path':str(result_path),'source_sha256':result.original_sha256,'quality_flags':list(result.quality_flags)})
