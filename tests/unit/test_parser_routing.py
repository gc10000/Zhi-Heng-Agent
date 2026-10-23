"""旧入口的格式误放行必须通过真实函数路径复现。"""
import pytest


def test_legacy_entry_rejects_unsupported_instead_of_success(tmp_path):
    from app.import_process.agent.nodes.node_entry import node_entry
    from app.import_process.agent.state import create_default_state
    path=tmp_path/'manual.exe';path.write_bytes(b'not a document')
    with pytest.raises(ValueError):
        node_entry(create_default_state(task_id='routing-unsupported',local_file_path=str(path)))


def test_legacy_entry_accepts_uppercase_pdf(tmp_path):
    import fitz
    from app.import_process.agent.nodes.node_entry import node_entry
    from app.import_process.agent.state import create_default_state
    path=tmp_path/'MANUAL.PDF'
    with fitz.open() as pdf:
        pdf.new_page();pdf.save(path)
    state=node_entry(create_default_state(task_id='routing-uppercase',local_file_path=str(path)))
    assert state['is_pdf_read_enabled']


@pytest.mark.parametrize('name,data',[('fake.pdf',b'not pdf'),('fake.md',b'%PDF-binary'),('fake.xlsx',b'PK invalid'),('binary.md',b'abc\x00def')])
def test_actual_type_must_match_extension(tmp_path,name,data):
    from app.ingestion.parsers.router import detect_format
    path=tmp_path/name;path.write_bytes(data)
    with pytest.raises(ValueError): detect_format(path)


def test_router_keeps_quality_and_original_separate(tmp_path):
    from app.ingestion.parsers.router import ParserRouter
    from app.ingestion.models import ParsedDocument, Block
    path=tmp_path/'m.MD';path.write_text('# 操作',encoding='utf-8')
    class Parser:
        def parse(self,path,*,document_id,revision_id):
            return ParsedDocument(document_id=document_id,revision_id=revision_id,original_sha256='a'*64,parser='test',parser_version='1',
                                  quality_flags=('native_fallback',),blocks=(Block(block_id='b',kind='image',text='原图标题',description='模型描述'),))
    result=ParserRouter({'md':Parser()}).parse(path,document_id='d',revision_id='r')
    assert result.blocks[0].text=='原图标题' and result.blocks[0].description=='模型描述'
    assert result.quality_flags==('native_fallback',)
