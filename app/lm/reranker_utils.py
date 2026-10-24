import threading
from app.conf.reranker_config import reranker_config

_reranker_model = None
_load_lock = threading.Lock()

def get_reranker_model():
    from FlagEmbedding import FlagReranker
    global _reranker_model  
    with _load_lock:
        if _reranker_model is None:
            _reranker_model= FlagReranker(
                model_name_or_path=reranker_config.bge_reranker_large,
                # FlagEmbedding 1.3.5 的构造参数为 devices；device 会被忽略。
                devices=reranker_config.bge_reranker_device,
                use_fp16=reranker_config.bge_reranker_fp16
            )
    return _reranker_model

def compute_rerank_scores(pairs, *, normalize=None,model=None):
    """正式/兼容入口共用小批锁；异常不返回半批成功结果。"""
    from app.lm.runtime import ModelRuntimePolicy,inference_lock
    from app.infrastructure.providers.policy import ProviderFailure
    import math
    if not pairs:return []
    policy=ModelRuntimePolicy.load()
    result=[]
    for start in range(0,len(pairs),policy.rerank_batch_size):
        batch=pairs[start:start+policy.rerank_batch_size]
        with inference_lock:
            model=get_reranker_model() if model is None else model
            scores=model.compute_score(batch,**({} if normalize is None else {'normalize':normalize}))
        if isinstance(scores,(int,float)):scores=[scores]
        try:
            values=[float(s) for s in scores]
            if len(values)!=len(batch) or not all(math.isfinite(s) for s in values):raise ValueError()
        except (ValueError,TypeError):raise ProviderFailure('provider_invalid_response') from None
        result.extend(values)
    return result
