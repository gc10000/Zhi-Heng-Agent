"""槽位事实与有界出口；测试不访问数据库或模型。"""
import pytest
from app.support.models import SupportInput
from app.support.workflow import initial, advance
from app.api.errors import APIError


def update(row, values=None, **kw):
    data = SupportInput(expected_version=row['version'], values=values or {}, **kw)
    result = advance(row, data, at='2026-10-25T00:00:00+00:00')
    result['version'] += 1
    return result


def test_one_required_slot_no_environment_or_error_code_forced():
    row = update(initial(), {'question': '通信失败'})
    assert row['requested_slot'] == 'device'
    row = update(row, {'device': 'AX-24'})
    assert row['requested_slot'] == 'symptom'
    row['citations'] = [{'citation_id': 'c'}]
    row = update(row, {'symptom': '指示灯熄灭'})
    assert row['state'] == 'ready'
    assert row['slots']['environment']['value'] is None


def test_missing_evidence_exit_without_fabricated_operation():
    row = update(initial(), {'question': '通信失败', 'device': 'AX-24', 'symptom': '无响应'})
    assert row['state'] == 'handoff' and row['reason'] == 'missing_evidence'
    assert row['operations'] == []


def test_unconfirmed_and_repeat_do_not_become_fact():
    row = initial()
    for _ in range(3):
        row = update(row, {'device': '可能型号'}, confirmed=False)
    assert row['state'] == 'handoff' and row['reason'] == 'no_progress'
    assert row['slots']['device']['source'] == 'unconfirmed'


@pytest.mark.parametrize('action,expected', [('cancel','cancelled'),('resolve','resolved'),('handoff','handoff')])
def test_explicit_user_exit_is_terminal(action, expected):
    row = update(initial(), action=action)
    assert row['state'] == expected
    with pytest.raises(APIError): update(row, {'question':'迟到输入'})


def test_correction_keeps_previous_snapshot_and_version():
    row = update(initial(), {'question': 'q', 'device': 'AX-24'})
    changed = update(row, {'device': 'AX-25'})
    assert changed['context_version'] == 2
    assert changed['history'][-1]['slots']['device']['value'] == 'AX-24'
    assert row['slots']['device']['value'] == 'AX-24'
    with pytest.raises(APIError) as error:
        advance(changed, SupportInput(expected_version=0, values={'device':'AX-26'}), at='now')
    assert error.value.status == 409


def test_explicit_clear_marks_confirmed_slot_unknown_and_records_previous_value():
    from app.support.models import SupportInput
    from app.support.workflow import advance
    row = initial()
    row['citations'] = [{'citation_id': 'old-citation'}]
    row = update(row, {'question': '通信失败', 'device': 'AX-24', 'symptom': '灯灭', 'environment': '室内'})
    row['evidence_slots'] = {key: dict(value) for key, value in row['slots'].items()}
    cleared = advance(row, SupportInput(expected_version=row['version'], clear_slots=['environment']), at='2026-10-25T00:01:00Z', user_id='operator')
    assert cleared['slots']['environment']['value'] is None
    assert cleared['slots']['environment']['confirmed'] is False
    assert cleared['slots']['environment']['source'] == 'unknown'
    assert cleared['history'][-1]['slots']['environment']['value'] == '室内'
    assert cleared['history'][-1]['withdrawal'] == {'slots':['environment'],'source':'user_request','user_id':'operator','recorded_at':'2026-10-25T00:01:00Z'}
    assert cleared['slots']['environment']['withdrawn_by'] == 'operator'
    assert cleared['context_version'] == row['context_version'] + 1
    assert cleared['needs_evidence'] is True
    assert cleared['state'] == 'awaiting_input' and cleared['reason'] == 'needs_fresh_evidence'


def test_clear_rejects_unconfirmed_duplicate_or_conflicting_slot_changes():
    from app.support.models import SupportInput
    from app.support.workflow import advance
    row = initial()
    for clear_slots, values in [(['device'], {}), (['device','device'], {}), (['device'], {'device':'AX-25'})]:
        with pytest.raises((APIError, ValueError)):
            advance(row, SupportInput(expected_version=0, clear_slots=clear_slots, values=values), at='now')


@pytest.mark.parametrize('value', ['', ' ', 'a'*4001])
def test_empty_or_oversized_slot_rejected(value):
    with pytest.raises(APIError) as error: update(initial(), {'question': value})
    assert error.value.status == 422
