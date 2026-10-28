"""独立离线反例：使用真实parser/chunker/prompt入口，无供应商/数据库。"""
from copy import deepcopy
import pytest
from tests.conftest import offline_boundary, answer_node
from app.answering.context_budget import pack_prompt_inputs
from app.ingestion.stages.chunking import chunk_document, split_text, ChunkBoundaryError
from app.ingestion.models import ParsedDocument, Block


def test_raw_mineru_code_body_keeps_shell_redirection_in_prompt(tmp_path,answer_node):
    import fitz
    from app.ingestion.parsers.mineru import MineruParser
    path=tmp_path/'manual.pdf'
    with fitz.open() as pdf:
        pdf.new_page();pdf.save(path)
    command='echo diagnostic >> trace.log'
    class CachedProvider:
        version='independent-raw-code'
        def parse_segment(self,path,work):
            return {'blocks':[{'type':'code','code_body':command,'page_idx':0}],'flags':[]}
    parsed=MineruParser(CachedProvider(),tmp_path/'cache').parse(path,document_id='d',revision_id='r')
    chunks=chunk_document(parsed)
    docs=[{'chunk_id':c.chunk_uid,'text':c.text} for c in chunks]
    before=deepcopy(docs)
    state={'original_query':'怎样把诊断信息追加到日志？','reranked_docs':docs}
    prompt=answer_node.module.step_2_construct_prompt(state)
    assert docs==before and chunks[0].text==command
    assert state['prompt_used_docs'][0]['text']==command
    assert command in prompt


def test_legitimate_set_notation_is_not_an_unrecognized_ui_icon():
    text=r'定义空集 $A=\emptyset$，且 $B=\varnothing$。'
    packed=pack_prompt_inputs([{'chunk_id':'formula','text':text}],[],12000)
    assert text in packed['context']


def test_multiline_inline_code_keeps_shift_and_redirection_literals():
    text='示例为 `first line\ncommand >> logfile`，不要改写操作符。'
    packed=pack_prompt_inputs([{'chunk_id':'inline','text':text}],[],12000)
    assert text in packed['context']


def test_long_fence_does_not_close_on_shorter_internal_fence():
    text='````text\n```shell\necho diagnostic\n```\n'+'example line\n'*8+'````'
    # 整个有效四反引号代码块超限，应明确拒绝，不能把内部三反引号当结束符切碎。
    with pytest.raises(ChunkBoundaryError):split_text(text,80)


def test_two_column_thead_td_header_keeps_column_qualification():
    table='<table><thead><tr><td>接口</td><td>限制（仅固件V1）</td></tr></thead><tbody><tr><td>管理端口</td><td>不得远程访问</td></tr><tr><td>业务端口</td><td>允许本地访问</td></tr></tbody></table>'
    doc=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='synthetic',parser_version='1',
        blocks=(Block(block_id='table',kind='table',text=table),))
    chunks=chunk_document(doc,max_chars=70)
    assert all('限制（仅固件V1）' in c.text for c in chunks if '管理端口' in c.text or '业务端口' in c.text)


def test_existing_fenced_code_remains_unchanged_control():
    text='```sh\necho diagnostic >> trace.log\n```'
    assert text in pack_prompt_inputs([{'chunk_id':'c','text':text}],[],12000)['context']


def test_actual_missing_navigation_icon_remains_explicit_control():
    text=r'点击 $> \emptyset > \emptyset$，进入电池设置页面。'
    value=pack_prompt_inputs([{'chunk_id':'nav','text':text}],[],12000)['context']
    assert '未识别图标' in value and '电池设置页面' in value
