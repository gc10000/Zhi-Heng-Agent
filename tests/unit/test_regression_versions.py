"""合成冻结题集；不修改真实题目或审核。"""
import copy
import json
import pytest
from concurrent.futures import ThreadPoolExecutor
from app.evaluation.catalog import EvaluationCatalog
from app.evaluation.regression_versions import derive_version
from tests.unit.test_evaluation_catalog import create_catalog
from tests.unit.test_evaluation_dataset import independent_annotation


def test_derived_version_is_immutable_recoverable_and_resolvable(tmp_path):
    root, path, dataset, manifest = create_catalog(tmp_path)
    catalog = EvaluationCatalog(path)
    parent = catalog.resolve('support-dev', 'r1', 'control', 'v1', kb_id='kb-test')
    before = dataset.read_bytes(), manifest.read_bytes(), path.read_bytes()
    question = json.loads(dataset.read_text(encoding='utf-8').splitlines()[0])
    question['expected']['key_points'] = ['合成修改，仍须保持范围']
    question['annotation'] = independent_annotation(question)
    result = derive_version(catalog, parent, question, dataset_id='support-dev', parent_version='r1', kb_id='kb-test')
    assert derive_version(catalog, parent, question, dataset_id='support-dev', parent_version='r1', kb_id='kb-test') == result
    resolved = catalog.resolve(**result, kb_id='kb-test')
    frozen = json.loads(resolved['manifest_path'].read_text(encoding='utf-8'))
    assert frozen['parent_dataset_sha256'] == parent['dataset_sha256']
    assert frozen['parent_manifest_sha256'] == parent['manifest_sha256']
    assert before == (dataset.read_bytes(), manifest.read_bytes(), path.read_bytes())
    assert resolved['config']['dataset_sha256'] == resolved['dataset_sha256']
    assert json.loads(resolved['dataset_path'].read_text(encoding='utf-8').splitlines()[0]) == question


@pytest.mark.parametrize('invalid', ['heldout', 'group', 'draft'])
def test_derivation_rejects_split_group_leakage_or_unreviewed_labels(tmp_path, invalid):
    _, path, dataset, _ = create_catalog(tmp_path)
    catalog = EvaluationCatalog(path)
    parent = catalog.resolve('support-dev', 'r1', 'control', 'v1', kb_id='kb-test')
    question = copy.deepcopy(json.loads(dataset.read_text(encoding='utf-8').splitlines()[0]))
    question['annotation'] = independent_annotation(question)
    if invalid == 'heldout': question['split'] = 'heldout'
    if invalid == 'group': question['group_id'] = 'g49'
    if invalid != 'draft': question['annotation'] = independent_annotation(question)
    else: question['annotation'] = {'method':'source_checked_assistant_draft','status':'draft'}
    with pytest.raises(ValueError):
        derive_version(catalog, parent, question, dataset_id='support-dev', parent_version='r1', kb_id='kb-test')


@pytest.mark.parametrize('point',['questions.jsonl','manifest.json','config.json','entry.json'])
def test_file_write_crashes_recover_without_exposing_partial_version(tmp_path,monkeypatch,point):
    import app.evaluation.regression_versions as module
    _,path,dataset,_=create_catalog(tmp_path)
    catalog=EvaluationCatalog(path)
    parent=catalog.resolve('support-dev','r1','control','v1',kb_id='kb-test')
    question=json.loads(dataset.read_text(encoding='utf-8').splitlines()[0])
    question['expected']['key_points']=['合成修订']
    question['annotation']=independent_annotation(question)
    real=module.immutable_file
    def crash(path,content):
        real(path,content)
        if path.name==point: raise SystemExit('合成落盘后退出')
    monkeypatch.setattr(module,'immutable_file',crash)
    with pytest.raises(SystemExit):
        derive_version(catalog,parent,question,dataset_id='support-dev',parent_version='r1',kb_id='kb-test')
    assert len(catalog.list_datasets('kb-test'))==(2 if point=='entry.json' else 1)
    monkeypatch.setattr(module,'immutable_file',real)
    identity=derive_version(catalog,parent,question,dataset_id='support-dev',parent_version='r1',kb_id='kb-test')
    assert catalog.resolve(**identity,kb_id='kb-test')['selected_questions']==35


def test_new_question_derives_parent_and_preserves_heldout(tmp_path):
    _,path,dataset,_=create_catalog(tmp_path)
    catalog=EvaluationCatalog(path)
    parent=catalog.resolve('support-dev','r1','control','v1',kb_id='kb-test')
    question=json.loads(dataset.read_text(encoding='utf-8').splitlines()[0])
    question.update(id='new-dev',group_id='new-family',question='合成新增回归题')
    question['annotation']=independent_annotation(question)
    identity=derive_version(catalog,parent,question,dataset_id='support-dev',parent_version='r1',kb_id='kb-test')
    actual=catalog.resolve(**identity,kb_id='kb-test')
    assert actual['selected_questions']==36
    before=[json.loads(l) for l in dataset.read_text(encoding='utf-8').splitlines() if json.loads(l)['split']=='heldout']
    after=[json.loads(l) for l in actual['dataset_path'].read_text(encoding='utf-8').splitlines() if json.loads(l)['split']=='heldout']
    assert before==after


def test_concurrent_same_derivation_publishes_one_immutable_version(tmp_path):
    _,path,dataset,_=create_catalog(tmp_path)
    catalog=EvaluationCatalog(path)
    parent=catalog.resolve('support-dev','r1','control','v1',kb_id='kb-test')
    question=json.loads(dataset.read_text(encoding='utf-8').splitlines()[0])
    question['expected']['key_points']=['并发合成修订']
    question['annotation']=independent_annotation(question)
    with ThreadPoolExecutor(max_workers=4) as pool:
        results=list(pool.map(lambda _:derive_version(catalog,parent,question,dataset_id='support-dev',
            parent_version='r1',kb_id='kb-test'),range(4)))
    assert all(r==results[0] for r in results)
    assert len(catalog.list_datasets('kb-test'))==2
