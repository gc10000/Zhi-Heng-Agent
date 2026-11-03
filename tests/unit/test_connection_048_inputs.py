"""完整标量输入冻结必须拒绝投影、自证prompt及来源漂移。"""
from copy import deepcopy
import pytest
from app.api.errors import APIError


def case():
    from tests.unit.test_connection_comparison_wiring import setup_connection
    from app.answering.service import AnswerBudget
    runner,pool,plan=setup_connection()
    budget=AnswerBudget(context_window=32768,output_tokens=4096,reserve_tokens=256,max_chars=12000)
    cfg=dict(parameters=dict(evidence_attribution=runner.evidence_attribution,
        answer_budget=budget.model_dump(mode='json'),retrieval=dict(context_limit=10)))
    question=dict(id='support-v1-048',question=plan.original_query,product_names=['Atlas A17','Beacon B24'],history=[])
    query_plan=plan.model_dump(mode='json')|dict(comparison_target=plan.comparison_target,
        comparison_target_reason=plan.comparison_target_reason)
    inputs=dict(question=question,query_plan=query_plan,product_ids=list(plan.product_ids),
        seeds=[pool[0],pool[2]],groups=[],frozen_scalar_payloads=pool)
    return cfg,inputs


def test_freeze_uses_full_pool_and_real_prompt_consumer():
    from app.evaluation.connection_048_inputs import assemble_input,validate_input_anchor
    cfg,inputs=case();anchor=assemble_input(cfg,inputs)
    assert anchor['result']['prompt'] and anchor['result']['budget']['input_limit']==28416
    assert len(anchor['result']['context'])==3
    assert [r['reference_number'] for r in anchor['result']['prompt_reference_map']]==[1,2,3]
    assert anchor['full_scope_scalar_payloads_replayed'] is True
    assert validate_input_anchor(anchor)==anchor


@pytest.mark.parametrize('reverse_names', [False, True])
def test_frozen_prompt_uses_formal_question_product_order_instead_of_selected_order(reverse_names):
    """正式adapter按题目产品顺序建会话；检索后selected顺序可以相反。"""
    from app.evaluation.connection_048_inputs import assemble_input
    from app.runs.query_runner import QueryRunner
    from app.answering.service import AnswerBudget
    from app.retrieval.models import QueryPlan
    cfg, inputs = case()
    if reverse_names:
        inputs['question']['product_names'].reverse()
    anchor = assemble_input(cfg, inputs)
    runner = object.__new__(QueryRunner)
    runner.answer_budget = AnswerBudget.model_validate(cfg['parameters']['answer_budget'])
    runner.evidence_attribution = cfg['parameters']['evidence_attribution']
    runner.retrieval_policy = cfg['parameters']['retrieval']
    _, formal_prompt = runner.evidence_prompt(inputs['question']['question'], anchor['result']['context'],
        anchor['result']['groups'], QueryPlan.model_validate(inputs['query_plan']),
        item_names=inputs['question']['product_names'], history=[], session_id='formal-order',
        product_ids=inputs['product_ids'], comparison_context=anchor['result']['comparison_context_assembly'])
    assert anchor['result']['prompt'] == formal_prompt


@pytest.mark.parametrize('fault',['missing','extra','duplicate','body','seed','question','target','budget'])
def test_freeze_rejects_faults_before_a_prompt_can_be_frozen(fault):
    from app.evaluation.connection_048_inputs import assemble_input
    cfg,inputs=case()
    if fault=='missing':inputs['frozen_scalar_payloads'].pop()
    if fault=='extra':inputs['frozen_scalar_payloads'].append(dict(inputs['frozen_scalar_payloads'][0],chunk_uid='extra'))
    if fault=='duplicate':inputs['frozen_scalar_payloads'].append(deepcopy(inputs['frozen_scalar_payloads'][0]))
    if fault=='body':inputs['frozen_scalar_payloads'][0]['text']+='changed'
    if fault=='seed':inputs['seeds'][0]['metadata']['heading_path']=['changed']
    if fault=='question':inputs['question']['question']+='changed'
    if fault=='target':inputs['query_plan']['comparison_target']=None
    if fault=='budget':cfg['parameters']['answer_budget']['max_chars']=10
    with pytest.raises((ValueError,APIError)):assemble_input(cfg,inputs)


@pytest.mark.parametrize('fault',['prompt','context','groups','budget','assembly','pool'])
def test_frozen_anchor_is_recomputed_instead_of_trusting_its_own_hash(fault):
    from app.evaluation.connection_048_inputs import assemble_input,validate_input_anchor
    from app.knowledge.repository import fingerprint
    cfg,inputs=case();anchor=assemble_input(cfg,inputs)
    if fault=='prompt':anchor['result']['prompt']+='changed'
    if fault=='context':anchor['result']['context'].pop()
    if fault=='groups':anchor['result']['groups']=[]
    if fault=='budget':anchor['result']['budget']['input_tokens']=1
    if fault=='assembly':anchor['result']['comparison_context_assembly']['documents']=[]
    if fault=='pool':anchor['production_inputs']['frozen_scalar_payloads'].pop()
    anchor['result_sha256']=fingerprint(anchor['result'])
    with pytest.raises(ValueError):validate_input_anchor(anchor)


def test_scalar_reader_projects_no_vector_and_pins_each_revision():
    from app.evaluation.connection_048_inputs import read_scalar_pool,SCALAR_FIELDS
    cfg,inputs=case();pool=inputs['frozen_scalar_payloads']
    docs=[dict(document_id='d-'+p,revision_id='r-'+p) for p in ('p','q')]
    cfg.update(target=dict(owner_id='o',kb_id='k',collection='m1_test_m4_unit'),corpus=dict(snapshot=dict(documents=docs)))
    calls=[]
    class Client:
        def query(self,**kwargs):
            calls.append(kwargs)
            return [r for r in pool if r['document_id']==docs[len(calls)-1]['document_id']]
    assert len(read_scalar_pool(Client(),cfg))==4
    assert len(calls)==2
    for call,doc in zip(calls,docs):
        assert call['output_fields']==list(SCALAR_FIELDS) and call['consistency_level']=='Strong'
        assert 'vector' not in call['output_fields'] and call['limit']<=1000
        assert all(value in call['filter'] for value in doc.values())
