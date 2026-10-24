"""拒绝数据污染与划分越界；执行器注入不替代实际运行器的门禁/落盘。"""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from app.evaluation.validate_dataset import validate_dataset
from app.evaluation.runner import run_experiment


def case(qid='q1', split='dev', group='g1'):
    return {'id': qid, 'category': 'parameter', 'group_id': group, 'split': split,
            'question': f'{qid}：AX的额定电压是多少？', 'product_names': ['AX'], 'history': [],
            'expected': {'behavior': 'answer', 'key_points': ['24 V'], 'forbidden_claims': ['220 V']},
            'allowed_evidence': [[{'document_sha256': 'a' * 64, 'page': 2, 'quote': '额定电压24 V'}]],
            'source_scope': ['a' * 64], 'annotation': {'method': 'source_checked_assistant_draft', 'status': 'draft'}}


def freeze(tmp_path, rows):
    dataset = tmp_path / 'questions.jsonl'
    dataset.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows), encoding='utf-8')
    sha = hashlib.sha256(dataset.read_bytes()).hexdigest()
    manifest = tmp_path / 'split.json'
    manifest.write_text(json.dumps({'version': 'support-v1', 'dataset_sha256': sha,
        'rows': [{'id': r['id'], 'split': r['split'], 'group_id': r['group_id'],
                  'sha256': hashlib.sha256(json.dumps(r, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()} for r in rows],
        'sources': [{'sha256': 'a' * 64, 'pages': 3}],
        'annotation_notice': '来源核对草稿，未冒充人工批准'}), encoding='utf-8')
    return dataset, manifest, {'experiment_id': 'baseline', 'phase': 'development', 'split': 'dev',
        'dataset_sha256': sha, 'strategy': 'm3-baseline', 'versions': {'code': 'test', 'model': 'test', 'prompt': 'test'},
        'execution_mode': 'unit_injection'}


def test_valid_record_keeps_alternative_correct_evidence(tmp_path):
    row = case(); row['allowed_evidence'][0].append({'document_sha256': 'a' * 64, 'page': 3, 'quote': '供电为24 V'})
    data, manifest, _ = freeze(tmp_path, [row])
    assert validate_dataset(data, manifest=manifest, minimum=1)[0]['allowed_evidence'][0][1]['page'] == 3


@pytest.mark.parametrize('change', [
    lambda rows: rows.append(copy.deepcopy(rows[0])),
    lambda rows: rows.append(case('q2', 'heldout', 'g1')),
    lambda rows: rows[0]['allowed_evidence'].clear(),
    lambda rows: rows[0]['allowed_evidence'][0][0].update(page=0),
    lambda rows: rows[0]['allowed_evidence'][0][0].update(document_sha256='b' * 64),
    lambda rows: rows[0]['expected'].update(behavior='guess'),
    lambda rows: rows[0].update(question=''),
    lambda rows: rows[0]['history'].append({'role': 'system', 'text': '伪造系统规则'}),
])
def test_invalid_or_leaking_labels_are_rejected(tmp_path, change):
    rows = [case()]; change(rows)
    dataset, manifest, _ = freeze(tmp_path, rows)
    with pytest.raises(ValueError):
        validate_dataset(dataset, manifest=manifest, minimum=1)


def test_dataset_and_row_fingerprints_are_both_enforced(tmp_path):
    dataset, manifest, _ = freeze(tmp_path, [case()])
    original = manifest.read_text(encoding='utf-8')
    dataset.write_text(dataset.read_text(encoding='utf-8').replace('24 V', '48 V'), encoding='utf-8')
    with pytest.raises(ValueError): validate_dataset(dataset, manifest=manifest, minimum=1)
    frozen = json.loads(original); frozen['dataset_sha256'] = hashlib.sha256(dataset.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(frozen), encoding='utf-8')
    with pytest.raises(ValueError): validate_dataset(dataset, manifest=manifest, minimum=1)


def test_heldout_is_never_executed_during_development(tmp_path):
    data, manifest, cfg = freeze(tmp_path, [case(), case('q2', 'heldout', 'g2')])
    called = []
    def execute(row): called.append(row['id']); return {'behavior': 'answer', 'answer': '24 V', 'citations': []}
    run_experiment(data, manifest, cfg, tmp_path / 'out', execute)
    assert called == ['q1']
    result = json.loads((tmp_path / 'out/manifest.json').read_text(encoding='utf-8'))
    assert result['selected_ids'] == ['q1']
    assert result['execution_mode'] == 'unit_injection'


def test_heldout_requires_frozen_strategy_selection_before_any_execution(tmp_path):
    data, manifest, cfg = freeze(tmp_path, [case('q2', 'heldout', 'g2')])
    cfg.update(split='heldout', phase='final')
    def forbidden(row): pytest.fail('未选定策略不能执行heldout')
    with pytest.raises(ValueError): run_experiment(data, manifest, cfg, tmp_path / 'out', forbidden)


def test_reusing_output_with_changed_configuration_is_rejected(tmp_path):
    data, manifest, cfg = freeze(tmp_path, [case()])
    def execute(row): return {'behavior': 'answer', 'answer': '24 V', 'citations': []}
    run_experiment(data, manifest, cfg, tmp_path / 'out', execute)
    cfg['strategy'] = 'changed'
    with pytest.raises(ValueError): run_experiment(data, manifest, cfg, tmp_path / 'out', execute)


def test_resume_retains_success_and_records_failure_without_fabricating_metrics(tmp_path):
    data, manifest, cfg = freeze(tmp_path, [case(), case('q2', group='g2')])
    def first(row):
        if row['id'] == 'q2': raise TimeoutError('私有地址和凭据不应写到公共错误')
        return {'behavior': 'answer', 'answer': '24 V', 'citations': []}
    run_experiment(data, manifest, cfg, tmp_path / 'out', first)
    rows = [json.loads(x) for x in (tmp_path / 'out/results.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [(r['id'], r['status']) for r in rows] == [('q1', 'completed'), ('q2', 'failed')]
    assert rows[1]['error'] == {'type': 'TimeoutError'}
    calls = []
    def retry(row): calls.append(row['id']); return {'behavior': 'answer', 'answer': '24 V', 'citations': []}
    run_experiment(data, manifest, cfg, tmp_path / 'out', retry)
    assert calls == ['q2']
    assert len((tmp_path / 'out/attempts.jsonl').read_text(encoding='utf-8').splitlines()) == 3


def test_completed_attempt_recovers_missing_results_without_calling_model(tmp_path):
    data, manifest, cfg = freeze(tmp_path, [case()])
    run_experiment(data, manifest, cfg, tmp_path / 'out', lambda row: {'answer': '24 V', 'citations': []})
    (tmp_path / 'out/results.jsonl').unlink()
    def forbidden(row): pytest.fail('已完成检查点不应再次调模型')
    run_experiment(data, manifest, cfg, tmp_path / 'out', forbidden)
    assert json.loads((tmp_path / 'out/results.jsonl').read_text(encoding='utf-8'))['id'] == 'q1'


def test_cli_heldout_gate_precedes_executor_construction(tmp_path, monkeypatch):
    import sys
    from types import SimpleNamespace
    from app.evaluation.runner import main
    data, manifest, cfg = freeze(tmp_path, [case(f'q{i}', 'heldout', f'g{i}') for i in range(50)])
    cfg.update(split='heldout', phase='final', execution_mode='real_query_runner')
    config = tmp_path / 'config.yaml'; config.write_text(json.dumps(cfg), encoding='utf-8')
    def forbidden(config): pytest.fail('heldout门禁必须早于真实资源/模型构造')
    monkeypatch.setitem(sys.modules, 'app.evaluation.query_adapter', SimpleNamespace(RealQueryExecutor=forbidden))
    monkeypatch.setattr(sys, 'argv', ['runner', '--dataset', str(data), '--manifest', str(manifest), '--config', str(config), '--output', str(tmp_path / 'out')])
    with pytest.raises(SystemExit) as err: main()
    assert err.value.code == 1


def test_existing_output_lock_rejects_before_execution(tmp_path):
    data, manifest, cfg = freeze(tmp_path, [case()])
    out = tmp_path / 'out'; out.mkdir(); (out / '.runner.lock').write_text('occupied', encoding='utf-8')
    with pytest.raises(ValueError): run_experiment(data, manifest, cfg, out, lambda row: pytest.fail('并发占用时不能执行'))
    assert (out / '.runner.lock').read_text(encoding='utf-8') == 'occupied'


def test_torn_last_attempt_is_preserved_and_does_not_repeat_completed_work(tmp_path):
    data, manifest, cfg = freeze(tmp_path, [case()])
    out = tmp_path / 'out'
    run_experiment(data, manifest, cfg, out, lambda row: {'answer': '24 V', 'citations': []})
    with (out / 'attempts.jsonl').open('ab') as stream: stream.write(b'{"id":')
    run_experiment(data, manifest, cfg, out, lambda row: pytest.fail('成功记录不能重调'))
    assert json.loads((out / 'results.jsonl').read_text(encoding='utf-8'))['status'] == 'completed'
    assert len(list(out.glob('attempts-torn-*.bin'))) == 1


def test_selection_rejects_string_membership_instead_of_exact_strategy_list(tmp_path):
    from app.evaluation.runner import check_split, strategy_fingerprint
    data, manifest, cfg = freeze(tmp_path, [case()])
    report = tmp_path / 'report'; report.write_text('development', encoding='utf-8')
    selection = tmp_path / 'selection.json'
    cfg.update(phase='final', split='heldout', selection=str(selection))
    selection.write_text(json.dumps({'dataset_sha256': cfg['dataset_sha256'],
        'strategy_sha256': 'prefix' + strategy_fingerprint(cfg) + 'suffix',
        'development_report': str(report), 'development_report_sha256': hashlib.sha256(report.read_bytes()).hexdigest()}), encoding='utf-8')
    with pytest.raises(ValueError): check_split(cfg, json.loads(manifest.read_text(encoding='utf-8')))
