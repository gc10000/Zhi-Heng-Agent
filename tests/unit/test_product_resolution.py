import copy
import pytest


def align(extracted, matches):
    from app.query_process.agent.nodes.node_item_name_confirm import step_5_align_item_names
    return step_5_align_item_names([{'extracted_name': extracted, 'matches': matches}])


def test_nearby_high_scores_require_product_clarification():
    result = align('M3070', [{'item_name': 'M3070DHF', 'score': .91}, {'item_name': 'M3070DXF', 'score': .90}])
    assert result == {'confirmed_item_names': [], 'options': ['M3070DHF', 'M3070DXF']}


@pytest.mark.parametrize('scores', [(.91, .90), (.7, .95)])
def test_exact_name_can_be_confirmed(scores):
    result = align('M3070DHF', [{'item_name': 'M3070DHF', 'score': scores[0]}, {'item_name': 'M3070DXF', 'score': scores[1]}])
    assert result == {'confirmed_item_names': ['M3070DHF'], 'options': []}


def test_low_empty_and_middle_scores():
    assert align('M', []) == {'confirmed_item_names': [], 'options': []}
    assert align('M', [{'item_name': 'M1', 'score': .59}]) == {'confirmed_item_names': [], 'options': []}
    assert align('M', [{'item_name': 'M1', 'score': .6}])['options'] == ['M1']
    assert align('M', [{'item_name': 'M1', 'score': .86}])['confirmed_item_names'] == ['M1']


def test_duplicate_hits_and_no_input_mutation():
    matches = [{'item_name': 'M1', 'score': .90}, {'item_name': 'M1', 'score': .91}]
    before = copy.deepcopy(matches)
    assert align('M', matches) == {'confirmed_item_names': ['M1'], 'options': []}
    assert matches == before


def test_ambiguous_result_propagates_to_clarification(monkeypatch):
    from app.query_process.agent.nodes import node_item_name_confirm as node
    result = align('M3070', [{'item_name': 'M3070DHF', 'score': .91}, {'item_name': 'M3070DXF', 'score': .90}])
    state = node.step_6_check_confirmation({}, result, 's', [], '')
    assert state['item_names'] == []
    assert 'M3070DHF' in state['answer'] and 'M3070DXF' in state['answer']


def test_one_confirmed_product_does_not_hide_another_ambiguity(monkeypatch):
    from app.query_process.agent.nodes import node_item_name_confirm as node
    monkeypatch.setattr(node, 'update_message_item_names', lambda *a: pytest.fail('澄清前不能更新历史主体'))
    result = {'confirmed_item_names': ['已知型号'], 'options': ['候选A', '候选B']}
    state = node.step_6_check_confirmation({}, result, 's', [{'_id': 'id'}], '')
    assert state['item_names'] == []
    assert '候选A' in state['answer'] and '候选B' in state['answer']
