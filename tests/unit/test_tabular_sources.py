"""合成工作簿/Markdown验证真实解析，不调用供应商。"""
from pathlib import Path
import zipfile


def make_workbook(path):
    with zipfile.ZipFile(path,'w') as z:
        z.writestr('[Content_Types].xml','<Types/>')
        z.writestr('xl/workbook.xml','<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="计划" sheetId="1" r:id="r1"/><sheet name="参数" sheetId="2" r:id="r2"/></sheets></workbook>')
        z.writestr('xl/_rels/workbook.xml.rels','<Relationships><Relationship Id="r1" Target="worksheets/s1.xml"/><Relationship Id="r2" Target="worksheets/s2.xml"/></Relationships>')
        z.writestr('xl/worksheets/s1.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>负责人</t></is></c><c r="B1" t="inlineStr"><is><t>任务</t></is></c></row><row r="2"><c r="A2"><f>SUM(B2:C2)</f><v>7</v></c><c r="B2"><v>0</v></c><c r="D2"><f>1+2</f></c></row></sheetData></worksheet>')
        z.writestr('xl/worksheets/s2.xml','<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData><row r="1"><c r="A1" t="inlineStr"><is><t>功率</t></is></c><c r="B1"><v>12</v></c></row></sheetData></worksheet>')


def test_all_sheets_formula_cache_and_zero_are_preserved(tmp_path):
    from app.ingestion.parsers.excel import ExcelParser
    path=tmp_path/'项目计划.xlsx';make_workbook(path)
    result=ExcelParser().parse(path,document_id='d',revision_id='r')
    assert result.purpose=='project_plan'
    assert {r.sheet for b in result.blocks for r in b.source_refs}=={'计划','参数'}
    cells={(b.source_refs[0].sheet,c.coordinate):c for b in result.blocks for c in b.cells}
    assert cells['计划','A2'].formula=='=SUM(B2:C2)'
    assert cells['计划','A2'].cached_value=='7' and cells['计划','A2'].value is None
    assert cells['计划','B2'].value=='0'
    assert cells['计划','D2'].cached_value is None and cells['计划','D2'].formula=='=1+2'
    assert all(r.page is None for b in result.blocks for r in b.source_refs)


def test_unknown_excel_not_assumed_technical(tmp_path):
    from app.ingestion.parsers.excel import ExcelParser
    path=tmp_path/'unknown.xlsx';make_workbook(path)
    assert ExcelParser().parse(path,document_id='d',revision_id='r').purpose!='technical'


def test_markdown_keeps_hierarchy_line_numbers_images_and_fenced_code(tmp_path):
    from app.ingestion.parsers.markdown import MarkdownParser
    path=tmp_path/'manual.md'
    path.write_text('# 主标题\n\n## 配置\n\n1. 步骤一\n2. 步骤二\n\n![拓扑](image.png)\n\n```text\n# 代码不是标题\n```\n',encoding='utf-8')
    (tmp_path/'image.png').write_bytes(b'local-image')
    result=MarkdownParser().parse(path,document_id='d',revision_id='r')
    assert len([b for b in result.blocks if b.kind=='heading'])==2
    steps=next(b for b in result.blocks if b.kind=='steps')
    assert steps.heading_path==('主标题','配置')
    assert steps.source_refs[0].line_start==5 and steps.source_refs[0].line_end==6
    assert len(result.images)==1 and '![拓扑](image.png)' in '\n'.join(b.text for b in result.blocks)
    assert '# 代码不是标题' in '\n'.join(b.text for b in result.blocks)


def test_markdown_missing_image_is_quality_flag_and_remote_not_downloaded(tmp_path):
    from app.ingestion.parsers.markdown import MarkdownParser
    path=tmp_path/'m.md';path.write_text('![缺图](missing.png)\n![远程](https://example.invalid/a.png)',encoding='utf-8')
    result=MarkdownParser().parse(path,document_id='d',revision_id='r')
    assert {'missing_image','external_image_unresolved'}<=set(result.quality_flags)
    assert not result.images
