"""XLSX直接读取OpenXML全部非空单元格；不计算公式，不混淆缓存值。"""
from pathlib import Path
import posixpath
import zipfile
import xml.etree.ElementTree as ET
from app.knowledge.models import SourceRef, content_hash, stable_id
from app.ingestion.models import Block,Cell,ParsedDocument

NS={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL='http://schemas.openxmlformats.org/officeDocument/2006/relationships'


class ExcelParser:
    def __init__(self,*,purpose=None): self.purpose=purpose

    def parse(self,path,*,document_id,revision_id):
        path=Path(path);blocks=[];flags=[];all_text=[]
        with zipfile.ZipFile(path) as book:
            if sum(i.file_size for i in book.infolist())>512_000_000: raise ValueError('工作簿解压体积过大')
            strings=[]
            if 'xl/sharedStrings.xml' in book.namelist():
                strings=[''.join(n.text or '' for n in si.findall('.//m:t',NS)) for si in ET.fromstring(book.read('xl/sharedStrings.xml')).findall('m:si',NS)]
            relationships={r.get('Id'):r.get('Target') for r in ET.fromstring(book.read('xl/_rels/workbook.xml.rels'))}
            workbook=ET.fromstring(book.read('xl/workbook.xml'))
            for sheet in workbook.findall('m:sheets/m:sheet',NS):
                name=sheet.get('name');target=relationships[sheet.get('{'+REL+'}id')]
                target=posixpath.normpath(target.lstrip('/') if target.startswith('/') else 'xl/'+target)
                if not target.startswith('xl/'): raise ValueError('工作表引用越界')
                root=ET.fromstring(book.read(target))
                for row in root.findall('m:sheetData/m:row',NS):
                    cells=[]
                    for node in row.findall('m:c',NS):
                        value=node.find('m:v',NS);raw=value.text if value is not None else None
                        if node.get('t')=='s' and raw is not None: raw=strings[int(raw)]
                        elif node.get('t')=='inlineStr': raw=''.join(n.text or '' for n in node.findall('.//m:t',NS))
                        formula=node.find('m:f',NS)
                        if formula is not None:
                            if raw is None: flags.append('formula_cache_missing')
                            cell=Cell(coordinate=node.get('r'),formula='='+(formula.text or ''),cached_value=raw)
                        elif raw is not None and raw!='': cell=Cell(coordinate=node.get('r'),value=raw)
                        else: continue
                        cells.append(cell)
                    if not cells: continue
                    line=' | '.join(c.coordinate+': '+(f'公式{c.formula}；缓存{c.cached_value if c.cached_value is not None else "未知"}' if c.formula is not None else c.value) for c in cells)
                    all_text.append(line)
                    refs=tuple(SourceRef(document_id=document_id,revision_id=revision_id,kind='excel',sheet=name,cell=c.coordinate,
                                         row_start=int(row.get('r')),row_end=int(row.get('r'))) for c in cells)
                    blocks.append(Block(block_id=stable_id('block',revision_id,[name,row.get('r')]),kind='table',text=line,heading_path=(name,),
                                        source_refs=refs,cells=tuple(cells),rows=(tuple(c.formula or c.value or '' for c in cells),)))
        text='\n'.join(all_text)
        purpose=self.purpose or ('project_plan' if any(w in path.stem for w in ('项目计划','课程计划','排期')) or ('负责人' in text and '任务' in text) else 'unknown')
        return ParsedDocument(document_id=document_id,revision_id=revision_id,original_sha256=content_hash(path.read_bytes()),parser='xlsx-openxml',parser_version='1',
                              purpose=purpose,quality_flags=tuple(sorted(set(flags))),blocks=tuple(blocks))
