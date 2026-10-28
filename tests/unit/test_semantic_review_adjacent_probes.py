"""独立相邻反例，使用正式prompt/chunk_document；不改业务源码。"""
import pytest
from tests.conftest import offline_boundary,answer_node
from app.ingestion.models import Block,ParsedDocument
from app.ingestion.stages.chunking import chunk_document,ChunkBoundaryError


def document(text,kind='steps'):
    return ParsedDocument(document_id='d',revision_id='r',original_sha256='a'*64,parser='synthetic',parser_version='1',blocks=(Block(block_id='b',kind=kind,text=text),))


@pytest.mark.parametrize('separator',['\f','\u2028'])
def test_non_commonmark_separator_before_fence_keeps_actual_prompt_code(answer_node,separator):
    text=f'说明{separator}补充{separator}再说明\n~~~~text\n点击 > > > 进入设置。\n~~~~'
    state=dict(original_query='说明代码',reranked_docs=[dict(chunk_id='c',text=text)])
    prompt=answer_node.module.step_2_construct_prompt(state)
    assert state['prompt_used_docs'][0]['text']==text
    assert text in prompt


@pytest.mark.parametrize('separator',['\f','\u2028'])
def test_non_commonmark_separator_before_fence_cannot_bypass_atomic_limit(separator):
    prefix=f'说明{separator}补充{separator}再说明\n'
    code='~~~~text\n'+'long command argument '*5+'\n~~~~'
    assert len(code)>80
    with pytest.raises(ChunkBoundaryError):chunk_document(document(prefix+code),max_chars=80)


def test_image_alt_code_span_uses_root_source_offset_in_actual_prompt(answer_node):
    text='这是足够长的前文说明，用于核对源码绝对坐标。![`点击 > > > 进入设置。`](asset.png)'
    state=dict(original_query='说明示例',reranked_docs=[dict(chunk_id='c',text=text)])
    prompt=answer_node.module.step_2_construct_prompt(state)
    assert text in prompt


def test_row_scope_th_cells_are_data_not_additional_column_header_rows():
    header='<thead><tr><th>接口</th><th>限制（仅固件V1）</th></tr></thead>'
    body=''.join(f'<tr><th scope="row">端口{i}</th><td>最大20且仅限本地</td></tr>' for i in range(4))
    chunks=chunk_document(document('<table>'+header+'<tbody>'+body+'</tbody></table>','table'),max_chars=45)
    assert len(chunks)==4
    assert all('仅固件V1' in c.text and f'端口{i}' in c.text for i,c in enumerate(chunks))


@pytest.mark.parametrize('newline',['\n','\r\n'])
def test_commonmark_line_endings_keep_atomic_fence_control(newline):
    code=newline.join(['~~~~text','long command argument '*5,'~~~~'])
    with pytest.raises(ChunkBoundaryError):chunk_document(document('正文'+newline+code),max_chars=80)


def test_thead_with_td_body_remains_supported_control():
    header='<thead><tr><td>接口</td><td>限制（仅固件V1）</td></tr></thead>'
    body=''.join(f'<tr><td>端口{i}</td><td>最大20且仅限本地</td></tr>' for i in range(4))
    chunks=chunk_document(document('<table>'+header+'<tbody>'+body+'</tbody></table>','table'),max_chars=45)
    assert len(chunks)==4 and all('仅固件V1' in c.text for c in chunks)
