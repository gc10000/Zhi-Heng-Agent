"""新连接模式从装配、prompt、缓冲生成到恢复的实际单元接线。"""
from copy import deepcopy
from types import SimpleNamespace
import json

import pytest

from app.answering.comparison_answers import build_frame_catalog, validate_saved_comparison
from app.answering.comparison_context import validate_context_policy
from app.answering.evidence_attribution import payload
from app.answering.errors import AnswerGenerationError
from app.answering.service import AnswerBudget
from app.knowledge.repository import fingerprint
from app.retrieval.models import QueryPlan
from app.runs.query_runner import QueryRunner
from app.query_process.agent.nodes.node_answer_output import step_1_check_answer, step_3_generate_response
from tests.unit.test_comparison_source_assembly import row

RAW = '{"schema_version":"comparison_frame_selection_v1","frames":[]}'


def rebind_without_source(row, policy, uid):
    """冻结策略不改，协调删除来源并重签所有Run内的自证字段。"""
    from app.answering.comparison_answers import bind_comparison_response, prompt_used_identity
    from app.answering.evidence_attribution import evidence_labels
    before = len(row['prompt_used_docs'])
    row['prompt_used_docs'] = [d for d in row['prompt_used_docs'] if d['chunk_uid'] != uid]
    assert len(row['prompt_used_docs']) == before - 1
    row['citations'] = [c for c in row.get('citations', []) if c['chunk_uid'] != uid]
    row['prompt_reference_map'] = [dict(label, reference_number=i+1) for i, label in
        enumerate(evidence_labels(row['prompt_used_docs'], policy))]
    context = row['comparison_context_assembly']
    for key in ('documents', 'selected_chunk_uids', 'required_chunk_uids'):
        context[key] = [v for v in context[key] if v != uid]
    context['dependencies'] = [dict(dep, chunk_uids=[v for v in dep['chunk_uids'] if v != uid])
        for dep in context['dependencies'] if any(v != uid for v in dep['chunk_uids'])]
    context['identity_sha256'] = fingerprint({k:v for k,v in context.items() if k != 'identity_sha256'})
    question = ((row.get('query_plan') or {}).get('rewritten_query') or
        row.get('rewritten_query') or row.get('original_query') or row['question'])
    question += '\n\n证据限制：比较只能依据本轮参考内容，未提供某型号证据时必须明确资料不足，不得推断其参数。'
    row['comparison_prompt_used_sha256'] = prompt_used_identity(question,
        row['prompt_reference_map'], row['prompt_used_docs'], row['comparison_target'])
    row['answer'], row['comparison_answer'] = bind_comparison_response(RAW,
        build_frame_catalog(row['prompt_reference_map'],row['prompt_used_docs'],policy),
        row.get('comparison_product_ids') or row['product_snapshot']['product_ids'],
        row['comparison_target'],row['comparison_policy_sha256'],row['comparison_prompt_used_sha256'],
        policy['products'],version='connection_comparison_v1',comparison_context=context)
    assert row['comparison_answer']['comparison_status'] == 'qualified_medium_difference'


def setup_connection():
    pool = [row('pa','p',0,['产品概述'],'为了实现对设备的管理，本设备需要通过3G/4G网络连接到运营商无线控制器。\n目前只支持与某厂商无线控制器互通。'),
        row('qa','q',0,['产品简介'],'本设备融合了Cable网络和无线路由器的功能。'),
        row('qp','q',1,['排障'],'请确认设备Cable口的同轴电缆是否插牢，同轴电缆另一端与入户接口是否连接正确。'),
        row('header','q',2,['封面'],'封面')]
    policy = payload(dict(enabled=True, scope=dict(owner_id='o',kb_id='k',
        database='m1_test_m4_unit',collection='m1_test_m4_unit',
        product_ids=['p','q'],revisions={'d-p':'r-p','d-q':'r-q'}),
        corpus_snapshot_sha256='a'*64, documents=[dict(document_id='d-'+p,revision_id='r-'+p,
            original_sha256=('b' if p=='p' else 'c')*64) for p in ['p','q']],
        products={'p':'Atlas A17','q':'Beacon B24'},
        source_relations=dict(enabled=True,frozen_payloads={r['chunk_uid']:fingerprint(r) for r in pool}),
        comparison_answer=dict(enabled=True,function_version='connection_comparison_v1')))
    runner = object.__new__(QueryRunner)
    runner.answer_budget = AnswerBudget(context_window=32768, output_tokens=512, reserve_tokens=64)
    runner.evidence_attribution = policy
    runner.retrieval_policy = {'context_limit':3}
    plan = QueryPlan(original_query='比较Atlas A17与Beacon B24的上联方式', route='compare',
        product_ids=('p','q'),comparison_target='device_uplink',comparison_target_reason='explicit_single_target')
    return runner, pool, plan


def state_and_prompt():
    runner, pool, plan = setup_connection()
    docs, groups, manifest = runner.assemble_connection_context([pool[0], pool[2], pool[3]],pool,['p','q'])
    state, prompt = runner.evidence_prompt(plan.original_query,docs,groups,plan,
        item_names=['Atlas A17','Beacon B24'],history=[],session_id='synthetic',
        comparison_context=manifest)
    return runner, state, prompt


def generate(state, prompt, raw=RAW, *, interrupted=False, truncated=False):
    class Model:
        calls = 0
        def stream(self, *args, **kwargs):
            self.calls += 1
            yield SimpleNamespace(content=raw, response_metadata={'finish_reason':'length' if truncated else 'stop'})
            if interrupted:
                raise TimeoutError('合成断流')
    model = Model()
    step_3_generate_response(state,prompt,client=model)
    return model


def test_assembly_replaces_only_structural_header_and_never_reads_scoring_labels():
    _, state, prompt = state_and_prompt()
    assert [d['chunk_uid'] for d in state['prompt_used_docs']] == ['pa','qa','qp']
    assert '融合' in prompt and '同轴' in prompt
    assert len(state['prompt_reference_map']) == 3
    assert 'expected' not in prompt and 'allowed_evidence' not in prompt


def test_connection_answer_and_cached_push_recompute_all_sources(monkeypatch):
    sent=[]
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',lambda *args:sent.append(args))
    runner,state,prompt=state_and_prompt()
    assert generate(state,prompt).calls == 1
    assert state['comparison_answer']['comparison_status'] == 'qualified_medium_difference'
    assert '融合Cable网络和无线路由器' in state['answer']
    assert '目前只支持' in state['answer'] and '现场链路已经建立' in state['answer']
    assert len(sent)==1 and RAW not in str(sent)
    assert step_1_check_answer(state) is True
    assert len(sent)==2
    assert state['comparison_answer']['comparison_context']==state['comparison_context_assembly']
    validate_context_policy(state['comparison_context_assembly'],runner.evidence_attribution,max_docs=3,max_chars=12000)


def test_coordinated_source_deletion_cannot_push_cached_answer(monkeypatch):
    runner,state,prompt=state_and_prompt()
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',lambda *args:None)
    generate(state,prompt)
    rebind_without_source(state,runner.evidence_attribution,'qa')
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',
        lambda *args:pytest.fail('协调删来源后的缓存答案不得推送'))
    with pytest.raises(ValueError):
        step_1_check_answer(state)


def test_missing_input_guard_stops_before_model():
    _,state,prompt=state_and_prompt()
    del state['_connection_input_guard']
    with pytest.raises(ValueError,match='调用前输入核验器'):
        generate(state,prompt)


@pytest.mark.parametrize('cached',[False,True])
def test_comparison_mode_cannot_be_disabled_after_input_freeze(monkeypatch,cached):
    _,state,prompt=state_and_prompt()
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',lambda *args:None)
    if cached:
        generate(state,prompt)
    state['comparison_mode']=False
    with pytest.raises(ValueError):
        if cached:
            step_1_check_answer(state)
        else:
            generate(state,prompt)


@pytest.mark.parametrize('field', ['source_facts','result','facts_sha256','answer_sha256',
    'rendered_frames','raw_selection','classifier_version','comparison_context'])
def test_cached_proof_mutations_are_rejected_before_any_push(monkeypatch,field):
    _,state,prompt=state_and_prompt()
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',lambda *args:None)
    generate(state,prompt)
    changed=deepcopy(state)
    changed['comparison_answer'][field] = 'tampered'
    def no_push(*args): pytest.fail('篡改答案不得泄漏')
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',no_push)
    with pytest.raises((ValueError,TypeError)):
        step_1_check_answer(changed)


@pytest.mark.parametrize('raw,truncated', [('自由答案',False),
    ('{"schema_version":"comparison_frame_selection_v1","frames":[],"frames":[]}',False),
    ('{"schema_version":"comparison_frame_selection_v1","frames":[{"reference":99,"frame":0}]}',False),
    (RAW,True)])
def test_invalid_selection_stays_buffered_and_failure_is_saved(monkeypatch,raw,truncated):
    _,state,prompt=state_and_prompt()
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',
        lambda *args:pytest.fail('拒绝结果不得推送'))
    with pytest.raises(AnswerGenerationError):
        generate(state,prompt,raw,truncated=truncated)
    assert state['comparison_answer_failure']['raw_selection']==raw
    assert 'answer' not in state


def test_interruption_keeps_partial_selection_without_public_delta(monkeypatch):
    _,state,prompt=state_and_prompt()
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',
        lambda *args:pytest.fail('断流不得推送内部JSON'))
    with pytest.raises(AnswerGenerationError):
        generate(state,prompt,RAW[:20],interrupted=True)
    assert state['comparison_answer_failure']['raw_selection']==RAW[:20]


def test_missing_manifest_and_modified_source_fail_before_model_call():
    runner,pool,plan=setup_connection()
    docs,groups,_=runner.assemble_connection_context([pool[0],pool[2]],pool,['p','q'])
    with pytest.raises(ValueError):
        runner.evidence_prompt(plan.original_query,docs,groups,plan,
            item_names=['Atlas A17','Beacon B24'],history=[],session_id='synthetic')
    _,state,prompt=state_and_prompt()
    state['prompt_used_docs'][0]['text']='篡改资料'
    with pytest.raises(ValueError):
        generate(state,prompt)


def test_missing_or_oversize_required_source_fails_without_partial_documents():
    runner,pool,_=setup_connection()
    runner.retrieval_policy={'context_limit':2}
    with pytest.raises(Exception) as failure:
        runner.assemble_connection_context([pool[0],pool[2]],pool,['p','q'])
    assert failure.value.code=='required_source_budget_exceeded'


def test_old_version_proof_is_not_accepted_under_new_mode(monkeypatch):
    _,state,prompt=state_and_prompt()
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',lambda *args:None)
    generate(state,prompt)
    state['comparison_answer']['function_version']='comparison_answer_v3'
    with pytest.raises(ValueError):
        step_1_check_answer(state)


def test_singleton_header_group_is_structural_but_multi_member_group_remains_atomic():
    runner,pool,_=setup_connection()
    docs,groups,_=runner.assemble_connection_context([pool[0],pool[2],pool[3]],pool,['p','q'],[['header']])
    assert {d['chunk_uid'] for d in docs}=={'pa','qa','qp'}
    with pytest.raises(Exception) as failure:
        runner.assemble_connection_context([pool[0],pool[2],pool[3]],pool,['p','q'],[['qp','header']])
    assert failure.value.code=='required_source_budget_exceeded'


def test_source_changed_during_stream_is_rejected_before_public_answer(monkeypatch):
    _,state,prompt=state_and_prompt()
    monkeypatch.setattr('app.query_process.agent.nodes.node_answer_output.push_to_session',
        lambda *args:pytest.fail('生成期间来源漂移不能泄漏答案'))
    class Changed:
        def stream(self,*args,**kwargs):
            state['prompt_used_docs'][0]['text']='本设备上联通过以太网连接到核心网。'
            yield SimpleNamespace(content=RAW,response_metadata={'finish_reason':'stop'})
    with pytest.raises(AnswerGenerationError):
        step_3_generate_response(state,prompt,client=Changed())
    assert state['comparison_answer_failure']['raw_selection']==RAW
    assert 'answer' not in state


def test_nonadjacent_atomic_group_does_not_reorder_frozen_reference_numbers():
    runner,pool,plan=setup_connection()
    docs,groups,manifest=runner.assemble_connection_context([pool[0],pool[2]],pool,['p','q'],[['pa','qp']])
    state,prompt=runner.evidence_prompt(plan.original_query,docs,groups,plan,item_names=['Atlas A17','Beacon B24'],
        history=[],session_id='synthetic',comparison_context=manifest)
    assert [d['chunk_uid'] for d in state['prompt_used_docs']]==['pa','qa','qp']
    assert len(state['prompt_reference_map'])==3 and prompt
