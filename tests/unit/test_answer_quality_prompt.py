"""提示输入应把证据范围与内部元数据区分开。"""
from app.answering.context_budget import pack_prompt_inputs, readable_evidence
from tests.unit.test_source_relations import render


def test_reviewed_object_is_presented_as_scope_not_internal_proof_metadata():
    label = dict(
        products=['合成产品'],
        product_status='snapshot',
        physical_pages=[3],
        page_status='exact',
        reviewed_subject=dict(
            subject='配件甲',
            kind='reviewed_accessory_table_member',
            proof_payload_sha256='a' * 64,
        ),
    )
    context = pack_prompt_inputs(
        [dict(chunk_id='synthetic', title='接口说明', text='配件甲具有 HDMI 接口。')],
        [],
        attributions=[label],
    )['context']

    assert '已核验对象范围=配件甲' in context
    assert 'reviewed_accessory_table_member' not in context
    assert 'proof_payload_sha256' not in context
    assert 'a' * 64 not in context


def test_system_added_icon_annotation_is_not_mistaken_for_source_text():
    rendered = readable_evidence('依次点击 > > 打开设置。')

    assert '系统标注' in rendered
    assert '非原文' in rendered
    assert '未识别图标路径' in rendered


def test_answer_prompt_exposes_direct_evidence_rules_without_internal_contract_labels():
    prompt, _, _ = render(
        '通过配件甲连接显示设备，下文以配件甲为例。HDMI 与 VGA 不能同时使用。'
    )

    assert 'attributed_assertions_v1' not in prompt
    assert 'source_relation_spans_v1' not in prompt
    assert '合同' not in prompt
    assert '内部规则不是产品事实或资料来源' in prompt
    assert '只在原文明确的对象、条件和范围内陈述限制' in prompt
    assert '不得把一个配件的能力或限制扩展到机身或其他配件' in prompt
    assert '保留原文的数量和限定词' in prompt
    assert '按原文顺序完整回答步骤' in prompt
