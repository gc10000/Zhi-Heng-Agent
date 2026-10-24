"""提交检查不能信任摘要中写死的通过状态或旧轮测试数量。"""
import hashlib
import json
import pytest
from scripts.verification.build_m4_artifacts import verify_summary


@pytest.fixture
def summary_case(tmp_path):
    junit = tmp_path / 'current.xml'
    junit.write_text('<testsuites><testsuite tests="2" failures="0" errors="0" skipped="0">'
        '<testcase classname="tests.unit.a"/><testcase classname="tests.contract.b"/>'
        '</testsuite></testsuites>', encoding='utf-8')
    live = tmp_path / 'live.json'
    live.write_text(json.dumps({'passed': True, 'selected_dev': 2, 'heldout_executed': 0}), encoding='utf-8')
    summary = {'tests': [{'junit': 'current.xml', 'passed': 2, 'exit_code': 0}],
        'real_baseline': {'report': 'live.json'},
        'raw_evidence': [{'path': 'current.xml', 'sha256': hashlib.sha256(junit.read_bytes()).hexdigest()},
                         {'path': 'live.json', 'sha256': hashlib.sha256(live.read_bytes()).hexdigest()}]}
    path = tmp_path / 'current-summary.json'
    path.write_text(json.dumps(summary), encoding='utf-8')
    return path, summary


def test_selected_current_summary_is_read_and_counts_come_from_junit(summary_case):
    path, summary = summary_case
    assert verify_summary(path, root=path.parent) == summary


@pytest.mark.parametrize('change', ['count', 'exit', 'raw', 'baseline', 'missing_hash'])
def test_invalid_current_report_not_hidden_by_other_passing_summary(summary_case, change):
    path, summary = summary_case
    (path.parent / 'old-summary.json').write_text(path.read_text('utf-8'), encoding='utf-8')
    if change == 'count': summary['tests'][0]['passed'] = 999
    elif change == 'exit': summary['tests'][0]['exit_code'] = 1
    elif change == 'raw': (path.parent / 'current.xml').write_text('changed', encoding='utf-8')
    elif change == 'baseline':
        live = path.parent / 'live.json'; live.write_text('{"passed": false}', encoding='utf-8')
        summary['raw_evidence'][1]['sha256'] = hashlib.sha256(live.read_bytes()).hexdigest()
    elif change == 'missing_hash': summary['raw_evidence'] = summary['raw_evidence'][:1]
    path.write_text(json.dumps(summary), encoding='utf-8')
    with pytest.raises(ValueError): verify_summary(path, root=path.parent)
