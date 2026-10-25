"""整段引用、去重和真实报告时间边界。"""
from copy import deepcopy
import pytest
from app.support.checklist import build_checklist, record_result
from app.support.models import OperationReport
from app.support.workflow import initial
from app.api.errors import APIError


def sample():
    return {'run_id': 'r', 'conversation_id': 'c', 'citations': [{'citation_id': 'cite', 'document_id': 'd',
        'revision_id': 'v', 'chunk_uid': 'chunk', 'text': '断电后检查接线。风险：禁止带电操作。', 'source_refs': [{'line_start': 3}]}]}


def test_excerpt_preserves_full_prerequisites_citation_and_unknown_execution():
    run = sample()
    row = build_checklist(initial(), run)
    step = row['operations'][0]
    assert step['suggestion'] == step['prerequisites'] == run['citations'][0]['text']
    assert step['citations'] == run['citations'] and step['reports'] == []
    assert step['status'] == 'not_tried'
    run['citations'][0]['text'] = 'changed'
    assert step['citations'][0]['text'] != 'changed'


def test_invalid_plain_facts_do_not_create_fabricated_instructions():
    run = sample()
    for text in ['额定输入24V。', '', '检查' * 4000]:
        run['citations'][0]['text'] = text
        assert build_checklist(initial(), run)['operations'] == []


def test_duplicate_evidence_new_run_does_not_repeat_ineffective_step():
    row = build_checklist(initial(), sample())
    oid = row['operations'][0]['operation_id']
    row = record_result(row, oid, OperationReport(expected_version=0,status='ineffective',note='已尝试无效'), at='2026-10-25T01:00:00Z',user_id='u')
    result = build_checklist(row, sample() | {'run_id': 'next'})
    assert len(result['operations']) == 1
    assert result['operations'][0]['reports'][0] == {'status':'ineffective','note':'已尝试无效',
        'recorded_at':'2026-10-25T01:00:00Z','source':'user_report','user_id':'u'}


def test_result_correction_appends_does_not_replace_history():
    row = build_checklist(initial(), sample())
    oid = row['operations'][0]['operation_id']
    for state, at in [('ineffective','first'),('not_tried','second')]:
        row = record_result(row, oid, OperationReport(expected_version=0,status=state,note='用户更正'),at=at,user_id='u')
    assert [r['recorded_at'] for r in row['operations'][0]['reports']] == ['first','second']
    assert row['operations'][0]['status'] == 'not_tried'


def test_unknown_operation_and_empty_observation_rejected():
    row = build_checklist(initial(), sample())
    for oid, note in [('foreign','x'),(row['operations'][0]['operation_id'],' ')]:
        before = deepcopy(row)
        with pytest.raises(APIError):
            record_result(row,oid,OperationReport(expected_version=0,status='tried',note=note),at='now',user_id='u')
        assert row == before
