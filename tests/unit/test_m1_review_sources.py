"""M1审查反例：真实解析到切片的值、物理来源和标题层级。"""
import zipfile
import pytest
from app.ingestion.parsers.markdown import MarkdownParser
from app.ingestion.stages.chunking import chunk_document


def test_excel_dash_value_and_cell_mapping_survive_chunking(tmp_path):
    from app.ingestion.parsers.excel import ExcelParser
    from tests.unit.test_tabular_sources import make_workbook
    path = tmp_path / 'dash.xlsx'
    make_workbook(path)
    with zipfile.ZipFile(path) as source:
        entries = {name: source.read(name) for name in source.namelist()}
    entries['xl/worksheets/s1.xml'] = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>' + ''.join(
        f'<row r="{i}"><c r="A{i}" t="inlineStr"><is><t>{value}</t></is></c></row>'
        for i, value in enumerate(['parameter', '---', 'actual-value'], 1)) + '</sheetData></worksheet>').encode()
    with zipfile.ZipFile(path, 'w') as target:
        for name, value in entries.items():
            target.writestr(name, value)
    chunks = chunk_document(ExcelParser().parse(path, document_id='d', revision_id='r'))
    chunk = next(c for c in chunks if c.heading_path == ('计划',))
    assert chunk.text.splitlines() == ['parameter', '---', 'actual-value']
    assert (chunk.source_refs[0].row_start, chunk.source_refs[0].row_end) == (2, 3)
    assert {r.cell for r in chunk.source_refs if r.cell} == {'A1', 'A2', 'A3'}


@pytest.mark.parametrize('prefix', ['', '前置正文\n', '前置正文\n\n'])
def test_markdown_split_table_keeps_physical_lines_and_dash_data(tmp_path, prefix):
    path = tmp_path / 'table.md'
    path.write_text(prefix + '|Name|Value|\n|--|--|\n|alpha|1|\n|beta|2|\n|---|---|', encoding='utf-8')
    doc = MarkdownParser().parse(path, document_id='d', revision_id='r')
    chunks = chunk_document(doc, max_chars=25)
    tables = [c for c in chunks if c.content_kind == 'table']
    assert len(tables) == 3
    offset = prefix.count('\n')
    for chunk, row, value in zip(tables, [3, 4, 5], ['alpha | 1', 'beta | 2', '--- | ---']):
        assert chunk.text == 'Name | Value\n' + value
        ref = chunk.source_refs[0]
        assert (ref.row_start, ref.row_end) == (offset + row, offset + row)
        assert (ref.line_start, ref.line_end) == (offset + row, offset + row)
        assert any(r.line_start == offset + 1 and r.line_end == offset + 1 for r in chunk.source_refs[1:])
    if prefix:
        assert any(c.text == '前置正文' and c.content_kind == 'text' for c in chunks)


def test_pdf_table_without_physical_rows_does_not_invent_locations():
    from app.ingestion.models import ParsedDocument, Block
    from app.knowledge.models import SourceRef
    doc = ParsedDocument(document_id='d', revision_id='r', original_sha256='a'*64, parser='pdf', parser_version='1', blocks=(
        Block(block_id='b', kind='table', rows=(('h',), ('---',), ('v',)), source_refs=(
            SourceRef(document_id='d', revision_id='r', kind='pdf', page=7),)),))
    chunks = chunk_document(doc, max_chars=8)
    assert any('---' in c.text for c in chunks)
    assert all(r.row_start is None and r.row_end is None and r.line_start is None and r.line_end is None
               for c in chunks for r in c.source_refs)


@pytest.mark.parametrize('text,paths', [
    ('# Root\n### First\n### Second\n正文', [('Root',), ('Root', 'First'), ('Root', 'Second')]),
    ('### Start\n##### Deep\n#### Back\n### Peer', [('Start',), ('Start', 'Deep'), ('Start', 'Back'), ('Peer',)]),
    ('# Root\n### Same\n### Same\n## Up', [('Root',), ('Root', 'Same'), ('Root', 'Same'), ('Root', 'Up')]),
    ('# Root\n```md\n### Ignore\n```\n### Real', [('Root',), ('Root', 'Real')]),
])
def test_markdown_heading_stack_uses_actual_levels(tmp_path, text, paths):
    path = tmp_path / 'headings.md'
    path.write_text(text, encoding='utf-8')
    doc = MarkdownParser().parse(path, document_id='d', revision_id='r')
    assert [b.heading_path for b in doc.blocks if b.kind == 'heading'] == paths
    assert all(b.heading_path == r.section_path for b in doc.blocks for r in b.source_refs)
    if text.endswith('正文'):
        assert doc.blocks[-1].heading_path == ('Root', 'Second')
