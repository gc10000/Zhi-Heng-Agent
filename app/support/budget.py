"""只读工具累计预算；预留先落库，崩溃或重复不能无限重试。"""
import json
from pydantic import BaseModel, ConfigDict, Field
from app.knowledge.repository import fingerprint


class ToolBudget(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid', allow_inf_nan=False)
    max_calls: int = Field(default=6, ge=1, le=6)
    max_searches: int = Field(default=2, ge=0, le=2)
    max_seconds: float = Field(default=30, gt=0, le=30)
    max_tokens: int = Field(default=12000, ge=1, le=12000)


def stop_reason(calls, policy):
    if any(call['status'] == 'running' for call in calls):
        return 'tool_inflight'
    if len(calls) >= policy.max_calls:
        return 'tool_call_budget'
    if sum(call.get('elapsed', 0) for call in calls) >= policy.max_seconds:
        return 'tool_time_budget'
    if sum(call.get('tokens', 0) for call in calls) >= policy.max_tokens:
        return 'tool_token_budget'
    return None


def result_cost(output):
    # 无生成分词器的只读JSON用UTF-8字节保守计数，不冒充供应商usage。
    return len(json.dumps(output, ensure_ascii=False, sort_keys=True).encode('utf-8'))


def repeated(calls, output):
    identity = fingerprint(output)
    return any(call.get('output_hash') == identity for call in calls)
