from app.evaluation.versions import runtime_versions


def test_versions_bind_actual_code_prompt_weights_and_generation_config(tmp_path, monkeypatch):
    (tmp_path / 'app').mkdir(); (tmp_path / 'app/query.py').write_text('version=1', encoding='utf-8')
    (tmp_path / 'prompts').mkdir(); (tmp_path / 'prompts/answer_out.prompt').write_text('原提示词', encoding='utf-8')
    model = tmp_path / 'local-model'; model.mkdir(); (model / 'model.safetensors').write_bytes(b'weights')
    first = runtime_versions(root=tmp_path, model_paths={'embedding': model, 'reranker': model})
    assert set(first) == {'code', 'prompt', 'model'}
    (tmp_path / 'app/query.py').write_text('version=2', encoding='utf-8')
    code_changed = runtime_versions(root=tmp_path, model_paths={'embedding': model, 'reranker': model})
    assert code_changed['code'] != first['code'] and code_changed['model'] == first['model']
    (model / 'model.safetensors').write_bytes(b'changed-weights')
    changed = runtime_versions(root=tmp_path, model_paths={'embedding': model, 'reranker': model})
    assert changed['model'] != first['model']
    monkeypatch.setenv('LLM_DEFAULT_TEMPERATURE', '0')
    assert runtime_versions(root=tmp_path, model_paths={'embedding': model, 'reranker': model})['model'] != changed['model']


def test_missing_local_weights_rejected_before_automatic_download(tmp_path):
    import pytest
    with pytest.raises(ValueError): runtime_versions(root=tmp_path, model_paths={'embedding': tmp_path / 'absent'})


def test_evaluation_matching_code_changes_are_bound_before_paid_execution(tmp_path):
    (tmp_path / 'app/evaluation').mkdir(parents=True)
    matching = tmp_path / 'app/evaluation/runner.py'; matching.write_text('matching=1', encoding='utf-8')
    model = tmp_path / 'weights'; model.mkdir(); (model / 'model.bin').write_bytes(b'synthetic')
    before = runtime_versions(root=tmp_path, model_paths={'embedding': model})
    matching.write_text('matching=2', encoding='utf-8')
    after = runtime_versions(root=tmp_path, model_paths={'embedding': model})
    assert before['code'] != after['code']
    assert before['model'] == after['model']
