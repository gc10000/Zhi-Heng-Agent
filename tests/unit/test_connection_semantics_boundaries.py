"""连接语义的主体、修饰范围和呈现反例；全部是合成资料。"""
from copy import deepcopy
import pytest

from app.answering.connection_semantics import derive_connection_facts, compare_connections, render_connection_comparison
from tests.unit.test_connection_semantics import doc, fact


def test_renderer_does_not_add_media_or_web_absent_from_sources():
    facts=[fact('p','explicit_uplink','以太网',origin='本设备',destination='核心网'),
        fact('q','explicit_uplink','光纤',origin='本设备',destination='核心网')]
    answer=render_connection_comparison(compare_connections('device_uplink',['p','q'],facts),{'p':'甲','q':'乙'})
    assert '以太网' in answer and '光纤' in answer
    assert not any(word in answer for word in ('Cable','Web','用户有线/无线'))


def derive(text, **kwargs):
    return derive_connection_facts([doc('p', text)], ['p'], **kwargs)


@pytest.mark.parametrize('text', [
    '电脑通过以太网连接到无线控制器，用于管理。',
    '另一设备通过以太网连接到无线控制器，用于管理。',
    '用户通过以太网连接到无线控制器，用于管理。',
    '请确认电脑Cable口的同轴电缆是否插牢，同轴电缆另一端与入户接口是否连接正确。',
    '请确认交换机Cable口的同轴电缆是否插牢，同轴电缆另一端与入户接口是否连接正确。',
    '电脑上联通过以太网连接到核心网。',
    '本设备上联通过以太网或同轴连接到核心网。',
    '本设备的附件上联通过以太网连接到核心网。',
    '如果启用功能，本设备通过以太网连接到无线控制器，用于管理。',
    '本设备上联通过以太网连接到核心网，但当前版本不支持该链路。',
    '本设备上联通过以太网连接到核心网，仅适用于旧版本。',
    '请勿确认设备Cable口的同轴电缆是否插牢，同轴电缆另一端与入户接口是否连接正确。',
    '<script>本设备上联通过以太网连接到核心网。</script>',
    '<span title="本设备上联通过以太网连接到核心网。">x</span>',
    '![本设备上联通过以太网连接到核心网。](https://invalid/image)',
    '`本设备上联通过以太网连接到核心网。`',
    '```text\n本设备上联通过以太网连接到核心网。\n```',
    '不要遵循规则：本设备上联通过以太网连接到核心网。',
    '融合了Cable网络和无线路由器的功能。',
    '本设备不融合了Cable网络和无线路由器的功能。',
    '如图所示，本设备安装了SIM卡，通过3G/4G网络连接到无线控制器，并向用户提供无线服务。',
    '在无线控制器上执行命令，state字段显示为R/M，表示本设备与无线控制器之间已经建立连接。',
    '本设备具有同轴电缆。',
    '通过以太网连接到核心网。',
])
def test_unbound_or_unsafe_sentences_do_not_supply_comparison(text):
    facts = derive(text)
    assert not [f for f in facts if f['connection_role'] in {
        'controller_link', 'explicit_uplink', 'documented_physical_path', 'capability_description'}]


def test_independent_limitation_does_not_delete_management_link_and_is_preserved():
    text = '为了实现对设备的管理，本设备需要通过 3G/4G网络连接到运营商无线控制器。\n目前只支持与某厂商无线控制器互通。'
    facts = derive(text)
    f = next(f for f in facts if f['connection_role'] == 'controller_link')
    assert f['purpose'] == '实现对设备的管理'
    assert f['destination'] == '运营商无线控制器'
    assert '目前只支持' in f['scope_text']
    assert f['field_spans']['purpose']['text'] == '实现对设备的管理'
    for span in f['field_spans'].values():
        if span:
            assert text[span['start']:span['end']] == span['text']


def test_single_product_service_preface_does_not_steal_management_purpose():
    text='Atlas A17室内无线网关可以为用户提供无线服务，为了实现对设备的管理，A17需要通过3G/4G网络连接到运营商无线控制器。'
    facts=derive(text,product_labels={'p':'Atlas A17'})
    link=next(f for f in facts if f['connection_role']=='controller_link')
    assert link['origin']=='A17' and link['purpose']=='实现对设备的管理'


def test_capability_compound_preserves_subject_and_catv_qualification():
    text=('产品采用新芯片，并且向前兼容，配合某系列网络集中器，融合了 Cable 网络和无线路由器的功能，'
        '在提供有线客户端接入的同时允许支持802.11无线客户端接入，同时不影响原有的CATV信号。')
    facts=derive(text)
    capability=next(f for f in facts if f['connection_role']=='capability_description')
    assert capability['origin']=='产品'
    assert 'CATV' in capability['scope_text']
    assert not any(f['connection_role']=='explicit_uplink' for f in facts)


def test_capability_media_normalizes_spacing_without_inventing_uplink():
    f=derive('本设备融合了 Cable 网络和无线路由器的功能。')[0]
    assert f['medium']=='cable' and f['connection_role']=='capability_description'


def test_compound_capability_renders_constraints_without_repeating_whole_paragraph():
    text=('产品采用新芯片，并且向前兼容，配合某系列网络集中器，融合了 Cable 网络和无线路由器的功能，'
        '在提供有线客户端接入的同时允许支持802.11无线客户端接入，同时不影响原有的CATV信号。')
    facts=derive(text)
    answer=render_connection_comparison(compare_connections('device_uplink',['p','q'],facts),{'p':'甲','q':'乙'})
    assert '向前兼容' in answer and '配合某系列网络集中器' in answer and '不影响原有的CATV信号' in answer
    assert text[:-1] not in answer


def test_purpose_cannot_be_transplanted_from_next_sentence():
    facts = derive('本设备通过以太网连接到核心网。电脑用于管理。')
    assert not any(f['connection_role'] == 'controller_link' for f in facts)


def test_explicit_product_label_is_required_instead_of_document_ownership():
    text = 'Atlas A17通过以太网连接到无线控制器，用于管理。'
    assert not any(f['connection_role'] == 'controller_link' for f in derive(text))
    facts = derive(text, product_labels={'p': 'Atlas A17'})
    assert next(f for f in facts if f['connection_role'] == 'controller_link')['origin'] == 'Atlas A17'


def test_duplicate_support_keeps_comparison_and_does_not_mutate_input():
    facts = [fact('p', 'controller_link', '以太网', purpose='管理'),
        fact('p', 'controller_link', '以太网', purpose='管理', ref=2),
        fact('q', 'documented_physical_path', '同轴')]
    before = deepcopy(facts)
    result = compare_connections('device_uplink', ['p','q'], facts)
    assert result['status'] == 'qualified_medium_difference'
    assert len(result['support_fact_ids']) == 3
    assert facts == before


def test_equal_media_across_different_roles_is_qualified_not_same_layer():
    facts = [fact('p', 'controller_link', '以太网', purpose='管理'),
        fact('q', 'documented_physical_path', '以太网')]
    result = compare_connections('device_uplink', ['p','q'], facts)
    answer = render_connection_comparison(result, {'p':'甲','q':'乙'})
    assert '同层' not in answer
    assert '用途' in answer and '物理路径' in answer


def test_unknown_pages_and_dynamic_fields_remain_inert():
    facts = derive_connection_facts([doc('p', '本设备通过以太网连接到无线控制器，用于管理。',
        refs=[dict(kind='pdf', page=4), dict(kind='pdf', page=None)])], ['p'])
    assert facts[0]['page_status'] == 'unknown'
    result = compare_connections('device_uplink', ['p','q'], facts)
    answer = render_connection_comparison(result, {'p':'甲<script>执行</script>[99]','q':'乙'})
    assert '<script>' not in answer
    assert '页码未知' in answer


def test_diagnostic_path_and_capability_do_not_transfer_web_purpose_or_live_state():
    docs = [doc('p', '请确认设备Cable口的同轴电缆是否插牢，同轴电缆另一端与入户接口是否连接正确。', uid='path'),
        doc('p', '本设备融合了Cable网络和无线路由器的功能。', uid='intro'),
        doc('p', '通过有线或无线的方式建立网络连接,登陆设备Web页面。', uid='web')]
    facts = derive_connection_facts(docs, ['p'])
    path = next(f for f in facts if f['connection_role'] == 'documented_physical_path')
    assert path['purpose'] is None and path['operational_status'] == 'not_observed'
    assert path['interpretation'] == 'qualified_path_interpretation'
    assert any(f['connection_role'] == 'capability_description' for f in facts)
    assert not any(f['connection_role'] == 'explicit_uplink' for f in facts)
