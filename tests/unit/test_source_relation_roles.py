"""角色边界只用合成原句；有歧义则未知，不按产品名猜词界。"""
import pytest
from app.answering.source_relations import extract_frames


def field(frame, key):
    return (frame['fields'][key] or {}).get('text')


@pytest.mark.parametrize('marker', ['为', '向'])
def test_unambiguous_service_positive_stays_known(marker):
    text = f'终端甲{marker}用户提供无线服务。'
    frames = extract_frames(text)
    assert len(frames) == 1
    f = frames[0]
    assert (field(f, 'origin'), field(f, 'destination'), field(f, 'purpose')) == ('终端甲', '用户', '无线服务')
    assert f['direction'] == 'origin_to_destination'


@pytest.mark.parametrize('text', [
    '名为甲的终端向用户提供无线服务。',
    '字符为乙的网关向用户提供无线服务。',
    '设备向导为用户提供无线服务。',
    '厂为既不会就该程序向您提供支持。',
    '因此厂为不对该程序提供任何保证。',
    '厂为明确表示不对任何通过本产品提供的服务承担责任。',
    '终端甲为用户提供的服务仅限测试。',
    '终端甲通过链路连接到控制器的操作步骤类似。',
    '• 通过配件将计算机连接到显示设备的操作步骤类似。',
    '终端甲通过链路连接到控制器并向用户提供无线服务。',
    '终端甲向用户提供无线服务并通过链路连接到控制器。',
    '若终端甲通过链路连接到控制器则提供服务。',
])
def test_ambiguous_roles_are_unresolved_with_original_clause_and_scope(text):
    frames = extract_frames(text)
    assert frames
    for f in frames:
        assert f['direction'] == 'unknown'
        assert all(span is None for span in f['fields'].values())
        assert f['kind'] == 'unresolved'
        assert f['scope']['text'] == text
        assert text[f['clause']['start']:f['clause']['end']] == f['clause']['text']


def test_no_comma_coordination_is_not_split_by_guessing_or_subject_inheritance():
    text = '终端甲通过链路连接到控制器并向用户提供无线服务。'
    frames = extract_frames(text)
    assert len(frames) == 1 and frames[0]['kind'] == 'unresolved'
    assert '连接到控制器并向用户提供' in frames[0]['clause']['text']


def test_punctuated_clauses_keep_partial_roles_without_inheriting_subject():
    frames = extract_frames('终端甲通过链路连接到控制器，并向用户提供无线服务。')
    assert len(frames) == 2
    assert field(frames[0], 'origin') == '终端甲' and field(frames[0], 'destination') == '控制器'
    assert field(frames[1], 'origin') is None and field(frames[1], 'destination') == '用户'
    assert frames[1]['direction'] == 'unknown'


def test_management_purpose_and_full_condition_stay_attached_to_separate_roles():
    text = '终端甲向用户提供无线服务，为了实现设备管理，终端甲需要通过蜂窝网络连接到控制器。目前只支持控制器乙。'
    frames = extract_frames(text)
    assert len(frames) == 2
    assert (field(frames[0], 'destination'), field(frames[0], 'purpose')) == ('用户', '无线服务')
    assert (field(frames[1], 'destination'), field(frames[1], 'purpose')) == ('控制器', '实现设备管理')
    assert all(f['scope']['text'] == text for f in frames)
