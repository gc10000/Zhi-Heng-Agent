"""原独立反例及相邻完整词、行关联边界，全部为合成原件。"""
import pytest
from tests.unit.test_pdf_table_row_sources import parsed
from app.ingestion.stages.chunking import chunk_document


def pages_of(doc):
    return {r.page for c in chunk_document(doc) if c.content_kind=="table" for r in c.source_refs}


@pytest.mark.parametrize('text,cells',[
    ('AX2400 Supports wired network connection',('AX240','Supports wired network connection')),
    ('2014 Legacy wireless only\n2019 Supports wired network connection',('2014','Supports wired network connection')),
    ('XAX240 Supports wired network connection',('AX240','Supports wired network connection')),
    ('2014\nSupports wired network connection',('2014','Supports wired network connection')),
    ('AX240 Supports wired network connection\nAX240 Supports wired network connection',('AX240','Supports wired network connection')),
])
def test_cannot_certify_substrings_or_unassociated_rows(tmp_path,text,cells):
    table='<table><tr>'+''.join('<td>'+c+'</td>' for c in cells)+'</tr></table>'
    doc=parsed(tmp_path,[text,'Unrelated'],table)
    assert pages_of(doc)=={None}
    assert 'table_row_page_unresolved' in doc.quality_flags


def test_crosspage_version_mismatch_is_unknown(tmp_path):
    doc=parsed(tmp_path,['2014 Legacy feature\n2019 Supports first part','and second part'],
        '<table><tr><td>2014</td><td>Supports first part and second part</td></tr></table>')
    assert pages_of(doc)=={None}


def test_correct_full_version_row_is_precise(tmp_path):
    doc=parsed(tmp_path,['2014 Supports wired network connection','Unrelated'],
        '<table><tr><td>2014</td><td>Supports wired network connection</td></tr></table>')
    assert pages_of(doc)=={1}


def test_scanned_page_has_no_character_proof(tmp_path):
    doc=parsed(tmp_path,['','Unrelated'],
        '<table><tr><td>AX240</td><td>Supports wired network connection</td></tr></table>')
    assert pages_of(doc)=={None}
