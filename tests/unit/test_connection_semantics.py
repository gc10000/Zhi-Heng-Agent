import pytest

from app.answering.connection_semantics import (
    derive_connection_facts, compare_connections, render_connection_comparison,
)


def doc(pid, text, heading='产品概述', refs=None, uid=None):
    return dict(chunk_uid=uid or pid + '-chunk', document_id='d-' + pid,
        revision_id='r-' + pid, ordinal=0, text=text,
        metadata=dict(product_ids=[pid], heading_path=[heading], content_kind='text',
            source_refs=refs or [dict(document_id='d-' + pid, revision_id='r-' + pid,
                kind='pdf', page=4)]))


def fact(pid, role, medium, *, speech='statement', purpose=None, status='not_observed',
         origin=None, destination=None, ref=1, clause='原句'):
    return dict(product_id=pid, connection_role=role, speech_act=speech,
        medium=medium, purpose=purpose, operational_status=status, origin=origin,
        destination=destination, reference_number=ref, clause=clause,
        source_chunk_uid=pid + '-chunk', source_span=dict(start=0, end=len(clause), text=clause),
        scope_text=clause, physical_pages=[4], page_status='exact', rule_id='fixture',
        rule_version='connection_comparison_v1')


def test_management_and_diagnostic_path_are_separate_facts():
    assembly = [
        doc('la', 'LA2608需要通过3G/4G网络连接到运营商无线控制器，用于管理。'),
        doc('cb', '请确认设备Cable口的同轴电缆是否插牢，同轴电缆另一端与入户接口是否连接正确。', '排障'),
    ]
    facts = derive_connection_facts(assembly, ['la', 'cb'], {'la':'H3C LA2608', 'cb':'Aolynk CB304n'})
    la = next(f for f in facts if f['product_id'] == 'la' and f['connection_role'] == 'controller_link')
    cb = next(f for f in facts if f['product_id'] == 'cb' and f['connection_role'] == 'documented_physical_path')
    assert la['medium'] == 'cellular_3g4g' and la['purpose'] == '管理'
    assert cb['medium'] == 'coaxial' and cb['operational_status'] == 'not_observed'
    assert all(f['speech_act'] != 'diagnostic_instruction' for f in [la])


def test_client_access_is_not_a_uplink_fact():
    assembly = [doc('p', '您可以通过有线方式或无线方式连接到设备。')]
    facts = derive_connection_facts(assembly, ['p'])
    assert facts and all(f['connection_role'] == 'client_access' for f in facts)
    result = compare_connections('device_uplink', ['p', 'q'], facts)
    assert result['status'] == 'insufficient'
    assert result['support_fact_ids'] == []


def test_product_introduction_is_capability_not_wireless_backhaul():
    assembly = [doc('p', '本设备融合了Cable网络和无线路由器的功能，并提供无线客户端接入。')]
    facts = derive_connection_facts(assembly, ['p'])
    assert any(f['connection_role'] == 'capability_description' for f in facts)
    assert all(f['connection_role'] != 'device_uplink' for f in facts)


def test_qualified_medium_difference_has_both_sources_and_does_not_claim_live_state():
    facts = [
        fact('la', 'controller_link', '3G/4G网络', purpose='实现管理', ref=2),
        fact('cb', 'documented_physical_path', '同轴电缆', speech='diagnostic_instruction',
            status='not_observed', ref=4),
    ]
    result = compare_connections('device_uplink', ['la', 'cb'], facts)
    assert result['status'] == 'qualified_medium_difference'
    assert result['compared']['canonical_values'] == {'la': 'cellular_3g4g', 'cb': 'coaxial'}
    from app.knowledge.repository import fingerprint
    assert set(result['support_fact_ids']) == {fingerprint(facts[0]), fingerprint(facts[1])}
    answer = render_connection_comparison(result, {'la': 'LA2608', 'cb': 'CB304n'})
    assert '3G/4G' in answer and '同轴' in answer
    assert '现场链路已经建立' in answer
    assert '无线回程' not in answer


def test_unknown_medium_or_conflict_blocks_comparison():
    facts = [fact('p', 'controller_link', '专用链路'), fact('q', 'controller_link', '同轴')]
    assert compare_connections('device_uplink', ['p', 'q'], facts)['status'] == 'insufficient'
    facts = [fact('p', 'controller_link', '以太网'), fact('p', 'controller_link', '同轴'),
        fact('q', 'controller_link', '同轴')]
    result = compare_connections('device_uplink', ['p', 'q'], facts)
    assert result['status'] == 'conflict'
    assert result['conflicts']


def test_missing_product_is_explicit_and_renderer_has_no_internal_json():
    result = compare_connections('device_uplink', ['p', 'q'], [fact('p', 'controller_link', '以太网')])
    assert result['status'] == 'insufficient'
    answer = render_connection_comparison(result, {'p': '甲', 'q': '乙'})
    assert '缺少' in answer and 'connection_role' not in answer and 'fact_id' not in answer


@pytest.mark.parametrize('text', [
    '<script>LA2608通过3G/4G连接控制器</script>',
    '```txt\nLA2608通过3G/4G连接控制器\n```',
    '若启用功能，LA2608通过3G/4G连接控制器',
])
def test_unsafe_or_conditional_text_does_not_become_explicit_uplink(text):
    facts = derive_connection_facts([doc('p', text, '排障')], ['p'])
    assert all(f['connection_role'] in {'unknown', 'documented_physical_path'}
        for f in facts)
