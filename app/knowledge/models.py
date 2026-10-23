"""知识实体；业务身份、不可变修订、内容指纹与来源精度分别记录。"""
import hashlib
import json
from typing import Annotated, Literal
from uuid import uuid4, uuid5, NAMESPACE_URL

from pydantic import BaseModel, ConfigDict, Field, model_validator

ID = Annotated[str, Field(strict=True, min_length=1)]
SHA256 = Annotated[str, Field(pattern=r'^[a-f0-9]{64}$')]


def new_id() -> str:
    return str(uuid4())


def content_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def stable_id(kind: str, revision_id: str, parts: list) -> str:
    """规范JSON消除拼接歧义；修订内同输入重试产生相同身份。"""
    return str(uuid5(NAMESPACE_URL, json.dumps([kind, revision_id, parts], ensure_ascii=False, sort_keys=True, separators=(',', ':'))))


class Entity(BaseModel):
    model_config = ConfigDict(frozen=True, extra='forbid')


class SourceRef(Entity):
    document_id: ID
    revision_id: ID
    kind: Literal['pdf', 'markdown', 'excel', 'image', 'image_description', 'legacy']
    page: int | None = Field(default=None, ge=1)
    printed_page: str | None = None
    section_path: tuple[str, ...] = ()
    sheet: str | None = None
    cell: str | None = None
    line_start: int | None = Field(default=None, ge=1)
    line_end: int | None = Field(default=None, ge=1)
    row_start: int | None = Field(default=None, ge=1)
    row_end: int | None = Field(default=None, ge=1)
    bbox: tuple[float, float, float, float] | None = None
    coordinate_system: Literal['normalized_top_left'] | None = None
    asset_id: ID | None = None

    @model_validator(mode='after')
    def location_consistency(self):
        if self.kind == 'excel' and self.page is not None:
            raise ValueError('Excel不能伪造PDF页码')
        if self.kind == 'pdf' and (self.sheet is not None or self.cell is not None):
            raise ValueError('PDF不能使用单元格定位')
        for start, end in ((self.line_start,self.line_end),(self.row_start,self.row_end)):
            if end is not None and (start is None or end < start):
                raise ValueError('来源范围必须正序')
        if self.bbox is not None:
            x0,y0,x1,y1=self.bbox
            if not (self.page and self.coordinate_system and 0<=x0<x1<=1 and 0<=y0<y1<=1):
                raise ValueError('区域必须附物理页码及归一化坐标系')
        return self


class KnowledgeBase(Entity):
    kb_id: ID = Field(default_factory=new_id)
    owner_id: ID
    name: str


class Document(Entity):
    document_id: ID = Field(default_factory=new_id)
    kb_id: ID
    owner_id: ID
    name: str
    purpose: Literal['technical', 'project_plan', 'unknown'] = 'unknown'
    product_ids: tuple[ID, ...] = ()
    active_revision_id: ID | None = None


class Revision(Entity):
    revision_id: ID = Field(default_factory=new_id)
    document_id: ID
    kb_id: ID
    owner_id: ID
    original_sha256: SHA256
    object_key: ID
    parser_version: str = 'unparsed'
    status: Literal['staged','validated','published','failed'] = 'staged'
    attempt: int = Field(default=0, ge=0)


class Section(Entity):
    section_id: ID
    document_id: ID
    revision_id: ID
    heading_path: tuple[str, ...] = ()
    source_refs: tuple[SourceRef, ...] = ()
    product_ids: tuple[ID, ...] = ()


class Chunk(Section):
    chunk_uid: ID
    parent_chunk_uid: ID | None = None
    ordinal: int = Field(ge=0, le=2147483647)
    text: str
    content_kind: Literal['text','table','image_description','warning','steps'] = 'text'
    asset_ids: tuple[ID, ...] = ()


class Asset(Entity):
    asset_id: ID
    document_id: ID
    revision_id: ID
    sha256: SHA256
    object_key: ID
    media_type: str
    source_refs: tuple[SourceRef, ...] = ()
    description: str | None = None
    description_status: Literal['pending','completed','failed','not_required'] = 'pending'
    description_cache_key: str | None = None
