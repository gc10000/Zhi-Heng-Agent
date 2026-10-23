import copy
import pytest
def _merge_short_sections(*args, **kwargs):
    from app.import_process.agent.nodes.node_document_split import _merge_short_sections as merge
    return merge(*args, **kwargs)


def step_4_refine_chunks(*args, **kwargs):
    from app.import_process.agent.nodes.node_document_split import step_4_refine_chunks as refine
    return refine(*args, **kwargs)


def section(title, content, **kwargs):
    return {'title': title, 'content': content, 'parent_title': '# 安装', 'file_title': '资料A', 'section_id': '同一已知章节', **kwargs}


def test_missing_parent_does_not_merge_unrelated_chapters():
    sections = [{'title': '# 安装', 'content': 'AAAAA'}, {'title': '# 故障', 'content': 'BBBBB'}]
    assert _merge_short_sections(sections, min_length=100) == sections


def test_same_source_parent_merge_without_mutating_input():
    sections = [section('安装-1', 'AAA', part=1), section('安装-2', 'BBB', part=2)]
    before = copy.deepcopy(sections)
    actual = _merge_short_sections(sections, 100)
    assert len(actual) == 1
    assert actual[0]['content'] == 'AAA\n\nBBB'
    assert actual[0]['file_title'] == '资料A'
    assert actual[0]['merged_titles'] == ['安装-1', '安装-2']
    assert sections == before


@pytest.mark.parametrize('change', [
    {'file_title': '资料B'}, {'item_name': '型号B'}, {'parent_title': '# 故障'},
    {'document_id': 'docB'}, {'revision_id': 'revB'}, {'section_id': 'secB'},
    {'kind': 'table'}, {'block_type': 'table'}, {'table_id': 'tableB'},
])
def test_structural_boundaries(change):
    base = {'item_name': '型号A', 'document_id': 'docA', 'revision_id': 'revA', 'section_id': 'secA', 'kind': 'text', 'block_type': 'text'}
    sections = [section('一', 'A', **base), section('二', 'B', **{**base, **change})]
    assert len(_merge_short_sections(sections, 100)) == 2


def test_missing_source_and_markdown_table_are_conservative():
    assert len(_merge_short_sections([section('一', 'A', file_title=None), section('二', 'B', file_title=None)], 100)) == 2
    assert len(_merge_short_sections([section('一', '|列|值|\n|--|--|\n|a|b|'), section('二', '说明')], 100)) == 2


def test_combined_size_checked_before_merge():
    sections = [section('一', 'A' * 400), section('二', 'B' * 1700)]
    assert len(_merge_short_sections(sections, 500)) == 2


def test_refine_respects_custom_max_and_input_metadata():
    sections = [section('一', 'A' * 40, section_id='s1', item_name='型号A'), section('二', 'B' * 70, section_id='s1', item_name='型号A')]
    before = copy.deepcopy(sections)
    actual = step_4_refine_chunks(sections, 100)
    assert len(actual) == 2
    assert sections == before
    assert all(s['item_name'] == '型号A' for s in actual)


def test_empty():
    assert _merge_short_sections([]) == []


def test_long_split_preserves_source_and_product_metadata():
    source = section('# 安装', '步骤。' * 80, document_id='doc', section_id='sec', item_name='型号A')
    before = copy.deepcopy(source)
    actual = step_4_refine_chunks([source], 100)
    assert len(actual) > 1
    assert all(c['document_id'] == 'doc' and c['section_id'] == 'sec' and c['item_name'] == '型号A' for c in actual)
    assert all(len(c['content']) <= 100 for c in actual)
    assert source == before


def test_full_title_to_refine_path_keeps_repeated_heading_instances_separate():
    from app.import_process.agent.nodes.node_document_split import step_2_split_by_titles
    content = ('## 配置\n' + ('A' * 65 + '。') * 3
               + '\n## 配置\n' + ('B' * 20 + '。') + ('B' * 80 + '。') * 3)
    sections, count, _ = step_2_split_by_titles(content, 'review-synthetic')
    before = copy.deepcopy(sections)
    assert count == 2
    chunks = step_4_refine_chunks(sections, 100)
    assert not any('A' in chunk['content'] and 'B' in chunk['content'] for chunk in chunks)
    assert sections == before
    identities = [s['section_instance_id'] for s in sections]
    assert len(set(identities)) == 2
    assert all(c['section_instance_id'] == identities[0] for c in chunks if 'A' in c['content'])
    assert all(c['section_instance_id'] == identities[1] for c in chunks if 'B' in c['content'])


@pytest.mark.parametrize('identity', [{}, {'heading_path': ['配置']}, {'section_id': ''}])
def test_same_parent_text_without_reliable_identity_does_not_merge(identity):
    metadata = {'section_id': None, **identity}
    sections = [section('配置-1', 'A', part=3, **metadata), section('配置-2', 'B', part=1, **metadata)]
    assert _merge_short_sections(sections, 100) == sections


def test_generated_same_section_children_can_merge_and_keep_identity():
    from app.import_process.agent.nodes.node_document_split import step_2_split_by_titles, _split_long_section
    sections, _, _ = step_2_split_by_titles('## 配置\n' + '合法操作。' * 8, '资料A')
    children = _split_long_section(sections[0], 35)
    assert len(children) > 1
    before = copy.deepcopy(children)
    merged = step_4_refine_chunks(children, 100)
    assert len(merged) == 1
    assert merged[0]['section_instance_id'] == sections[0]['section_instance_id']
    assert merged[0]['merged_parts'] == list(range(1, len(children) + 1))
    assert children == before


def test_refine_defaults_do_not_mutate_short_section_input():
    sections = [{'title': '配置', 'content': '短内容', 'file_title': '资料A'}]
    before = copy.deepcopy(sections)
    result = step_4_refine_chunks(sections, 100)
    assert sections == before
    assert result[0]['parent_title'] == '配置' and result[0]['part'] == 0


def test_separate_split_runs_do_not_share_section_instance():
    from app.import_process.agent.nodes.node_document_split import step_2_split_by_titles
    first, _, _ = step_2_split_by_titles('## 配置\nA', '资料A')
    second, _, _ = step_2_split_by_titles('## 配置\nB', '资料A')
    assert first[0]['section_instance_id'] != second[0]['section_instance_id']
