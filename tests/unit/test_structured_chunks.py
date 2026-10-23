"""N1旧路径红测及结构化块来源/范围/稳定性。"""
import pytest


@pytest.mark.parametrize('title,text',[('短标题','长'*2500),('题'*2300,'正文'*1500)],ids=['continuous','long-title'])
def test_legacy_continuous_text_and_long_title_respect_limit(title,text):
    from app.import_process.agent.nodes.node_document_split import step_4_refine_chunks
    result=step_4_refine_chunks([{'title':title,'content':text,'file_title':'f'}],2000)
    assert result and all(len(b['content'])<=2000 for b in result)
    combined=''.join(b['content'].removeprefix(title+'\n\n') for b in result)
    assert combined==text


def test_structured_chunks_keep_table_headers_rows_assets_and_products():
    from app.knowledge.models import SourceRef
    from app.ingestion.models import ParsedDocument,Block
    from app.ingestion.stages.chunking import chunk_document
    ref=SourceRef(document_id='d',revision_id='r',kind='excel',sheet='参数',row_start=1,row_end=20)
    rows=(('参数','值'),)+tuple((f'参数{i}','值'*15) for i in range(1,20))
    parsed=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='test',parser_version='1',blocks=(
        Block(block_id='table',kind='table',rows=rows,source_refs=(ref,),heading_path=('参数',),product_ids=('p1',),asset_ids=('a',)),
        Block(block_id='warning',kind='warning',text='警告：禁止带电操作',source_refs=(ref,),product_ids=('p2',))))
    chunks=chunk_document(parsed,max_chars=150)
    assert all(len(c.text)<=150 for c in chunks)
    tables=[c for c in chunks if c.content_kind=='table']
    assert len(tables)>1 and all(c.text.startswith('参数 | 值\n') for c in tables)
    assert all(c.asset_ids==('a',) and c.product_ids==('p1',) for c in tables)
    assert tables[0].source_refs[0].row_start==2
    assert tables[-1].source_refs[0].row_end==20
    assert chunks[-1].product_ids==('p2',)
    assert [c.chunk_uid for c in chunk_document(parsed,max_chars=150)]==[c.chunk_uid for c in chunks]


def test_long_unbroken_text_heading_and_parent_relationship():
    from app.ingestion.models import ParsedDocument,Block
    from app.ingestion.stages.chunking import chunk_document
    text='字'*2500
    doc=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='t',parser_version='1',
                       blocks=(Block(block_id='b',kind='steps',text=text,heading_path=('题'*2300,)),))
    chunks=chunk_document(doc,max_chars=2000)
    assert all(len(c.text)<=2000 for c in chunks)
    assert ''.join(c.text for c in chunks)==text
    assert all(c.heading_path==('题'*2300,) for c in chunks)
    assert chunks[0].parent_chunk_uid is None and chunks[1].parent_chunk_uid==chunks[0].chunk_uid


def test_oversized_atomic_image_marker_or_table_row_is_explicit_error():
    from app.ingestion.models import ParsedDocument,Block
    from app.ingestion.stages.chunking import chunk_document,ChunkBoundaryError
    for block in (Block(block_id='i',kind='text',text='![a]('+('u'*200)+')'),
                  Block(block_id='t',kind='table',rows=(('h',),('x'*200,)))):
        doc=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='t',parser_version='1',blocks=(block,))
        with pytest.raises(ChunkBoundaryError):chunk_document(doc,max_chars=100)


def test_excel_chunks_preserve_actual_cell_rows_and_one_header(tmp_path):
    from app.ingestion.parsers.excel import ExcelParser
    from app.ingestion.stages.chunking import chunk_document
    from tests.unit.test_tabular_sources import make_workbook
    path=tmp_path/'parameters.xlsx';make_workbook(path)
    parsed=ExcelParser().parse(path,document_id='d',revision_id='r')
    chunks=chunk_document(parsed,max_chars=300)
    first=next(c for c in chunks if c.heading_path==('计划',))
    assert first.text.startswith('负责人 | 任务')
    assert first.source_refs[0].row_start==2 and first.source_refs[0].row_end==2
    assert any(ref.cell=='D2' and ref.row_start==2 for ref in first.source_refs)


def test_cross_revision_source_is_rejected():
    from app.knowledge.models import SourceRef
    from app.ingestion.models import Block,ParsedDocument
    from app.ingestion.stages.chunking import chunk_document
    doc=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='t',parser_version='1',
                       blocks=(Block(block_id='b',kind='text',text='content',source_refs=(SourceRef(document_id='d',revision_id='other',kind='legacy'),)),))
    with pytest.raises(ValueError):chunk_document(doc)
