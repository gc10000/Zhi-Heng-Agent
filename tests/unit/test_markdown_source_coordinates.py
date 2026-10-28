"""原始源码坐标回归：不把Unicode分隔符当Markdown换行。"""
import pytest
from app.answering.context_budget import pack_prompt_inputs
from app.ingestion.stages.chunking import split_text,ChunkBoundaryError,chunk_document
from app.ingestion.models import Block,ParsedDocument


@pytest.mark.parametrize('newline',['\n','\r\n','\r'])
@pytest.mark.parametrize('separator',['\f','\u2028','\u2029','\x85'])
def test_original_code_and_line_endings_survive_projection_and_atomic_split(newline,separator):
    code=newline.join(['~~~~text','点击 > > > 进入设置。','~~~~'])
    text='前文'+separator+'补充'+separator+'结束'+newline+code+newline+'点击 > > > 电源选项。'
    packed=pack_prompt_inputs([dict(chunk_id='c',text=text)],[],12000)
    assert code in packed['context'] and '未识别图标' in packed['context']
    with pytest.raises(ChunkBoundaryError):split_text(text,len(code)-1)
    parts=split_text(text,len(code)+2)
    assert any(code in p for p in parts) and ''.join(parts)==text


@pytest.mark.parametrize('prefix',['短。','很长的前文说明。'*12])
@pytest.mark.parametrize('alt',['`点击 > > > 进入设置。`','![`点击 > > > 进入设置。`](inner.png)'])
def test_nested_image_alt_code_coordinates_do_not_hide_adjacent_navigation(answer_node,prefix,alt):
    image=f'![{alt}](asset.png)'
    text=prefix+image+' 点击 > > > 电源选项。'
    state=dict(original_query='说明示例',reranked_docs=[dict(chunk_id='c',text=text)])
    prompt=answer_node.module.step_2_construct_prompt(state)
    assert image in prompt and '未识别图标' in prompt
    assert state['prompt_used_docs'][0]['text']==text


@pytest.mark.parametrize('scope',['row','rowgroup'])
def test_row_headers_keep_names_with_multirow_column_conditions(scope):
    head='<thead><tr><th scope="col">接口</th><th scope="col">仅V1</th></tr><tr><th scope="col">名称</th><th scope="col">单位W</th></tr></thead>'
    body=''.join(f'<tr><th scope="{scope}">端口{i}</th><td>最大20</td></tr>' for i in range(3))
    doc=ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='synthetic',parser_version='1',
        blocks=(Block(block_id='t',kind='table',text='<table>'+head+'<tbody>'+body+'</tbody></table>'),))
    chunks=chunk_document(doc,max_chars=35)
    assert len(chunks)==3 and all('仅V1' in c.text and '单位W' in c.text and f'端口{i}' in c.text for i,c in enumerate(chunks))
