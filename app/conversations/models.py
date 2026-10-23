"""会话可变展示字段与逐轮不可变设备快照分离。"""
from pydantic import BaseModel, ConfigDict, Field


class ConversationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(default='新会话', min_length=1, max_length=200)
    kb_id: str = Field(min_length=1, max_length=128)
    product_ids: list[str] = Field(default_factory=list, max_length=50)


class ConversationPatch(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0)
    title: str | None = Field(default=None, min_length=1, max_length=200)
    archived: bool | None = None
