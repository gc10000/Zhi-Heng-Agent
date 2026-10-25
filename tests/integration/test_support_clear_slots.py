"""已确认信息可显式撤回；历史快照不改写，未来运行不继承撤回事实。"""
from copy import deepcopy
import pytest
from app.runs.models import RunInput

pytestmark = pytest.mark.integration


def confirmed_support(client, headers, cid, rid):
    return client.post(f'/api/v1/conversations/{cid}/support', headers=headers, json={
        'expected_version': 0, 'run_id': rid,
        'values': {'device': 'AX-24', 'symptom': '通信失败', 'environment': '室内',
                   'error_code': 'E42', 'tried': '检查电源'},
    })


def test_optional_confirmed_values_can_be_withdrawn_without_rewriting_old_snapshots(support_client):
    client, headers, resources, user, cid, rid, citation = support_client
    url = f'/api/v1/conversations/{cid}/support'
    created = confirmed_support(client, headers, cid, rid)
    assert created.status_code == 200, created.text
    current = created.json()
    case_response = client.post('/api/v1/cases', headers=headers, json={
        'run_id': rid, 'expected_support_version': current['version']})
    assert case_response.status_code == 201, case_response.text
    case = case_response.json()
    case = client.post(f"/api/v1/cases/{case['case_id']}/confirm", headers=headers,
                       json={'expected_version': case['version']}).json()
    old_run = resources['runs'].prepare(user, cid, RunInput(question='旧环境问题', kb_id='k', client_request_id='old-facts'))
    old_snapshot = deepcopy(old_run['support_snapshot'])
    old_case_snapshot = deepcopy(resources['db'].support_cases.find_one({'case_id': case['case_id']})['context_snapshot'])

    cleared = client.post(url, headers=headers, json={'expected_version': current['version'],
        'clear_slots': ['environment', 'error_code', 'tried']})
    assert cleared.status_code == 200, cleared.text
    row = cleared.json()
    for name in ('environment', 'error_code', 'tried'):
        assert {key: row['slots'][name][key] for key in ('value', 'confirmed', 'source')} == {
            'value': None, 'confirmed': False, 'source': 'unknown'}
        assert row['slots'][name]['recorded_at']
        assert row['slots'][name]['withdrawn_by'] == user.user_id
    assert row['state'] == 'awaiting_input' and row['reason'] == 'needs_fresh_evidence'
    assert row['context_version'] == current['context_version'] + 1
    assert resources['runs'].get(user, old_run['run_id'])['support_snapshot'] == old_snapshot
    assert resources['db'].support_cases.find_one({'case_id': case['case_id']})['context_snapshot'] == old_case_snapshot
    saved_case = client.get(f"/api/v1/cases/{case['case_id']}")
    assert saved_case.status_code == 200
    assert saved_case.json()['status'] == 'confirmed'
    assert saved_case.json()['fields']['environment'] == '室内'

    fresh = resources['runs'].prepare(user, cid, RunInput(question='使用当前事实', kb_id='k', client_request_id='fresh-facts'))
    slots = fresh['support_snapshot']['slots']
    assert slots['environment']['value'] is None and not slots['environment']['confirmed']
    assert slots['error_code']['value'] is None and slots['tried']['value'] is None
    assert slots['device']['value'] == 'AX-24'
    from app.runs.query_runner import QueryRunner
    runner = QueryRunner.__new__(QueryRunner)
    runner._recent_messages = lambda _user, _run: []
    current_history = str(runner._history(user, fresh))
    old_history = str(runner._history(user, old_run))
    assert all(value not in current_history for value in ('室内', 'E42', '检查电源'))
    assert all(value in old_history for value in ('室内', 'E42', '检查电源'))
    assert resources['runs'].get(user, old_run['run_id'])['support_snapshot'] == old_snapshot


def test_withdrawing_required_device_requests_it_again_and_rejects_stale_version(support_client):
    client, headers, resources, user, cid, rid, citation = support_client
    url = f'/api/v1/conversations/{cid}/support'
    current = confirmed_support(client, headers, cid, rid).json()
    response = client.post(url, headers=headers, json={'expected_version': current['version'], 'clear_slots': ['device']})
    assert response.status_code == 200, response.text
    row = response.json()
    assert row['slots']['device']['value'] is None and row['slots']['device']['confirmed'] is False
    assert row['state'] == 'awaiting_input' and row['requested_slot'] == 'device'
    snapshot = deepcopy(row)
    stale = client.post(url, headers=headers, json={'expected_version': current['version'], 'clear_slots': ['device']})
    assert stale.status_code == 409
    assert resources['conversations'].get(user, cid)['support'] == snapshot


def test_clear_unknown_is_not_a_supported_slot(support_client):
    client, headers, resources, user, cid, rid, citation = support_client
    current = confirmed_support(client, headers, cid, rid).json()
    response = client.post(f'/api/v1/conversations/{cid}/support', headers=headers,
        json={'expected_version': current['version'], 'clear_slots': ['device','invented']})
    assert response.status_code == 422
    assert resources['conversations'].get(user, cid)['support'] == current
