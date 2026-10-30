"""版面边界的同根因正反对照；均为合成PDF。"""
import fitz
import pytest
from tests.unit.test_table_layout_sources import locate
from app.ingestion.parsers.mineru import MineruParser
from app.ingestion.stages.chunking import chunk_document


def test_single_cell_adjacent_lines_preserved(tmp_path):
    assert locate(tmp_path,[(130,40,'Supports wired'),(130,54,'network connection')],['Supports wired network connection'])=={1}


def test_single_cell_separator_rejects_continuation(tmp_path):
    assert locate(tmp_path,[(130,40,'Supports wired'),(130,54,'network connection')],['Supports wired network connection'],dividers=(46,))=={None}


@pytest.mark.parametrize('x,y,expected',[(130,40,{1,2}),(400,40,{None}),(130,700,{None})])
def test_crosspage_column_and_region_independently_checked(tmp_path,x,y,expected):
    path=tmp_path/'cross.pdf'
    with fitz.open() as pdf:
        p=pdf.new_page();p.insert_text((30,40),'AX240');p.insert_text((130,40),'Supports wired')
        p=pdf.new_page();p.insert_text((x,y),'network connection');pdf.save(path)
    class Provider:
        version='synthetic-layout-adjacent'
        def parse_segment(self,*a):
            return {'blocks':[dict(type='table',page_idx=0,table_body='<table><tr><td>AX240</td><td>Supports wired network connection</td></tr></table>')]}
    doc=MineruParser(Provider(),tmp_path/'cache').parse(path,document_id='d',revision_id='r')
    assert {r.page for c in chunk_document(doc) if c.content_kind=='table' for r in c.source_refs}==expected
