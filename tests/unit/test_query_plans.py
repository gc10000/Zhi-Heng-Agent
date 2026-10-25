"""纯目录/上下文路由，不联网、不调用模型，不从候选补事实。"""
import copy
import pytest
from app.retrieval.query_planner import plan_query


@pytest.fixture
def directory():
    return [{'product_id': 'a', 'model': 'AX-24', 'aliases': ['甲型'], 'series': 'AX电源', 'brand': '安信'},
            {'product_id': 'b', 'model': 'AX-48', 'aliases': ['乙型'], 'series': 'AX电源', 'brand': '安信'}]


@pytest.mark.parametrize('question', ['ＡＸ－２４供电', 'ax24供电', '甲型供电', 'AX-24.'])
def test_normalized_exact_model_and_alias_skip_vector_candidates(directory, question):
    def forbidden(*args): pytest.fail('精确目录不应再调用向量')
    plan = plan_query(question, directory, candidate_search=forbidden)
    assert plan.product_ids == ('a',) and plan.route == 'answer'


@pytest.mark.parametrize('question', ['AX-42的供电', 'ＡＸ－４２的供电'])
def test_similar_model_remains_unconfirmed_even_with_high_vector_rank(directory, question):
    called = []
    def candidates(*args): called.append(True); return ['b', 'a']
    plan = plan_query(question, directory, selected_ids=['a'], candidate_search=candidates)
    assert called and plan.route == 'clarify' and not plan.product_ids
    assert plan.candidates == ('b', 'a') and plan.unconfirmed_tokens == ('AX-42',)
    assert 'device' not in plan.slots


def test_unknown_second_model_blocks_partial_comparison_assumption(directory):
    plan = plan_query('比较AX-24和AX-42供电', directory)
    assert plan.route == 'clarify' and 'device' not in plan.slots


def test_shared_alias_requires_clarification(directory):
    for p in directory: p['aliases'] = ['电源盒']
    plan = plan_query('电源盒供电', directory)
    assert plan.route == 'clarify' and set(plan.candidates) == {'a', 'b'}


def test_full_model_wins_over_embedded_short_model(directory):
    directory[1]['model'] = 'AX-24增强版'
    plan = plan_query('AX-24增强版如何供电', directory)
    assert plan.product_ids == ('b',)


def test_numeric_brand_is_series_scope_not_a_confirmed_model():
    products = [{'product_id': 'a', 'model': 'H3C LA2608', 'aliases': [], 'brand': 'H3C'}]
    plan = plan_query('H3C的设备有哪些接入方式', products)
    assert plan.route == 'series'


def test_series_general_and_comparison_have_distinct_scopes(directory):
    series = plan_query('AX电源系列供电', directory)
    general = plan_query('不限定型号，通用问题', directory, selected_ids=['a'])
    compare = plan_query('比较AX-24和AX-48供电', directory)
    assert series.route == 'series' and series.scope_groups == (('a', 'b'),)
    assert general.route == 'general' and general.product_ids == ()
    assert compare.route == 'compare' and compare.scope_groups == (('a',), ('b',))


def test_followup_rewrite_only_adds_confirmed_device_and_preserves_original(directory):
    history = [{'role': 'user', 'text': '我使用乙型', 'product_snapshot': {'product_ids': ['b'], 'version': 1}},
               {'role': 'assistant', 'text': '猜测在Ubuntu且电压220V。', 'product_snapshot': {'product_ids': ['b'], 'version': 1}}]
    before = copy.deepcopy(history)
    question = '它的供电是多少？'
    plan = plan_query(question, directory, messages=history)
    assert plan.original_query == question and plan.product_ids == ('b',)
    assert 'AX-48' in plan.search_queries[0]
    assert 'Ubuntu' not in plan.search_queries[0] and '220V' not in plan.search_queries[0]
    assert history == before


def test_conflicting_explicit_selection_and_pronoun_context_requires_confirmation(directory):
    plan = plan_query('它怎么接线', directory, selected_ids=['a'], requested_ids=['a'],
        messages=[{'role': 'assistant', 'text': '已确认', 'product_snapshot': {'product_ids': ['b']}}])
    assert plan.route == 'clarify' and set(plan.candidates) == {'a', 'b'}


def test_user_confirmation_resumes_unknown_name_without_repeating_clarification(directory):
    plan = plan_query('AX-42供电', directory, selected_ids=['b'], confirmed=True)
    assert plan.route == 'answer' and plan.product_ids == ('b',)


def test_protocol_number_not_mistaken_for_unknown_product(directory):
    plan = plan_query('IPv4和RS485配置', directory, selected_ids=['a'])
    assert plan.route == 'answer' and not plan.unconfirmed_tokens


def test_forged_selection_is_not_hidden_by_valid_model_in_question(directory):
    with pytest.raises(ValueError): plan_query('AX-24供电', directory, selected_ids=['other-kb'])


def test_cancelled_user_snapshot_does_not_replace_last_completed_model(directory):
    messages = [{'role': 'assistant', 'text': '已确认乙型', 'product_snapshot': {'product_ids': ['b']}},
                {'role': 'user', 'text': 'AX-42的参数？', 'product_snapshot': {'product_ids': ['a']}}]
    plan = plan_query('它如何供电', directory, selected_ids=['a'], messages=messages)
    assert plan.product_ids == ('b',)


def test_general_context_reset_does_not_resurrect_old_conversation_selection(directory):
    messages = [{'role': 'assistant', 'text': '甲型供电', 'product_snapshot': {'product_ids': ['a']}},
                {'role': 'user', 'text': '不限定型号的通用问题', 'product_snapshot': {'product_ids': ['a']}},
                {'role': 'assistant', 'text': '通用说明', 'product_snapshot': {'product_ids': [], 'context_route': 'general'}}]
    plan = plan_query('它具体如何供电', directory, selected_ids=['a'], messages=messages)
    assert plan.route == 'clarify' and not plan.product_ids


def test_explicit_context_reset_does_not_auto_select_single_catalog_model(directory):
    plan = plan_query('它具体如何供电', directory[:1], selected_ids=['a'], context_reset=True)
    assert plan.route == 'clarify' and plan.reason == 'model_required_after_context_reset'
    assert plan.product_ids == () and plan.candidates == ('a',)


def test_unknown_foreign_model_does_not_silently_reuse_old_device(directory):
    plan = plan_query('ZZ99如何供电', directory, selected_ids=['a'])
    assert plan.route == 'clarify' and not plan.product_ids


def test_error_code_looking_like_a_model_stays_an_observed_slot(directory):
    plan = plan_query('AX-24报错AX-42，如何排查', directory)
    assert plan.route == 'answer' and plan.product_ids == ('a',)
    assert plan.slots['error_code'] == 'AX-42'


def test_explicit_from_to_switch_uses_target_model_only(directory):
    plan = plan_query('从AX-24切换到AX-48，供电要求是什么', directory, selected_ids=['a'])
    assert plan.route == 'answer' and plan.product_ids == ('b',)


@pytest.mark.parametrize('question', ['设备型号：2609，如何供电', '型号不确定，如何供电'])
def test_explicit_unknown_model_intent_cannot_inherit_old_selection(directory, question):
    plan = plan_query(question, directory, selected_ids=['a'])
    assert plan.route == 'clarify' and not plan.product_ids


def test_operating_system_version_is_environment_not_a_second_device(directory):
    plan = plan_query('AX-24环境：Ubuntu22.04，现象：网卡失败', directory)
    assert plan.route == 'answer' and plan.slots['environment'] == 'Ubuntu22.04'


@pytest.mark.parametrize('interface',['Cellular-Ethernet2/0接口','GigabitEthernet1/0/1端口','Serial1/0接口','LoopBack0接口'])
def test_physical_interface_identifier_is_not_an_unconfirmed_device(directory,interface):
    result=plan_query('AX-24的'+interface+'无法获取IP地址',directory)
    assert result.route=='answer' and result.product_ids==('a',)
    assert not result.unconfirmed_tokens


def test_interface_rule_never_confirms_a_foreign_model_or_unknown_ax_device(directory):
    assert plan_query('型号Ethernet2/0接口的供电',directory,selected_ids=['a']).route=='clarify'
    assert plan_query('AX-42接口无法获取IP',directory,selected_ids=['a']).route=='clarify'
