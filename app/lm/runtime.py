"""单进程模型共享推理锁与有界小批策略；不创建进程或自动下载模型。"""
import os
import threading
from pydantic import BaseModel,ConfigDict,Field

inference_lock=threading.RLock()


class ModelRuntimePolicy(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    embedding_batch_size:int=Field(default=4,ge=1,le=64,strict=True)
    rerank_batch_size:int=Field(default=8,ge=1,le=64,strict=True)
    cache_enabled:bool=Field(default=False,strict=True)
    cache_max_entries:int=Field(default=128,ge=1,le=2048,strict=True)
    cache_ttl_seconds:int=Field(default=60,ge=1,le=3600,strict=True)

    @classmethod
    def load(cls):
        value=os.getenv('MODEL_RUNTIME_JSON','').strip()
        if not value:return cls()
        try:return cls.model_validate_json(value)
        except ValueError:raise ValueError('MODEL_RUNTIME_JSON须为有效有界配置，详见配置文档') from None


def warmup_models():
    from .embedding_utils import generate_embeddings
    from .reranker_utils import compute_rerank_scores
    generate_embeddings(['设备参数预热'],input_type='query')
    compute_rerank_scores([['设备参数','参数以资料为准。']],normalize=True)
    return dict(embedding_ready=True,rerank_ready=True)
