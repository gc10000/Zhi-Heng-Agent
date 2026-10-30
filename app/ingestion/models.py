"""解析中间契约：原文、模型描述、定位精度和降级质量均显式保留。"""
from typing import Literal
from pydantic import Field
from app.knowledge.models import Entity, ID, SHA256, SourceRef


class Page(Entity):
    number: int = Field(ge=1)
    width: float | None = None
    height: float | None = None
    rotation: int = 0


class Cell(Entity):
    coordinate: str
    value: str | None = None
    formula: str | None = None
    cached_value: str | None = None


class Block(Entity):
    block_id: ID
    kind: Literal['text','heading','table','image','warning','steps']
    text: str = ''
    description: str | None = None
    heading_path: tuple[str, ...] = ()
    source_refs: tuple[SourceRef, ...] = ()
    product_ids: tuple[ID, ...] = ()
    asset_ids: tuple[ID, ...] = ()
    rows: tuple[tuple[str, ...], ...] = ()
    # PDF表格每行独立定位；空元组表示未提供行级定位，(page=None,)表示明确无法精确匹配。
    row_source_refs: tuple[tuple[SourceRef, ...], ...] = ()
    table_header_rows: int = Field(default=1,ge=1)
    row_numbers: tuple[int, ...] = ()
    cells: tuple[Cell, ...] = ()


class ParsedImage(Entity):
    image_id: ID
    local_path: str
    context: str = ''
    source_refs: tuple[SourceRef, ...] = ()


class ParsedDocument(Entity):
    document_id: ID
    revision_id: ID
    original_sha256: SHA256
    parser: str
    parser_version: str
    quality_flags: tuple[str, ...] = ()
    purpose: Literal['technical','project_plan','unknown'] = 'unknown'
    pages: tuple[Page, ...] = ()
    blocks: tuple[Block, ...] = ()
    images: tuple[ParsedImage, ...] = ()

    @property
    def tables(self):
        return tuple(b for b in self.blocks if b.kind=='table')
