"""字符版面关联独立反例；PDF全部为合成且不访问供应商。"""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
import fitz
import pytest
from app.ingestion.parsers.mineru import MineruParser
from app.ingestion.stages.chunking import chunk_document

def locate(tmp_path,placements,cells,dividers=()):
    path=tmp_path/'layout.pdf'
    with fitz.open() as pdf:
        page=pdf.new_page()
        for x,y,text in placements:page.insert_text((x,y),text)
        for y in dividers:page.draw_line((20,y),(550,y))
        pdf.save(path)
    table='<table><tr>'+''.join('<td>'+c+'</td>' for c in cells)+'</tr></table>'
    class Provider:
        version='synthetic-layout-review'
        def parse_segment(self,*a):return {'blocks':[dict(type='table',page_idx=0,table_body=table)]}
    parsed=MineruParser(Provider(),tmp_path/'cache').parse(path,document_id='d',revision_id='r')
    chunks=[c for c in chunk_document(parsed) if c.content_kind=='table']
    return {ref.page for c in chunks for ref in c.source_refs}

def test_disjoint_single_cell_fragments_cannot_certify_row(tmp_path):
    pages=locate(tmp_path,[(30,40,'Supports wired'),(400,700,'network connection')],['Supports wired network connection'])
    assert pages=={None},'跨页内远处不同行带的内容不能拼成单个精确单元格'

def test_cell_bounding_rectangle_cannot_bridge_unrelated_regions(tmp_path):
    pages=locate(tmp_path,[(30,40,'AX240'),(130,40,'Supports wired'),(130,700,'network connection')],['AX240','Supports wired network connection'])
    assert pages=={None},'描述的整体包围框与型号行相交不证明远处续文属于该行'

def test_same_row_distinct_columns_still_precise(tmp_path):
    assert locate(tmp_path,[(30,40,'AX240'),(130,40,'Supports wired network connection')],['AX240','Supports wired network connection'])=={1}

def test_adjacent_wrap_within_same_column_still_precise(tmp_path):
    assert locate(tmp_path,[(30,40,'AX240'),(130,40,'Supports wired'),(130,54,'network connection')],['AX240','Supports wired network connection'])=={1}

def test_reverse_column_order_is_unknown(tmp_path):
    assert locate(tmp_path,[(130,40,'AX240'),(30,40,'Supports wired network connection')],['AX240','Supports wired network connection'])=={None}

def test_different_row_versions_are_unknown(tmp_path):
    assert locate(tmp_path,[(30,40,'2014'),(130,54,'Supports wired network connection')],['2014','Supports wired network connection'],dividers=(46,))=={None}

def test_crosspage_fragment_must_preserve_column_relationship(tmp_path):
    path=tmp_path/'crosspage.pdf'
    with fitz.open() as pdf:
        page=pdf.new_page();page.insert_text((30,40),'AX240');page.insert_text((130,40),'Supports wired')
        page=pdf.new_page();page.insert_text((400,700),'network connection')
        pdf.save(path)
    class Provider:
        version='synthetic-crosspage-review'
        def parse_segment(self,*a):
            return {'blocks':[dict(type='table',page_idx=0,table_body='<table><tr><td>AX240</td><td>Supports wired network connection</td></tr></table>')]}
    parsed=MineruParser(Provider(),tmp_path/'cache').parse(path,document_id='d',revision_id='r')
    pages={ref.page for c in chunk_document(parsed) if c.content_kind=='table' for ref in c.source_refs}
    assert pages=={None},'跨页续文丢失列位置且远离关联区域时不能仅凭字符串拼接确认两页'
