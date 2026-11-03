"""独立审查缺陷的实现回归：完整语境消费，不以装配成功替代答案消费。"""
from copy import deepcopy

import pytest

from app.answering.connection_semantics import derive_connection_facts, compare_connections, render_connection_comparison
from tests.unit.test_connection_semantics import doc
from tests.unit.test_connection_comparison_wiring import setup_connection, generate
from tests.unit.test_comparison_source_assembly import row
from app.knowledge.repository import fingerprint


STRONG = {'controller_link','explicit_uplink','documented_physical_path','capability_description'}


@pytest.mark.parametrize('framing', [
    '以下为错误示例。', '下面是假设场景。', '下列仅为配置示例。',
    '错误示例：', '以下是错误示例：',
])
def test_enclosing_nonassertive_scope_cannot_promote_following_sentence(framing):
    facts=derive_connection_facts([doc('p',framing+'\n本设备上联通过以太网连接到核心网。')],['p'])
    assert not [f for f in facts if f['connection_role'] in STRONG]


@pytest.mark.parametrize('limitation', ['该上联方式已废弃。','上述上联方式已经停用。'])
def test_noncurrent_relation_scope_cannot_promote_preceding_sentence(limitation):
    facts=derive_connection_facts([doc('p','本设备上联通过以太网连接到核心网。'+limitation)],['p'])
    assert not [f for f in facts if f['connection_role'] in STRONG]


@pytest.mark.parametrize('sentence', [
    '本设备上联通过以太网连接到核心网或通过光纤连接到备用核心网。',
    '本设备上联通过以太网连接到核心网并通过同轴连接到备用接口。',
    '本设备上联通过以太网连接到核心网或备用核心网。',
    '本设备上联通过以太网连接到核心网并提供无线回程。',
])
def test_endpoint_must_not_swallow_another_relation_or_alternative(sentence):
    facts=derive_connection_facts([doc('p',sentence)],['p'])
    assert not [f for f in facts if f['connection_role'] in STRONG]


@pytest.mark.parametrize('destination', [
    '入户接口或通过光纤连接的核心网', '入户接口或备用接口',
    '入户接口并提供无线回程',
])
def test_diagnostic_endpoint_is_one_object(destination):
    text=f'请确认设备Cable口的同轴电缆是否插牢，同轴电缆另一端与{destination}是否连接正确。'
    assert not derive_connection_facts([doc('p',text)],['p'])


@pytest.mark.parametrize('content_kind,ref_kind', [
    ('image_description','image_description'), ('image_description','pdf'),
    ('text','image_description'), ('text','image'), ('table','image_description'),
])
def test_nontext_source_cannot_supply_strong_connection_fact(content_kind,ref_kind):
    source=doc('p','本设备上联通过以太网连接到核心网。')
    source['metadata']['content_kind']=content_kind
    source['metadata']['source_refs'][0]['kind']=ref_kind
    assert not derive_connection_facts([source],['p'])


def test_nonassertive_heading_cannot_promote_body():
    source=doc('p','本设备上联通过以太网连接到核心网。',heading='错误示例')
    assert not derive_connection_facts([source],['p'])


def test_original_pdf_table_path_remains_comparable_but_code_stays_inert():
    text='请确认设备Cable口的同轴电缆是否插牢，同轴电缆另一端与入户接口是否连接正确。'
    source=doc('p',text)
    source['metadata']['content_kind']='table'
    facts=derive_connection_facts([source],['p'])
    assert len(facts)==1 and facts[0]['connection_role']=='documented_physical_path'
    other=derive_connection_facts([doc('q','本设备上联通过以太网连接到核心网。')],['q'])
    assert compare_connections('device_uplink',['p','q'],facts+other)['status']=='qualified_medium_difference'
    source['text']='```text\n'+text+'\n```'
    assert not derive_connection_facts([source],['p'])


@pytest.mark.parametrize('condition', [
    '该管理链路仅在安装指定专用SIM卡时可用。',
    '安装指定专用SIM卡后方可使用本管理链路。',
    '使用该方式前，务必安装指定专用SIM卡。',
])
def test_child_condition_is_consumed_and_bound_with_own_reference(monkeypatch,condition):
    runner,pool,plan=setup_connection()
    child=row('p-condition','p',3,['产品概述','适用限制'],condition)
    pool.append(child)
    policy=deepcopy(runner.evidence_attribution)
    policy['source_relations']['frozen_payloads'][child['chunk_uid']]=fingerprint(child)
    runner.evidence_attribution=policy
    runner.retrieval_policy={'context_limit':4}
    docs,groups,manifest=runner.assemble_connection_context([pool[0],pool[2]],pool,['p','q'])
    state,prompt=runner.evidence_prompt(plan.original_query,docs,groups,plan,
        item_names=['Atlas A17','Beacon B24'],history=[],session_id='condition',comparison_context=manifest)
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',lambda *a:None)
    generate(state,prompt)
    assert condition[:-1] in state['answer']
    assert state['comparison_answer']['comparison_status']=='qualified_medium_difference'
    contexts=state['comparison_answer']['result']['source_contexts']
    actual=next(c for c in contexts if c['source_chunk_uid']=='p-condition')
    assert actual['scope_text']==condition and actual['product_id']=='p'
    assert actual['context_sha256']==fingerprint(actual['scope_text'])
    assert '['+str(actual['reference_number'])+']' in state['answer']


def test_unclassified_limitation_in_same_scope_is_rendered_without_keyword_guess():
    text='本设备通过以太网连接到无线控制器，用于管理。安装专用SIM卡后方可使用此连接。'
    facts=derive_connection_facts([doc('p',text)],['p'])
    answer=render_connection_comparison(compare_connections('device_uplink',['p','q'],facts),{'p':'甲','q':'乙'})
    assert '安装专用SIM卡后方可使用此连接' in answer
