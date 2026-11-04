"""Windows现有模型环境的受控桥接；Linux worker不安装CUDA或下载权重。"""
import hmac
import os
import threading
from typing import Literal
from fastapi import Depends, FastAPI, Header
from pydantic import BaseModel, ConfigDict, Field
from app.api.errors import APIError, install

app = FastAPI(title='本机模型桥接')
lock = threading.Lock()
evaluation_slot = threading.BoundedSemaphore(1)


def authorize(x_model_token: str = Header('')):
    expected = os.getenv('MODEL_HOST_TOKEN', '')
    if not expected or not hmac.compare_digest(expected, x_model_token):
        from fastapi import HTTPException
        raise HTTPException(401, '模型桥接令牌无效')


class TextBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    texts: list[str] = Field(min_length=1, max_length=64)
    input_type:Literal['query','document']='document'


@app.get('/health', dependencies=[Depends(authorize)])
def health():
    return {'ready': True}


@app.get('/health/ready', dependencies=[Depends(authorize)])
def model_readiness():
    import sys
    from fastapi.responses import JSONResponse
    embedding = sys.modules.get('app.lm.embedding_utils')
    reranker = sys.modules.get('app.lm.reranker_utils')
    loaded = dict(embedding=getattr(embedding, '_bge_m3_ef', None) is not None,
                  reranker=getattr(reranker, '_reranker_model', None) is not None)
    # 只看现有单例，不调用get_*工厂，不产生预热或推理。
    ready = all(loaded.values())
    return JSONResponse({'ready': ready, 'loaded': loaded}, status_code=200 if ready else 503)


class RankBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    pairs: list[tuple[str, str]] = Field(min_length=1, max_length=64)


@app.post('/rerank', dependencies=[Depends(authorize)])
def rerank(data: RankBatch):
    if sum(len(q) + len(p) for q, p in data.pairs) > 256000:
        from fastapi import HTTPException
        raise HTTPException(413, '重排批次过大')
    with lock:
        from app.lm.reranker_utils import compute_rerank_scores
        return {'scores': compute_rerank_scores([list(pair) for pair in data.pairs], normalize=True)}


@app.post('/evaluation-jobs/{experiment_id}', dependencies=[Depends(authorize)])
def evaluation_job(experiment_id: str):
    from uuid import UUID
    from fastapi import HTTPException
    try:
        UUID(experiment_id)
    except ValueError:
        raise HTTPException(422, '实验ID无效') from None
    if not evaluation_slot.acquire(blocking=False):
        raise HTTPException(429, '独立评测预算已占用')
    try:
        from app.evaluation.jobs import run_local_job
        run_local_job(experiment_id)
        return {'accepted': True}
    finally:
        evaluation_slot.release()


@app.post('/embeddings', dependencies=[Depends(authorize)])
def embeddings(data: TextBatch):
    if sum(map(len, data.texts)) > 256000:
        from fastapi import HTTPException
        raise HTTPException(413, '批次文本过大')
    # 重用宿主已有设备配置；不覆盖线程、模型版本或下载设置。
    with lock:
        from app.lm.embedding_utils import generate_embeddings
        values = generate_embeddings(data.texts,input_type=data.input_type)
        return {'dense': [[float(x) for x in vector] for vector in values['dense']],
                'sparse': [{str(k): float(v) for k, v in vector.items()} for vector in values['sparse']]}
