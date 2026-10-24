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


@pytest.mark.parametrize('skip_kind',['wrong_clarify','failed','expected_clarify'])
def test_grid_recall_never_drops_questions_that_require_evidence(tmp_path,monkeypatch,skip_kind):
    import json
    from app.evaluation import retrieval_grid as grid
    data,manifest,cfg=grid_fixture(tmp_path)
    if skip_kind=='expected_clarify':
        rows=[json.loads(line) for line in data.read_text('utf-8').splitlines()]
        rows[0]['allowed_evidence']=[]
        rows[0]['expected']['behavior']='clarify'
        data,manifest,_=freeze(tmp_path,rows)
        cfg.update(dataset_sha256=file_sha(data),split_manifest_sha256=file_sha(manifest))
    class Execute:
        def __init__(self,*a,**kw):self.encode=lambda q:None
        def execute(self,q,policy):
            if q['id']=='q0':
                if skip_kind=='failed':raise TimeoutError('synthetic')
                return dict(answer='',citations=[],behavior='clarify',route='clarify',stage_metrics={},stage_timings={})
            ref=q['allowed_evidence'][0][0]
            return dict(answer='',citations=[ref],behavior='answer',route='answer',
                stage_metrics=dict(candidates=1.,reranked=1.,context=1.),
                stage_timings=dict(estimated_pipeline_seconds=.01))
    monkeypatch.setattr(grid,'RetrievalExecutor',Execute)
    report=grid.run_grid(cfg,data,manifest,tmp_path/'result',None,embedder=None,ranker=lambda *a:None)[0]
    expected_count=34 if skip_kind=='expected_clarify' else 35
    expected_recall=1. if skip_kind=='expected_clarify' else 34/35
    for stage in ('candidates','reranked','context'):
        assert report['recall'][stage]['applicable_questions']==expected_count, '错误澄清和失败题不能从证据分母消失'
        assert report['recall'][stage]['mean']==pytest.approx(expected_recall)


@pytest.mark.parametrize('corruption',[None,'lock','missing','attempt','config','summary','duplicate','record_config'])
def test_independent_grid_analysis_validates_frozen_outputs_without_overwriting(tmp_path,monkeypatch,corruption):
    import json
    from app.evaluation import retrieval_grid as grid
    from app.evaluation.analyze_grid import analyze
    data,manifest,cfg=grid_fixture(tmp_path)
    class Execute:
        def __init__(self,*a,**kw):self.encode=lambda q:None
        def execute(self,q,policy):
            refs=[] if q['id']=='q0' else q['allowed_evidence'][0]
            return dict(answer='',citations=refs,behavior='clarify' if not refs else 'answer',
                route='clarify' if not refs else 'answer',stage_metrics={} if not refs else dict(candidates=1.,reranked=1.,context=1.),
                stage_timings={} if not refs else dict(estimated_pipeline_seconds=.01))
    monkeypatch.setattr(grid,'RetrievalExecutor',Execute)
    source=tmp_path/'result'
    grid.run_grid(cfg,data,manifest,source,None,embedder=None,ranker=lambda *a:None)
    child=source/'control'
    if corruption=='lock':(source/'.runner.lock').write_text('occupied')
    if corruption in ('missing','duplicate','record_config'):
        path=child/'results.jsonl';rows=[json.loads(x) for x in path.read_text('utf-8').splitlines()]
        if corruption=='missing':rows.pop()
        elif corruption=='duplicate':rows[-1]=rows[0]
        else:rows[0]['config_sha256']='a'*64
        text=''.join(json.dumps(r)+'\n' for r in rows)
        path.write_text(text,encoding='utf-8')
        if corruption=='record_config':(child/'attempts.jsonl').write_text(text,encoding='utf-8')
    if corruption=='attempt':(child/'attempts.jsonl').write_text('',encoding='utf-8')
    if corruption in ('config','summary'):
        path=child/'manifest.json' if corruption=='config' else source/'grid-summary.json'
        row=json.loads(path.read_text('utf-8'));row['config_sha256']='a'*64
        path.write_text(json.dumps(row),encoding='utf-8')
    before={p:p.read_bytes() for p in source.rglob('*') if p.is_file()}
    if corruption:
        with pytest.raises(ValueError):analyze(source,data,manifest)
    else:
        report=analyze(source,data,manifest)
        assert report['variants'][0]['recall']['context']==dict(mean=34/35,applicable_questions=35)
        assert report['variants'][0]['timed_questions']==34
        assert report['heldout_executed']==0 and report['paid_calls']==0
    assert {p:p.read_bytes() for p in before}==before,'独立分析不能改写原实验字节'
