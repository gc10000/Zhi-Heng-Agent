"""浏览器身份与授权范围；公开对象不包含密码或会话散列。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class Principal(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    user_id: str
    username: str
    role: Literal['viewer', 'maintainer', 'admin']
    kb_ids: tuple[str, ...]


class LoginInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    username: str = Field(min_length=1, max_length=128)
    password: str = Field(min_length=1, max_length=1024)
