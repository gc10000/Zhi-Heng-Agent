"""已有模型包装的并发首次加载及query/document语义；不加载真实权重。"""
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize('kind',['embedding','rerank'])
def test_simultaneous_first_calls_construct_one_model(monkeypatch,kind):
    if kind=='embedding':
        from app.lm import embedding_utils as module
        import pymilvus.model.hybrid as sdk
        getter=module.get_bge_m3_ef
        monkeypatch.setattr(module,'_bge_m3_ef',None)
        sdk_attr='BGEM3EmbeddingFunction'
    else:
        from app.lm import reranker_utils as module
        import FlagEmbedding as sdk
        getter=module.get_reranker_model
        monkeypatch.setattr(module,'_reranker_model',None)
        sdk_attr='FlagReranker'
    calls=[]
    def factory(**kwargs):
        calls.append(kwargs);time.sleep(.05);return object()
    monkeypatch.setattr(sdk,sdk_attr,factory)
    barrier=threading.Barrier(4)
    def load():barrier.wait();return getter()
    with ThreadPoolExecutor(max_workers=4) as pool:models=list(pool.map(lambda _:load(),range(4)))
    assert len(calls)==1,'并发首次使用只能构造一份模型'
    assert all(model is models[0] for model in models)


def test_query_runner_uses_sdk_query_encoding_instead_of_document_encoding(monkeypatch):
    import numpy as np
    from scipy.sparse import csr_array
    from app.lm import embedding_utils
    from app.runs.query_runner import encode
    calls=[]
    def value(kind,texts):
        calls.append(kind)
        return dict(dense=np.array([[1.,0.]]),sparse=csr_array([[0.,.5]]))
    model=SimpleNamespace(encode_queries=lambda texts:value('query',texts),encode_documents=lambda texts:value('document',texts))
    monkeypatch.setattr(embedding_utils,'get_bge_m3_ef',lambda:model)
    monkeypatch.delenv('MODEL_HOST_URL',raising=False);monkeypatch.delenv('MODEL_HOST_TOKEN',raising=False)
    result=encode(['参数'])
    assert result==dict(dense=[[1.,0.]],sparse=[{1:.5}])
    assert calls==['query'],'正式查询应调用SDK查询接口，导入继续使用document接口'


def test_installed_bgem3_query_and_document_methods_share_encode_semantics():
    from pymilvus.model.hybrid.bge_m3 import BGEM3EmbeddingFunction
    model=BGEM3EmbeddingFunction.__new__(BGEM3EmbeddingFunction)
    seen=[]
    model._encode=lambda values:seen.append(values) or dict(dense=values,sparse=values)
    assert model.encode_queries(['同一文本'])==model.encode_documents(['同一文本'])
    assert seen==[['同一文本'],['同一文本']]


@pytest.mark.parametrize('kind',['embedding','rerank'])
def test_failed_first_load_does_not_poison_next_attempt(monkeypatch,kind):
    if kind=='embedding':
        from app.lm import embedding_utils as module
        import pymilvus.model.hybrid as sdk
        name='_bge_m3_ef';attr='BGEM3EmbeddingFunction';getter=module.get_bge_m3_ef
    else:
        from app.lm import reranker_utils as module
        import FlagEmbedding as sdk
        name='_reranker_model';attr='FlagReranker';getter=module.get_reranker_model
    monkeypatch.setattr(module,name,None)
    calls=[];ready=object()
    def load(**kw):
        calls.append(kw)
        if len(calls)==1:raise RuntimeError('synthetic-load-failure')
        return ready
    monkeypatch.setattr(sdk,attr,load)
    with pytest.raises(RuntimeError):getter()
    assert getattr(module,name) is None
    assert getter() is getter() is ready and len(calls)==2


def test_embedding_batches_preserve_query_document_order_and_do_not_overlap(monkeypatch):
    import json,numpy as np
    from scipy.sparse import csr_array
    from app.lm import embedding_utils as module
    monkeypatch.setenv('MODEL_RUNTIME_JSON',json.dumps(dict(embedding_batch_size=2)))
    seen=[];active=0
    def compute(kind,texts):
        nonlocal active
        assert active==0
        active+=1;time.sleep(.01);seen.append((kind,list(texts)));active-=1
        return dict(dense=np.array([[float(t),1.] for t in texts]),sparse=csr_array([[0.,float(t)+1.] for t in texts]))
    model=SimpleNamespace(encode_queries=lambda t:compute('query',t),encode_documents=lambda t:compute('document',t))
    monkeypatch.setattr(module,'get_bge_m3_ef',lambda:model)
    with ThreadPoolExecutor(max_workers=2) as pool:
        jobs=[pool.submit(module.generate_embeddings,[str(i) for i in range(5)],input_type=k) for k in ('query','document')]
        outputs=[job.result() for job in jobs]
    assert all(v['dense']==[[float(i),1.] for i in range(5)] for v in outputs)
    assert sorted(len(t) for k,t in seen)==[1,1,2,2,2,2]


def test_rerank_batches_handle_scalar_one_and_reject_partial_failure(monkeypatch):
    import json
    from app.lm.reranker_utils import compute_rerank_scores
    from app.infrastructure.providers.policy import ProviderFailure
    monkeypatch.setenv('MODEL_RUNTIME_JSON',json.dumps(dict(rerank_batch_size=2)))
    seen=[]
    def rank(pairs,**kw):
        seen.append((pairs,kw))
        return .5 if len(pairs)==1 else [.1,.2]
    model=SimpleNamespace(compute_score=rank)
    assert compute_rerank_scores([['q',str(i)] for i in range(5)],normalize=True,model=model)==[.1,.2,.1,.2,.5]
    assert [len(p) for p,kw in seen]==[2,2,1] and all(kw==dict(normalize=True) for p,kw in seen)
    model.compute_score=lambda *a,**kw:[float('nan')]
    with pytest.raises(ProviderFailure):compute_rerank_scores([['q','bad']],model=model)


@pytest.mark.parametrize('value',[dict(embedding_batch_size=0),dict(rerank_batch_size=65),dict(cache_enabled=1),dict(cache_ttl_seconds=0),dict(extra=1)])
def test_invalid_runtime_policy_rejected(value):
    from app.lm.runtime import ModelRuntimePolicy
    with pytest.raises(ValueError):ModelRuntimePolicy(**value)


@pytest.mark.parametrize('kind',['query','document'])
def test_host_bridge_preserves_requested_encoding_type(monkeypatch,kind):
    import requests
    from app.infrastructure.queue.model_client import HostEmbedder
    from app.infrastructure.model_host import TextBatch,embeddings
    from app.lm import embedding_utils
    monkeypatch.setenv('MODEL_HOST_URL','http://synthetic.invalid')
    monkeypatch.setenv('MODEL_HOST_TOKEN','synthetic')
    monkeypatch.setenv('PROVIDER_POLICIES_ENABLED','false')
    seen=[]
    monkeypatch.setattr(embedding_utils,'generate_embeddings',lambda texts,**kw:seen.append((texts,kw)) or dict(dense=[[1.,0.]],sparse=[{1:.5}]))
    class Session:
        def __enter__(self):return self
        def __exit__(self,*args):pass
        def post(self,url,**kw):
            value=embeddings(TextBatch.model_validate(kw['json']))
            return SimpleNamespace(raise_for_status=lambda:None,json=lambda:value)
    monkeypatch.setattr(requests,'Session',Session)
    assert HostEmbedder(input_type=kind)(['参数'])['dense']==[[1.,0.]]
    assert seen==[(['参数'],dict(input_type=kind))]


def test_explicit_warmup_reuses_public_bounded_entry_points(monkeypatch):
    from app.lm import runtime,embedding_utils,reranker_utils
    seen=[]
    monkeypatch.setattr(embedding_utils,'generate_embeddings',lambda t,**kw:seen.append(('embedding',kw)))
    monkeypatch.setattr(reranker_utils,'compute_rerank_scores',lambda p,**kw:seen.append(('rerank',kw)))
    assert runtime.warmup_models()==dict(embedding_ready=True,rerank_ready=True)
    assert seen==[('embedding',dict(input_type='query')),('rerank',dict(normalize=True))]


@pytest.mark.parametrize('concurrency',[1,2,4])
def test_resource_wave_observes_every_concurrent_session_without_model_or_cloud(concurrency):
    from app.evaluation.resource_benchmark import measure_wave
    seen=[]
    def execute(q):seen.append(q['id']);return dict(stage_counts=dict(context=1))
    wave=measure_wave(execute,[dict(id=str(i)) for i in range(4)],concurrency,resources=lambda:dict(rss_bytes=1))
    assert wave['completed']==len(seen)==concurrency and wave['failed']==0
    assert len(wave['records'])==concurrency and wave['seconds']>0
    assert wave['before']==wave['after']==dict(rss_bytes=1)


def test_resource_wave_failure_cannot_be_reported_as_completed():
    from app.evaluation.resource_benchmark import measure_wave
    def fail(q):raise RuntimeError('synthetic-inference')
    with pytest.raises(RuntimeError):measure_wave(fail,[dict(id=str(i)) for i in range(4)],4,resources=lambda:{})
