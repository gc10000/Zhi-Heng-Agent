"""SQ复审反例与相邻边界；合成资料，验证正式prompt/chunker入口。"""
import pytest
from app.answering.context_budget import pack_prompt_inputs
from app.ingestion.models import Block, ParsedDocument
from app.ingestion.stages.chunking import chunk_document, split_text, ChunkBoundaryError


@pytest.mark.parametrize('text',[
    'echo diagnostic >> trace.log',
    r'空集 $A=\emptyset$，$B=\varnothing$；x >> 2。',
    '示例 `first line\ncommand >> logfile` 保持原样。',
    '``first ` line\n点击 > > > 进入设置。``',
    '    点击 > > > 进入设置。\n',
    '```text\n点击 > > > 进入设置。\n```',
])
def test_valid_technical_evidence_reaches_actual_prompt_unchanged(answer_node,text):
    state=dict(original_query='说明技术资料',reranked_docs=[dict(chunk_id='c',text=text)])
    prompt=answer_node.module.step_2_construct_prompt(state)
    assert text.strip() in prompt
    assert state['prompt_used_docs'][0]['text']==text


@pytest.mark.parametrize('text',[
    r'点击 $> \emptyset > \emptyset$，进入电池设置页面。',
    '点击 > > > 电源和电池选项。',
])
def test_confirmed_missing_ui_path_is_marked_and_budgeted_without_mutating_source(text):
    doc=dict(chunk_id='c',text=text)
    packed=pack_prompt_inputs([doc],[],12000)
    assert '未识别图标' in packed['context']
    assert packed['used_chars']==len(packed['context'])
    assert pack_prompt_inputs([doc],[],packed['used_chars']-1)['used_doc_indices']==[]
    assert doc['text']==text


@pytest.mark.parametrize('marker',['`','~'])
def test_short_internal_fence_cannot_split_long_outer_fence_in_formal_chunker(marker):
    text=marker*4+'text\n'+marker*3+'sh\n'+('command\n'*12)+marker*3+'\n'+marker*4
    doc=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='synthetic',parser_version='1',
                       blocks=(Block(block_id='code',kind='steps',text=text),))
    with pytest.raises(ChunkBoundaryError):chunk_document(doc,max_chars=80)
    pieces=split_text('正文。\n'+text+'\n尾文。',len(text)+2)
    assert any(text in part for part in pieces) and ''.join(pieces)=='正文。\n'+text+'\n尾文。'


@pytest.mark.parametrize('wrapper',['thead','th'])
def test_explicit_headers_keep_units_and_version_on_each_data_chunk(wrapper):
    if wrapper=='thead':header='<thead><tr><td>端口</td><td>功率（W，仅固件V1）</td></tr></thead>'
    else:header='<tr><th>端口</th><th>功率（W，仅固件V1）</th></tr>'
    text='<table>'+header+'<tbody>'+''.join(f'<tr><td>接口{i}</td><td>示例范围为20到30</td></tr>' for i in range(4))+'</tbody></table>'
    doc=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='synthetic',parser_version='1',
                       blocks=(Block(block_id='t',kind='table',text=text),))
    chunks=chunk_document(doc,max_chars=45)
    assert len(chunks)==4
    assert all('功率（W，仅固件V1）' in c.text and f'接口{i}' in c.text for i,c in enumerate(chunks))


def test_multiple_thead_rows_keep_both_version_and_units_with_every_data_row():
    text='<table><thead><tr><td>接口</td><td>限制（仅固件V1）</td></tr><tr><td>名称</td><td>单位：W</td></tr></thead><tbody>'+''.join(f'<tr><td>端口{i}</td><td>最大20</td></tr>' for i in range(3))+'</tbody></table>'
    doc=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='synthetic',parser_version='1',
                       blocks=(Block(block_id='t',kind='table',text=text),))
    chunks=chunk_document(doc,max_chars=45)
    assert len(chunks)==3
    assert all('仅固件V1' in c.text and '单位：W' in c.text and f'端口{i}' in c.text for i,c in enumerate(chunks))


def test_td_column_labels_keep_parenthesized_version_without_thead():
    text='<table><tr><td>接口</td><td>说明（仅旧版本）</td></tr><tr><td>业务端口</td><td>仅限本地</td></tr></table>'
    doc=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='synthetic',parser_version='1',
                       blocks=(Block(block_id='t',kind='table',text=text),))
    chunks=chunk_document(doc)
    assert len(chunks)==1 and '仅旧版本' in chunks[0].text and '业务端口' in chunks[0].text
