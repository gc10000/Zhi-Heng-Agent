"""M6源内容完整性回归；全部为合成资料，不调用解析/生成供应商。"""
from copy import deepcopy
import pytest
from app.ingestion.models import Block, ParsedDocument
from app.ingestion.stages.chunking import chunk_document, split_text, ChunkBoundaryError
from app.knowledge.models import SourceRef
from app.retrieval.query_planner import plan_query


def document(blocks):
    return ParsedDocument(document_id='d', revision_id='r', original_sha256='a'*64,
                          parser='synthetic', parser_version='1', blocks=tuple(blocks))


def ref(page):
    return SourceRef(document_id='d', revision_id='r', kind='pdf', page=page)


def test_actual_pdf_adapter_preserves_provider_code_body_and_physical_page(tmp_path):
    import fitz
    from app.ingestion.parsers.mineru import MineruParser
    path=tmp_path/'manual.pdf'
    with fitz.open() as pdf:
        pdf.new_page(); pdf.new_page(); pdf.save(path)
    class CachedProvider:
        version='synthetic-code'
        def parse_segment(self, path, work):
            return dict(blocks=[dict(type='code', code_body='```txt\n[GW]set route example\n```', page_idx=1)],flags=[])
    parsed=MineruParser(CachedProvider(),tmp_path/'cache').parse(path,document_id='d',revision_id='r')
    chunks=chunk_document(parsed)
    assert [c.text for c in chunks]==['```txt\n[GW]set route example\n```']
    assert chunks[0].source_refs[0].page==2


def test_fenced_cli_unit_moves_whole_instead_of_cutting_a_command():
    cli='```txt\n[GW]set address example\n[GW]enable service\n```'
    parts=split_text('说明。'*15+'\n'+cli,65)
    assert cli in parts
    assert ''.join(parts)=='说明。'*15+'\n'+cli


def test_oversized_cli_unit_is_explicit_failure_instead_of_corrupted_syntax():
    with pytest.raises(ChunkBoundaryError): split_text('```txt\n'+('command '*20)+'\n```',40)


def test_cross_page_neighbour_steps_keep_continuation_and_all_source_refs():
    blocks=[Block(block_id='a',kind='text',text='缺省提供一个名为',heading_path=('配置',),source_refs=(ref(1),)),
            Block(block_id='b',kind='text',text='EXAMPLE_XXXX 的网络；后缀取设备标识。',heading_path=('配置',),source_refs=(ref(2),))]
    before=deepcopy(blocks)
    chunks=chunk_document(document(blocks))
    assert len(chunks)==1
    assert 'EXAMPLE_XXXX' in chunks[0].text and '缺省提供一个名为' in chunks[0].text
    assert [r.page for r in chunks[0].source_refs]==[1,2]
    assert blocks==before


@pytest.mark.parametrize('change',[dict(heading_path=('别章',)),dict(product_ids=('other',)),
                                   dict(source_refs=(ref(4),)),dict(kind='warning')])
def test_step_coalescing_never_crosses_section_product_page_gap_or_warning(change):
    first=Block(block_id='a',kind='steps',text='1 连接本地网络。',heading_path=('配置',),source_refs=(ref(1),))
    second=first.model_copy(update=dict(block_id='b',text='2 禁用其他网卡。')|change)
    assert len(chunk_document(document([first,second])))==2


def test_headerless_key_value_table_indexes_each_object_without_false_header():
    table='<table><tr><td>机身接口</td><td>连接有线网络。</td></tr><tr><td>扩展坞充电口</td><td>仅充电，不传数据。</td></tr></table>'
    chunks=chunk_document(document([Block(block_id='t',kind='table',text=table,heading_path=('接口',),source_refs=(ref(3),))]))
    assert [c.text for c in chunks]==['机身接口 | 连接有线网络。','扩展坞充电口 | 仅充电，不传数据。']
    assert all(c.source_refs[0].page==3 for c in chunks)
    assert chunks[1].parent_chunk_uid is None


def test_real_table_header_is_repeated_and_limits_preserved():
    table='<table><tr><th>接口</th><th>限制</th></tr>'+''.join(f'<tr><td>端口{i}</td><td>仅部分型号可用。</td></tr>' for i in range(8))+'</table>'
    chunks=chunk_document(document([Block(block_id='t',kind='table',text=table)]),max_chars=65)
    assert len(chunks)>1 and all(c.text.startswith('接口 | 限制\n') and len(c.text)<=65 for c in chunks)


@pytest.mark.parametrize('question',['G540 上的 USB 2.0 接口每台都有卡槽吗？',
    '仅凭 G540 型号能否确定 USB 2.0 位置一定相同？',
    'MateDock 3 上标为 USB-C 充电的接口能传数据吗？','MateDock 2 上 HDMI 与 VGA 能否并行输出？'])
def test_known_interface_and_source_owned_accessory_enter_retrieval(question):
    products=[dict(product_id='pc',model='华为擎云 G540',brand='华为',aliases=['G540']),
              dict(product_id='gw',model='AX-24')]
    plan=plan_query(question,products,selected_ids=['pc'])
    assert plan.route=='answer' and plan.product_ids==('pc',) and not plan.unconfirmed_tokens
    assert plan.original_query==question and plan.search_queries==(question,)


@pytest.mark.parametrize('question',['G540 型号：USB 2.0 如何接线？', 'G540 和 MateDock 7 如何接线？',
                                    '型号AX-42如何接线？','我的网关怎样连接管理端？'])
def test_interface_and_accessory_rules_do_not_resolve_unknown_devices(question):
    products=[dict(product_id='pc',model='华为擎云 G540',brand='华为',aliases=['G540']),dict(product_id='gw',model='AX-24')]
    assert plan_query(question,products).route=='clarify'


def test_accessory_provenance_is_not_applied_to_other_product_or_brand():
    products=[dict(product_id='pc',model='Other G540',brand='Other',aliases=['G540'])]
    assert plan_query('MateDock 3 的充电接口',products,selected_ids=['pc']).route=='clarify'


def test_layout_image_between_sentence_and_continuation_keeps_both_text_and_asset():
    blocks=[Block(block_id='a',kind='text',text='缺省提供一个名为',heading_path=('配置',),source_refs=(ref(1),)),
            Block(block_id='image',kind='image',text='连接示意',asset_ids=('asset',),heading_path=('配置',),source_refs=(ref(1),)),
            Block(block_id='b',kind='text',text='EXAMPLE_XXXX 的网络；后缀取设备标识。',heading_path=('配置',),source_refs=(ref(1),))]
    chunks=chunk_document(document(blocks))
    assert any('缺省提供一个名为' in c.text and 'EXAMPLE_XXXX' in c.text for c in chunks)
    assert any(c.asset_ids==('asset',) for c in chunks)


def test_unresolved_navigation_icons_are_not_passed_as_an_executable_path(answer_node):
    state=dict(original_query='怎样检查当前电量？',reranked_docs=[dict(chunk_id='icon',
        text=r'点击 $> \emptyset > \emptyset$，进入电池设置页面。',title='电池设置')])
    prompt=answer_node.module.step_2_construct_prompt(state)
    assert r'\emptyset' not in prompt
    assert '电池设置页面' in prompt and '未识别图标' in prompt
    assert state['prompt_used_docs'][0]['text']==r'点击 $> \emptyset > \emptyset$，进入电池设置页面。'


def test_readability_projection_preserves_literal_cli_and_inline_code():
    from app.answering.context_budget import pack_prompt_inputs
    text='```txt\ncommand >> logfile\n>>> prompt\n> > > literal\n```\n`> > >`\n点击 > > > 进入设置。'
    value=pack_prompt_inputs([dict(chunk_id='c',text=text)],[],12000)['context']
    assert 'command >> logfile' in value and '>>> prompt' in value
    assert '> > > literal' in value and '`> > >`' in value
    assert '未识别图标路径' in value


def test_multicolumn_table_retains_its_header_with_data():
    table='<table><tr><td>参数</td><td>值</td><td>适用范围</td></tr><tr><td>速率</td><td>示例值</td><td>部分型号</td></tr></table>'
    chunks=chunk_document(document([Block(block_id='t',kind='table',text=table)]))
    assert chunks[0].text=='参数 | 值 | 适用范围\n速率 | 示例值 | 部分型号'


def test_two_column_table_with_td_header_retains_column_meaning():
    table='<table><tr><td>参数</td><td>说明</td></tr><tr><td>超时</td><td>只适用于旧版本。</td></tr><tr><td>地址</td><td>示例必须按现场修改。</td></tr></table>'
    chunks=chunk_document(document([Block(block_id='t',kind='table',text=table)]),max_chars=40)
    assert all(c.text.startswith('参数 | 说明\n') for c in chunks)
    assert any('旧版本' in c.text for c in chunks) and any('现场修改' in c.text for c in chunks)


def test_actual_ranker_receives_object_heading_without_modifying_evidence(monkeypatch):
    from app.runs.query_runner import rerank
    from app.lm import reranker_utils
    pairs=[]
    def score(values,**kw):
        pairs.extend(values); return [.2,.8]
    monkeypatch.setattr(reranker_utils,'compute_rerank_scores',score)
    docs=[dict(chunk_id='dock',text='LAN连接网线。',title='配件/扩展坞'),
          dict(chunk_id='body',text='RJ45连接网线。',metadata=dict(heading_path=['机身/接口']))]
    before=deepcopy(docs)
    result=rerank('机身如何连接网线',docs)
    assert '配件/扩展坞' in pairs[0][1] and '机身/接口' in pairs[1][1]
    assert [r['chunk_id'] for r in result]==['body','dock']
    assert docs==before and result[0]['text']=='RJ45连接网线。'
