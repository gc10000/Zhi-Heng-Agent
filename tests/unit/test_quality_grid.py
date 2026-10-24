"""真实阶段复用不改变证据语义，也不能让缓存绕过可选分支时限。"""
from types import SimpleNamespace
import time
import pytest
from app.evaluation.quality_grid import QualityExecutor,StageCache
from app.evaluation.strategy import EvaluationStrategy
from tests.unit.test_retrieval_grid import fixture_config
from tests.unit.test_evaluation_dataset import case


def fixture_executor(tmp_path,*,base=True,hyde=None):
    cfg=fixture_config();entity=dict(document_id='d',revision_id='r',chunk_uid='c',text='实际资料24V',
        metadata=dict(source_refs=[dict(kind='pdf',page=2)],asset_ids=[],product_ids=['p']))
    calls=[]
    class Index:
        def search(self,repo,text,**kwargs):
            calls.append(text)
            return [dict(entity=entity)] if base or '检索假设' in text else []
    repo=SimpleNamespace(owner_id='o',kb_id='kb',get_active_revisions=lambda:[dict(document_id='d',active_revision_id='r')])
    g=SimpleNamespace(owner_id='o',repo=lambda kb:repo,index=Index,
        product_kbs=SimpleNamespace(distinct=lambda *a:['p']),
        products=SimpleNamespace(collection=SimpleNamespace(find=lambda *a:[dict(product_id='p',model='AX')])) )
    rank_calls=[]
    def rank(q,docs):rank_calls.append(q);return [d|dict(score=.9) for d in docs]
    executor=QualityExecutor(cfg,g,embedder=lambda t:dict(dense=[[1.,0.]],sparse=[{1:.5}]),ranker=rank,
        cache=StageCache(tmp_path/'cache','frozen-scope'),hyde=hyde)
    q=case();q.update(question='AX无法启动故障',product_names=['AX'],history=[])
    return executor,q,calls,rank_calls


def test_quality_stage_cache_reuses_real_observed_work_and_never_sends_gold(tmp_path):
    executor,q,calls,ranks=fixture_executor(tmp_path)
    q['expected']['key_points']=['private-gold-canary']
    first=executor.execute(q,EvaluationStrategy().model_dump())
    second=executor.execute(q,EvaluationStrategy(answer_budget=dict(context_window=64000)).model_dump())
    assert len(calls)==len(ranks)==1
    assert 'private-gold-canary' not in str(calls+ranks)
    assert first['citations']==second['citations'] and first['stage_metrics']['context']==1.
    assert all(o['reused'] for o in second['stage_cache'])


def test_cached_slow_hyde_cannot_become_accepted_only_because_cache_is_fast(tmp_path):
    def hyde(q,p,field):time.sleep(.3);return 'synthetic-query-only'
    executor,q,calls,ranks=fixture_executor(tmp_path,base=False,hyde=hyde)
    policy=EvaluationStrategy(enhancement=dict(hyde_enabled=True,timeout_seconds=.15)).model_dump()
    first=executor.execute(q,policy)
    time.sleep(.4)
    second=executor.execute(q,policy)
    assert first['citations']==[]
    assert second['citations']==[],'原始HyDE超时必须在复用后继续作为超时，不得伪装组合改善'
    assert second['retrieval_branches'][1]['status']=='timeout'


def test_stage_cache_rejects_modified_value_and_never_overwrites_it(tmp_path):
    import json
    cache=StageCache(tmp_path,'scope')
    cache.get('hypothesis',['q'],lambda:'original')
    path=next(tmp_path.glob('*.json'));data=json.loads(path.read_text('utf-8'));data['value']='changed'
    path.write_text(json.dumps(data),encoding='utf-8');before=path.read_bytes()
    with pytest.raises(ValueError):cache.get('hypothesis',['q'],lambda:pytest.fail('污染不得重调覆盖'))
    assert path.read_bytes()==before


def test_expired_optional_branch_preserves_local_duplicate(tmp_path):
    def hyde(q,p,field):time.sleep(.08);return 'same-evidence'
    executor,q,_,_=fixture_executor(tmp_path,hyde=hyde)
    policy=EvaluationStrategy(enhancement=dict(hyde_enabled=True,timeout_seconds=.03)).model_dump()
    first=executor.execute(q,policy)
    time.sleep(.12)
    second=executor.execute(q,policy)
    assert first['citations'] and first['citations']==second['citations']
    assert second['retrieval_branches'][1]['status']=='timeout'
    assert all(o.get('branch') in ('local','hyde','post_join') for o in second['stage_cache'])


def test_stage_cache_elapsed_time_is_integrity_checked(tmp_path):
    import json
    cache=StageCache(tmp_path,'scope')
    cache.get('hypothesis',['q'],lambda:'result')
    path=next(tmp_path.glob('*.json'));saved=json.loads(path.read_text('utf-8'))
    saved['seconds']=0.
    path.write_text(json.dumps(saved),encoding='utf-8')
    with pytest.raises(ValueError):cache.get('hypothesis',['q'],lambda:pytest.fail('禁止重写损坏缓存'))


def test_stage_cache_scope_and_inputs_are_isolated(tmp_path):
    a=StageCache(tmp_path,'frozen-a');b=StageCache(tmp_path,'frozen-b')
    assert a.get('hypothesis',['q'],lambda:['a'])[0]==['a']
    value,meta=a.get('hypothesis',['q'],lambda:pytest.fail('应复用'))
    value.append('mutation')
    assert meta['reused'] and a.get('hypothesis',['q'],lambda:None)[0]==['a']
    assert b.get('hypothesis',['q'],lambda:['b'])[0]==['b']
    assert a.get('hypothesis',['other'],lambda:['other'])[0]==['other']


@pytest.mark.parametrize('parameters',[
    dict(unknown=True),dict(enhancement=dict(timeout_seconds=float('nan'))),
    dict(retrieval=dict(context_limit=0)),dict(answer_budget=dict(context_window=256)),
    dict(runtime=dict(unknown=True)),dict(expansion=dict(enabled='yes'))])
def test_invalid_strategy_fails_before_retrieval(tmp_path,parameters):
    executor,q,calls,_=fixture_executor(tmp_path)
    with pytest.raises(ValueError):executor.execute(q,parameters)
    assert calls==[]


def test_provider_counts_preserve_options_and_count_failed_calls():
    from app.evaluation.provider_counts import LogicalProviderCounts
    counts=LogicalProviderCounts();seen=[]
    class Client:
        extra_body={'enable_thinking':False}
        def invoke(self,*args,**kwargs):seen.append(kwargs);raise RuntimeError('injected')
        def stream(self,*args,**kwargs):seen.append(kwargs);yield 'chunk'
    client=counts.wrap(Client())
    with pytest.raises(RuntimeError):client.invoke('private',extra_body={'max_tokens':10})
    stream=client.stream('private',temperature=0)
    assert counts.snapshot()==dict(invoke_started=1,stream_started=0)
    assert list(stream)==['chunk']
    assert client.extra_body=={'enable_thinking':False} and seen==[{'extra_body':{'max_tokens':10}},{'temperature':0}]
    assert counts.snapshot()==dict(invoke_started=1,stream_started=1)
