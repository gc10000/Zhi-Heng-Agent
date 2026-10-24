"""缓存范围、退出代际、并发与边界，全部使用离线向量。"""
import copy
import threading
import time
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.retrieval.cache import ScopedEmbeddingCache,REQUIRED_SCOPE
from app.lm.runtime import ModelRuntimePolicy


def scope():return dict(user_id='u',permissions=['k'],owner_id='o',kb_id='k',products=['p'],revisions=[['d','r']],model='m',strategy='s')


@pytest.mark.parametrize('field',sorted(REQUIRED_SCOPE))
def test_every_scope_component_prevents_cross_scope_reuse(field):
    cache=ScopedEmbeddingCache();policy=ModelRuntimePolicy(cache_enabled=True)
    calls=[]
    def compute(texts):calls.append(texts);return dict(dense=[[1.]],sparse=[{1:.5}])
    a=scope();first=cache.get_or_compute(a,['q'],compute,policy);first['dense'][0][0]=9.
    assert cache.get_or_compute(a,['q'],compute,policy)['dense']==[[1.]]
    other=copy.deepcopy(a);other[field]='different'
    cache.get_or_compute(other,['q'],compute,policy)
    assert len(calls)==2
    cache.get_or_compute(a,['new-question'],compute,policy)
    assert len(calls)==3


def test_ttl_lru_disabled_and_errors_never_become_cached_success():
    now=[0.];cache=ScopedEmbeddingCache(clock=lambda:now[0]);p=ModelRuntimePolicy(cache_enabled=True,cache_max_entries=1,cache_ttl_seconds=1)
    calls=[]
    def compute(t):calls.append(t);return t
    cache.get_or_compute(scope(),['a'],compute,p)
    cache.get_or_compute(scope(),['b'],compute,p)
    cache.get_or_compute(scope(),['a'],compute,p)
    now[0]=2.;cache.get_or_compute(scope(),['a'],compute,p)
    assert len(calls)==4 and len(cache.entries)==1
    off=ModelRuntimePolicy();cache.get_or_compute(scope(),['a'],compute,off);cache.get_or_compute(scope(),['a'],compute,off)
    assert len(calls)==6
    def fail(t):raise TimeoutError('synthetic')
    with pytest.raises(TimeoutError):cache.get_or_compute(scope(),['fail'],fail,p)
    assert cache.get_or_compute(scope(),['fail'],compute,p)==['fail']


def test_concurrent_identical_misses_compute_once_and_return_copies():
    cache=ScopedEmbeddingCache();p=ModelRuntimePolicy(cache_enabled=True);barrier=threading.Barrier(4);calls=[]
    def compute(t):calls.append(t);time.sleep(.05);return [[1.]]
    def query():barrier.wait();return cache.get_or_compute(scope(),['q'],compute,p)
    with ThreadPoolExecutor(max_workers=4) as pool:values=list(pool.map(lambda _:query(),range(4)))
    assert len(calls)==1
    values[0][0][0]=9.
    assert all(v==[[1.]] for v in values[1:])


def test_logout_during_computation_cannot_repopulate_or_join_old_generation():
    cache=ScopedEmbeddingCache();p=ModelRuntimePolicy(cache_enabled=True);started=threading.Event();release=threading.Event()
    def old(t):started.set();assert release.wait(2);return ['old']
    with ThreadPoolExecutor(max_workers=1) as pool:
        pending=pool.submit(cache.get_or_compute,scope(),['q'],old,p)
        assert started.wait(2)
        cache.invalidate('u')
        assert cache.get_or_compute(scope(),['q'],lambda t:['new'],p)==['new']
        release.set();assert pending.result()==['old']
    assert cache.get_or_compute(scope(),['q'],lambda t:pytest.fail('旧计算不得覆盖新代缓存'),p)==['new']


def test_incomplete_scope_rejected_before_compute():
    cache=ScopedEmbeddingCache()
    with pytest.raises(ValueError):cache.get_or_compute({},['q'],lambda t:pytest.fail('缺范围不得调用'),ModelRuntimePolicy(cache_enabled=True))
