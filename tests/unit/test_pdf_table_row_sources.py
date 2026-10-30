"""合成跨页表经正式解析、结构化及切片后不能借用表格起始页。"""
import pytest
from app.ingestion.parsers.mineru import MineruParser
from app.ingestion.stages.chunking import chunk_document


def parsed(tmp_path, pages, rows, *, tail_page=1):
    import fitz
    path=tmp_path/'table.pdf'
    with fitz.open() as pdf:
        for text in pages:
            page=pdf.new_page();page.insert_text((30,40),text)
        pdf.save(path)
    class CachedProvider:
        version='synthetic-row-sources'
        def parse_segment(self,*args):
            return {'blocks':[{'type':'table','page_idx':0,'table_body':rows},
                {'type':'text','page_idx':tail_page,'text':'after table'}]}
    return MineruParser(CachedProvider(),tmp_path/'cache').parse(path,document_id='d',revision_id='r')


def test_key_value_rows_follow_actual_physical_page(tmp_path):
    doc=parsed(tmp_path,['Microphone Audio recording','Ethernet Wired network connection'],
        '<table><tr><td>Microphone</td><td>Audio recording</td></tr>'
        '<tr><td>Ethernet</td><td>Wired network connection</td></tr></table>')
    chunks=[c for c in chunk_document(doc) if c.content_kind=='table']
    assert [{r.page for r in c.source_refs} for c in chunks]==[{1},{2}]


def test_repeated_headers_keep_header_and_data_pages(tmp_path):
    doc=parsed(tmp_path,['Parameter Description\nalpha First supported feature','beta Second supported feature'],
        '<table><thead><tr><th>Parameter</th><th>Description</th></tr></thead>'
        '<tr><td>alpha</td><td>First supported feature</td></tr>'
        '<tr><td>beta</td><td>Second supported feature</td></tr></table>')
    chunks=[c for c in chunk_document(doc,max_chars=65) if c.content_kind=='table']
    assert len(chunks)==2
    assert [{r.page for r in c.source_refs} for c in chunks]==[{1},{1,2}]


@pytest.mark.parametrize('pages',[
    ['Unrelated content','Other content','Ethernet Wired network connection'],
    ['Ethernet Wired network connection','Ethernet Wired network connection'],
    ['Ethernet other description','Unrelated content'],
])
def test_unmatched_ambiguous_or_remote_text_has_no_precise_page(tmp_path,pages):
    doc=parsed(tmp_path,pages,'<table><tr><td>Ethernet</td><td>Wired network connection</td></tr></table>')
    refs=next(c for c in chunk_document(doc) if c.content_kind=='table').source_refs
    assert {r.page for r in refs}=={None}
    assert 'table_row_page_unresolved' in doc.quality_flags


def test_cross_page_cell_keeps_both_sources(tmp_path):
    doc=parsed(tmp_path,['Feature Supports first part','and the second part'],
        '<table><tr><td>Feature</td><td>Supports first part and the second part</td></tr></table>')
    refs=next(c for c in chunk_document(doc) if c.content_kind=='table').source_refs
    assert {r.page for r in refs}=={1,2}


def test_row_source_identity_cannot_cross_revision():
    from app.ingestion.models import Block,ParsedDocument
    from app.knowledge.models import SourceRef
    doc=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='x',parser_version='1',
        blocks=(Block(block_id='b',kind='table',rows=(('name','value'),),
            row_source_refs=((SourceRef(document_id='d',revision_id='other',kind='pdf',page=2),),)),))
    with pytest.raises(ValueError):chunk_document(doc)


def test_short_version_cell_cannot_be_ignored_when_locating_row(tmp_path):
    # 短版本限定缺席时，绝不能仅凭长描述给精确页码。
    doc2=parsed(tmp_path,['2019 Supports wired network connection','Unrelated content'],
        '<table><tr><td>2014</td><td>Supports wired network connection</td></tr></table>')
    assert {r.page for r in next(c for c in chunk_document(doc2) if c.content_kind=='table').source_refs}=={None}
