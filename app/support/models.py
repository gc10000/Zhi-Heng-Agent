"""支持上下文：候选、自报事实与资料快照分开保存。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

SLOTS = ('question', 'device', 'symptom', 'environment', 'error_code', 'tried')


class SupportInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0)
    values: dict[Literal['question', 'device', 'symptom', 'environment', 'error_code', 'tried'], str] = Field(default_factory=dict, max_length=6)
    confirmed: bool = True
    action: Literal['update', 'handoff', 'resolve', 'cancel'] = 'update'
    run_id: str | None = Field(default=None, max_length=128)

