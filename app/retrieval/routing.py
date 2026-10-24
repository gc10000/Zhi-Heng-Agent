"""明确诊断意图才增强；参数/错误码保持直接本地检索。"""
import os
import re
from pydantic import BaseModel,ConfigDict,Field


class EnhancementPolicy(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True,allow_inf_nan=False)
    hyde_enabled:bool=Field(default=False,strict=True)
    decomposition_enabled:bool=Field(default=False,strict=True)
    timeout_seconds:float=Field(default=8.,ge=.01,le=60.,strict=True)
    max_queries:int=Field(default=3,ge=1,le=3,strict=True)
    hyde_max_chars:int=Field(default=2000,ge=1,le=2000,strict=True)
    hyde_output_tokens:int=Field(default=512,ge=1,le=1024,strict=True)

    @classmethod
    def load(cls):
        raw=os.getenv('RETRIEVAL_ENHANCEMENT_JSON','').strip()
        if not raw:return cls()
        try:return cls.model_validate_json(raw)
        except ValueError:raise ValueError('RETRIEVAL_ENHANCEMENT_JSON须为有效有界JSON，详见配置文档') from None


def diagnostic_intent(question):
    return bool(re.search(r'故障|无法|不能|不亮|异常|时断时续|掉线',question)) and not bool(re.search(r'错误码|故障码|报错\s*[:：]?\s*[A-Za-z0-9]',question))


def enhancement_queries(plan,policy):
    policy=EnhancementPolicy.model_validate(policy)
    allowed=plan.route=='answer' and bool(plan.product_ids) and not plan.unconfirmed_tokens and diagnostic_intent(plan.original_query)
    parts=[q.strip() for q in re.split(r'并且|同时|以及|[；;]',plan.original_query) if q.strip()]
    queries=tuple(dict.fromkeys('设备型号：'+plan.slots.get('device','')+'\n现象：'+q for q in parts))[:max(0,policy.max_queries-1)]
    return dict(hyde=allowed and policy.hyde_enabled,
        decomposition=queries if allowed and policy.decomposition_enabled and len(parts)>1 else ())
