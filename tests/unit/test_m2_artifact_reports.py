"""复审必须核对显式选择的本轮报告，拒绝旧结果掩盖当前失败。"""
import json
import pytest
from scripts.verification import build_m2_artifacts as audit


@pytest.mark.parametrize('current_passed', [True, False])
def test_selected_reports_override_historical_paths(tmp_path, monkeypatch, current_passed):
    from app.main import create_app
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    monkeypatch.setattr(audit, 'SUMMARY', tmp_path / 'summary.json')
    evidence = tmp_path / 'docs/development/evidence'
    evidence.mkdir(parents=True)
    # 历史报告与当前报告结论相反，确保不能误用旧文件。
    (evidence / 'M2-live-api-first.json').write_text(json.dumps({'passed': not current_passed, 'checks': {'selected': not current_passed}}))
    (evidence / 'M2-legacy-reimport-v2.txt').write_text('Ran 99 tests; FAILED')
    (tmp_path / 'selected-live.json').write_text(json.dumps({'passed': current_passed, 'checks': {'selected': current_passed}}))
    (tmp_path / 'selected-legacy.txt').write_text('Ran 1 tests; OK')
    (tmp_path / 'stage.xml').write_text('<testsuites><testsuite tests="1" errors="0" failures="0" skipped="0"><testcase classname="tests.unit.current"/></testsuite></testsuites>')
    architecture = tmp_path / 'docs/architecture'
    architecture.mkdir(parents=True)
    (architecture / 'openapi-v1.json').write_text(json.dumps(create_app().openapi()))
    summary = {'raw_evidence': [], 'stage': {'junit': 'stage.xml', 'passed': 1, 'test_directory_counts': {'unit': 1}, 'exit_code': 0},
               'live_api': {'report': 'selected-live.json', 'checks': {'selected': True}, 'exit_code': 0},
               'legacy_reimport': {'report': 'selected-legacy.txt', 'passed': 1, 'exit_code': 0}}
    audit.SUMMARY.write_text(json.dumps(summary))
    if current_passed:
        assert audit.verify_results() == summary
    else:
        with pytest.raises(ValueError, match='真实API'):
            audit.verify_results()
