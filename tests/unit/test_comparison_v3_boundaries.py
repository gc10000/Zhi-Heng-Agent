"""v3直接边界：资料归属不等于句中端口归属，未分类不等于原文未说明。"""
import pytest

from app.answering.comparison_answers import (
    bind_comparison_response, build_frame_catalog, derive_facts, compare_facts,
    render_comparison_answer,
)
from app.answering.evidence_attribution import payload
from app.knowledge.repository import fingerprint
from tests.unit.test_comparison_answers import _frozen_inputs, _fact


def bind(text):
    policy, doc, refs = _frozen_inputs(text)
    policy['comparison_answer']['function_version'] = 'comparison_answer_v3'
    catalog = build_frame_catalog(refs, [doc], policy)
    answer, proof = bind_comparison_response(
        '{"schema_version":"comparison_frame_selection_v1","frames":[]}',
        catalog, ['p', 'q'], 'device_uplink', fingerprint(payload(policy)), 'b'*64,
        {'p': '合成网关', 'q': '另一网关'}, version='comparison_answer_v3')
    facts = derive_facts(proof['rendered_frames'], catalog, ['p', 'q'],
        version='comparison_answer_v3')
    return answer, facts


@pytest.mark.parametrize('origin', ['其他设备LAN口', '电脑LAN口', '另一网关WAN口',
    '设备旁的交换机LAN口'])
def test_other_endpoint_in_own_document_is_not_current_product_documented_path(origin):
    text = f'请检查{origin}的网线是否插牢,网线另一端与入户接口是否连接正确。'
    answer, facts = bind(text)
    assert text in answer
    assert facts and all(f.get('documented_path') is None for f in facts)
    assert '这是资料描述的物理接线路径' not in answer


@pytest.mark.parametrize('origin', ['设备Cable口', '本设备的LAN口', '该设备WAN口', '合成网关LAN口'])
def test_unambiguous_own_port_preserves_documented_path(origin):
    text = f'请检查{origin}的网线是否插牢,网线另一端与入户接口是否连接正确。'
    answer, facts = bind(text)
    fact = next(f for f in facts if f.get('documented_path'))
    assert fact['documented_path']['origin'] == origin
    assert fact['operational_status'] == 'unknown'
    assert text in answer


@pytest.mark.parametrize('declaration', ['此路径承担设备上联。', '此路径已经建立。'])
def test_classifier_insufficiency_does_not_claim_source_has_no_uplink_declaration(declaration):
    text = (declaration + '请检查设备Cable口的同轴电缆是否插牢,'
        '同轴电缆另一端与入户接口是否连接正确。')
    _answer, facts = bind(text)
    management = _fact('q', 'management_link', '3G/4G网络', 2,
        '另一网关通过3G/4G网络连接到控制器用于管理。')
    management.update(origin='另一网关', destination='控制器', purpose='管理')
    result = compare_facts('device_uplink', ['p', 'q'], facts + [management],
        version='comparison_answer_v3')
    answer = render_comparison_answer(result, {'p': '合成网关', 'q': '另一网关'})
    assert text in answer
    assert '现有证据不足' in answer
    assert '资料未说明' not in answer
    assert '不能仅凭' in answer
