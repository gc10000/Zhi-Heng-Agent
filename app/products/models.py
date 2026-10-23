"""产品标准名与别名分离；型号范围通过product_id关联。"""
from pydantic import Field
from app.knowledge.models import Entity, ID, new_id


class Product(Entity):
    product_id: ID = Field(default_factory=new_id)
    owner_id: ID
    model: str
    brand: str | None = None
    series: str | None = None
    aliases: tuple[str, ...] = ()
