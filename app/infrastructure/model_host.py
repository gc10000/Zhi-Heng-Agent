"""Windows现有模型环境的受控桥接；Linux worker不安装CUDA或下载权重。"""
import hmac
import os
import threading
from fastapi import Depends, FastAPI, Header
from pydantic import BaseModel, ConfigDict, Field
from app.api.errors import APIError, install

app = FastAPI(title='本机模型桥接')
lock = threading.Lock()


def authorize(x_model_token: str = Header('')):
    expected = os.getenv('MODEL_HOST_TOKEN', '')
    if not expected or not hmac.compare_digest(expected, x_model_token):
        from fastapi import HTTPException
        raise HTTPException(401, '模型桥接令牌无效')


class TextBatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    texts: list[str] = Field(min_length=1, max_length=64)


@app.get('/health', dependencies=[Depends(authorize)])
def health():
    return {'ready': True}


@app.post('/embeddings', dependencies=[Depends(authorize)])
def embeddings(data: TextBatch):
    if sum(map(len, data.texts)) > 256000:
        from fastapi import HTTPException
        raise HTTPException(413, '批次文本过大')
    # 重用宿主已有设备配置；不覆盖线程、模型版本或下载设置。
    with lock:
        from app.lm.embedding_utils import generate_embeddings
        values = generate_embeddings(data.texts)
        return {'dense': [[float(x) for x in vector] for vector in values['dense']],
                'sparse': [{str(k): float(v) for k, v in vector.items()} for vector in values['sparse']]}
