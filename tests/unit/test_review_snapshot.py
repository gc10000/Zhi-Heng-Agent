"""验证新实测证据会覆盖旧状态推断；仅使用临时 JSON 与清单，不访问真实服务。"""
import hashlib
import json

import pytest


def make_inputs(tmp_path, count, cold_ok):
    def write(rel, value):
        path = tmp_path / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value if isinstance(value, str) else json.dumps(value), encoding='utf-8')
    write('docs/plans/DEVELOPMENT_TODO.md', '\n'.join(f'- [x] **M0-0{i}**' for i in range(1, 10)))
    write('docs/development/REVIEW_STATUS.md', '| M0 | 待审查 |')
    write('current-tests.txt', f'{count} passed in 1.0s')
    write('validation.json', {'runs': [{'exit_code': 0, 'passed': count, 'evidence': 'current-tests.txt',
                                       'evidence_sha256': hashlib.sha256((tmp_path / 'current-tests.txt').read_bytes()).hexdigest()}]})
    report = {'source_document': '合成来源', 'source_chunk_ids': ['1'], 'source_hashes': {'1': 'hash'},
              'scope': {}, 'objects': [], 'models': {}, 'prompt_sha256': {},
              'prewarm_reranker': False,
              'questions': [{'kind': kind, 'question': kind, 'status': 'completed', 'elapsed_seconds': 1,
                             'checks': {'ok': True}, 'image_count': 1} for kind in ('known', 'followup', 'image')],
              'image_verification': {'checks': {'expected_topology_in_body': True, 'expected_topology_in_final': True,
                                                'downloads_verified': True}}}
    write('selected-live.json', report)
    write('cold.json', {'status': 'passed', 'process_exit_code': 0, 'normal_configuration': True,
                        'prewarm_reranker': not cold_ok, 'thread_overrides': {}, 'assistant_saved_count': 1})
    spec = {'revision': 'synthetic', 'record_date': '2026-10-23', 'live_report': 'selected-live.json',
            'validation_report': 'validation.json', 'cold_start_report': 'cold.json',
            'image_expectation': 'expectation.json', 'limitations': [], 'evidence': [], 'submission': 'submission.md'}
    return spec


@pytest.mark.parametrize('count', [17, 123])
def test_snapshot_uses_selected_new_report_and_actual_counts(tmp_path, count):
    from scripts.verification.build_m0_review_artifacts import make_manifest
    spec = make_inputs(tmp_path, count, True)
    result = make_manifest(spec, tmp_path)
    assert result['tests'][0]['passed'] == count
    assert result['status'] == '已验收'
    assert result['evidence_complete']
    assert result['selected_live_report'] == 'selected-live.json'


def test_prewarmed_probe_cannot_count_as_normal_cold_start(tmp_path):
    from scripts.verification.build_m0_review_artifacts import make_manifest
    spec = make_inputs(tmp_path, 17, False)
    result = make_manifest(spec, tmp_path)
    assert not result['cold_start_verified']
    assert not result['evidence_complete']
    assert result['status'] == '未完成'


def test_changed_test_output_cannot_reuse_stale_summary(tmp_path):
    from scripts.verification.build_m0_review_artifacts import make_manifest
    spec = make_inputs(tmp_path, 17, True)
    (tmp_path / 'current-tests.txt').write_text('failed', encoding='utf-8')
    with pytest.raises(AssertionError, match='哈希'):
        make_manifest(spec, tmp_path)
