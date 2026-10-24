"""网格只执行dev，标签不进入模型；阶段追踪包含真实重排结果。"""
import copy
from types import SimpleNamespace
import pytest
from app.evaluation.retrieval_grid import RetrievalExecutor, validate_grid
from app.retrieval.search import RetrievalPolicy
from tests.unit.test_evaluation_dataset import case, freeze
from app.evaluation.validate_dataset import file_sha


def fixture_config():
    return dict(target=dict(kb_id='kb'), corpus=dict(documents=[dict(document_id='d', revision_id='r', original_sha256='a'*64)],
        snapshot=dict(documents=[dict(assets=[])])))


def test_grid_records_actual_rerank_trace_and_never_sends_gold_to_models():
    cfg = fixture_config()
    entity = dict(document_id='d', revision_id='r', chunk_uid='c', text='电压24V', metadata=dict(
        source_refs=[dict(kind='pdf', page=2)], asset_ids=[]))
    products = [dict(product_id='p', model='AX')]
    index = SimpleNamespace(search=lambda *a, **kw: [dict(entity=entity)])
    repo = SimpleNamespace(kb_id='kb', get_active_revisions=lambda: [dict(document_id='d', active_revision_id='r')])
    g = SimpleNamespace(owner_id='owner', repo=lambda kb: repo, index=lambda: index,
        product_kbs=SimpleNamespace(distinct=lambda *a: ['p']),
        products=SimpleNamespace(collection=SimpleNamespace(find=lambda *a: products)))
    seen = []
    def encode(texts):
        seen.extend(texts); return dict(dense=[[1.,0.]], sparse=[{1:.5}])
    def rank(q, docs):
        seen.append(q); seen.extend(d['text'] for d in docs)
        return [d | dict(score=.9) for d in docs]
    q = case(); q['expected']['key_points'] = ['private-gold-canary']
    execute = RetrievalExecutor(cfg, g, embedder=encode, ranker=rank)
    result = execute.execute(q, RetrievalPolicy())
    assert 'private-gold-canary' not in str(seen)
    assert result['stage_metrics'] == dict(candidates=1., reranked=1., context=1.)
    assert result['trace'][0]['stages'][-1]['stage'] == 'rerank'
    assert result['trace'][0]['stages'][-1]['score'] == .9


def grid_fixture(tmp_path):
    rows = [case(f'q{i}', 'dev' if i < 35 else 'heldout', f'g{i}') for i in range(50)]
    data, manifest, cfg = freeze(tmp_path, rows)
    cfg.update(execution_mode='real_retrieval_grid', split_manifest_sha256=file_sha(manifest),
        grid=[dict(id='control', policy=RetrievalPolicy().model_dump())])
    return data, manifest, cfg


def test_grid_selects_only_frozen_dev(tmp_path):
    data, manifest, cfg = grid_fixture(tmp_path)
    assert [q['id'] for q in validate_grid(cfg, data, manifest)] == [f'q{i}' for i in range(35)]


@pytest.mark.parametrize('change', [lambda c: c.update(split='heldout'),
    lambda c: c.update(phase='final'), lambda c: c.update(split_manifest_sha256='b'*64),
    lambda c: c.update(dataset_sha256='b'*64), lambda c: c.update(execution_mode='unit_injection'),
    lambda c: c['grid'].append(copy.deepcopy(c['grid'][0])),
    lambda c: c['grid'][0].update(id='../private'),
    lambda c: c['grid'][0]['policy'].update(context_limit=1001)])
def test_invalid_grid_rejected_before_resources(tmp_path, change):
    data, manifest, cfg = grid_fixture(tmp_path); change(cfg)
    with pytest.raises(ValueError): validate_grid(cfg, data, manifest)
