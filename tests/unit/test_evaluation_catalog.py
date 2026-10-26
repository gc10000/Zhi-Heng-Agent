"""服务器目录只登记冻结dev题集和配置，不接受客户端路径。"""
import importlib.util
import json

import pytest

from tests.unit.test_evaluation_dataset import case, freeze


def catalog_type():
    spec = importlib.util.find_spec('app.evaluation.catalog')
    assert spec is not None, 'M6-03需要受控服务端评测目录'
    from app.evaluation.catalog import EvaluationCatalog
    return EvaluationCatalog


def create_catalog(tmp_path, *, path_override=None):
    from app.evaluation.validate_dataset import file_sha
    root = tmp_path / 'evals'
    (root / 'datasets').mkdir(parents=True)
    (root / 'configs').mkdir()
    rows = [case(f'q{i}', 'dev' if i < 35 else 'heldout', f'g{i}') for i in range(50)]
    dataset, manifest, config = freeze(root / 'datasets', rows)
    config.update(metric_schema_version=1, seed=11)
    config_path = root / 'configs' / 'dev.yaml'
    config_path.write_text(
        'experiment_id: registered-dev\nphase: development\nsplit: dev\n'
        'execution_mode: real_query_runner\nstrategy: m3-baseline\nmetric_schema_version: 1\nseed: 11\n'
        f'dataset_sha256: {file_sha(dataset)}\nsplit_manifest_sha256: {file_sha(manifest)}\n'
        'versions:\n  code: code\n  model: model\n  prompt: prompt\n', encoding='utf-8')
    catalog_file = root / 'catalog.json'
    relative_dataset = path_override or 'datasets/questions.jsonl'
    catalog_file.write_text(json.dumps({
        'datasets': [{'id': 'support-dev', 'version': 'r1', 'dataset': relative_dataset,
                      'manifest': 'datasets/split.json', 'kb_ids': ['kb-test']}],
        'configs': [{'id': 'control', 'version': 'v1', 'path': 'configs/dev.yaml'}],
    }), encoding='utf-8')
    return root, catalog_file, dataset, manifest


def test_catalog_exposes_only_metadata_and_matches_dev_config_to_frozen_set(tmp_path):
    root, catalog_file, dataset, manifest = create_catalog(tmp_path)
    catalog = catalog_type()(catalog_file)
    options = catalog.list_datasets('kb-test')
    assert len(options) == 1
    assert options[0]['id'] == 'support-dev' and options[0]['question_count'] == 50
    assert 'path' not in json.dumps(options) and 'expected' not in json.dumps(options)
    resolved = catalog.resolve('support-dev', 'r1', 'control', 'v1', kb_id='kb-test')
    assert resolved['config']['split'] == 'dev'
    assert resolved['dataset_sha256'] == options[0]['dataset_sha256']
    assert resolved['selected_questions'] == 35


@pytest.mark.parametrize('unsafe', ['../private.jsonl', 'C:/private/eval.jsonl', '/etc/passwd'])
def test_catalog_rejects_absolute_or_parent_dataset_paths(tmp_path, unsafe):
    _, catalog_file, _, _ = create_catalog(tmp_path, path_override=unsafe)
    with pytest.raises(ValueError, match='路径|目录'):
        catalog_type()(catalog_file).list_datasets('kb-test')


def test_catalog_rejects_frozen_hash_drift_before_returning_options(tmp_path):
    root, catalog_file, dataset, _ = create_catalog(tmp_path)
    dataset.write_text(dataset.read_text(encoding='utf-8') + ' ', encoding='utf-8')
    with pytest.raises(ValueError, match='指纹|冻结|题集'):
        catalog_type()(catalog_file).list_datasets('kb-test')
