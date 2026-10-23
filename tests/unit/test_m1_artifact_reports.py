"""提交验证必须读取选定轮次的JUnit，不能偷偷沿用旧结果。"""
import json
import pytest
from scripts.verification import build_m1_artifacts as audit


@pytest.mark.parametrize('actual,expected,accepted', [(3, 3, True), (2, 3, False)])
def test_summary_selects_its_own_junit(tmp_path, monkeypatch, actual, expected, accepted):
    old = tmp_path / 'docs/development/evidence/M1-stage-final.xml'
    old.parent.mkdir(parents=True)
    old.write_text('<testsuites><testsuite tests="3" failures="0" errors="0" skipped="0"/></testsuites>')
    current = tmp_path / 'current.xml'
    current.write_text(f'<testsuites><testsuite tests="{actual}" failures="0" errors="0" skipped="0"/></testsuites>')
    summary = {'raw_evidence': [], 'stage': {'passed': expected, 'exit_code': 0, 'junit': 'current.xml'},
               'legacy_reimport': {'exit_code': 0}, 'live': {'exit_code': 0}, 'current_code_live_recheck': {'exit_code': 0}}
    summary_path = tmp_path / 'summary.json'
    summary_path.write_text(json.dumps(summary))
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    monkeypatch.setattr(audit, 'SUMMARY', summary_path)
    if accepted:
        assert audit.verify_results() == summary
    else:
        with pytest.raises(ValueError, match='测试数'):
            audit.verify_results()
