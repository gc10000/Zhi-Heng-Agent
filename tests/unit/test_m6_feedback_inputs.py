"""生产输入重算必须消费真实标量，而非信任可自签的prompt。"""
import copy
import pytest


def test_scalar_pool_rejects_missing_duplicate_or_changed_source():
    from app.evaluation.m6_feedback_inputs import validate_scalar_pool
    from tests.unit.test_comparison_source_assembly import row
    from app.knowledge.repository import fingerprint
    rows = [row('a', 'AX', 0, ['简介'], '资料正文')]
    scope = dict(owner_id='o', kb_id='k', revisions={'d-AX': 'r-AX'}, product_ids=['AX'])
    frozen = {r['chunk_uid']: fingerprint(r) for r in rows}
    config = {'parameters': {'evidence_attribution': {'scope': scope,
        'source_relations': {'frozen_payloads': frozen}}}}
    assert validate_scalar_pool(config, rows) == rows
    for bad in ([], rows + rows, [rows[0] | {'text': '篡改正文'}]):
        with pytest.raises(ValueError):
            validate_scalar_pool(config, bad)


def test_production_input_replay_rejects_a_self_consistent_forged_prompt(monkeypatch):
    from app.evaluation import m6_feedback_inputs as inputs
    expected = {'prompt': '正式消费者产出的prompt', 'context': [], 'groups': [],
        'budget': {'input_tokens': 24, 'input_limit': 28416}, 'prompt_reference_map': []}
    monkeypatch.setattr(inputs, 'assemble_member', lambda *args: copy.deepcopy(expected))
    monkeypatch.setattr(inputs, 'validate_input_plan', lambda *args: None, raising=False)
    entry = {'question': {'id': 'q'}, 'production_input': {'inputs': {}, 'result': copy.deepcopy(expected)}}
    inputs.validate_member({}, [], entry)
    entry['production_input']['result']['prompt'] = '伪造prompt'
    with pytest.raises(ValueError):
        inputs.validate_member({}, [], entry)


def test_member_route_and_product_plan_must_follow_the_original_question():
    from app.evaluation.m6_feedback_inputs import validate_input_plan
    from app.retrieval.query_planner import plan_query, serialize_query_plan
    products = [dict(product_id='p', model='AX100', aliases=[], series='AX')]
    question = dict(id='q', question='AX100如何连接？', product_names=['AX100'], history=[])
    config = dict(corpus=dict(snapshot=dict(products=products)),
        parameters=dict(evidence_attribution=dict(scope=dict(revisions={'d':'r'}))))
    plan = plan_query(question['question'], products, requested_ids=['p']).model_copy(update={'revision_ids':('r',)})
    entry = dict(member=dict(question_id='q',route='answer'),question=question,
        production_input=dict(inputs=dict(question=question,product_ids=['p'],
            query_plan=serialize_query_plan(plan,include_comparison=True))))
    validate_input_plan(config, entry)
    for section, key, value in [('query_plan','route','series'),('query_plan','product_ids',[]),
            ('query_plan','revision_ids',['other']),('inputs','product_ids',[])]:
        bad = copy.deepcopy(entry)
        target = bad['production_input']['inputs']
        (target if section=='inputs' else target[section])[key]=value
        with pytest.raises(ValueError):
            validate_input_plan(config,bad)
