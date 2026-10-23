"""实际分段解析必须把跨段标题层级传播到正文与来源。"""


def test_pdf_heading_paths_survive_segment_boundary(tmp_path):
    import fitz
    from app.ingestion.parsers.mineru import MineruParser
    path=tmp_path/'source.pdf';pdf=fitz.open();pdf.new_page();pdf.new_page();pdf.save(path);pdf.close()
    class Provider:
        version='heading-test'
        def parse_segment(self,path,work):
            blocks=[{'type':'text','text':'设备手册','text_level':1,'page_idx':0},
                    {'type':'text','text':'配置','text_level':2,'page_idx':0}] if work.name=='0' else []
            return {'blocks':blocks+[{'type':'text','text':'连接控制器','page_idx':0}],'flags':[]}
    parsed=MineruParser(Provider(),tmp_path/'cache',max_pages=1).parse(path,document_id='d',revision_id='r')
    assert parsed.blocks[-1].heading_path==('设备手册','配置')
    assert parsed.blocks[-1].source_refs[0].section_path==('设备手册','配置')
    assert parsed.blocks[-1].source_refs[0].page==2
