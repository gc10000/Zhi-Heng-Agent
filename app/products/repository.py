"""产品注册使用稳定业务ID；别名不覆盖标准型号。"""
from app.products.models import Product
from app.knowledge.repository import ConflictError, fingerprint, KnowledgeRepository


class ProductRepository:
    def __init__(self,db,*,owner_id):
        self.owner_id=owner_id
        self.collection=db['knowledge_products']
        self.collection.create_index('product_id',unique=True)

    def register(self,product:Product):
        if product.owner_id!=self.owner_id:
            raise ValueError('产品归属不匹配')
        data=product.model_dump(mode='json')
        data['request_fingerprint']=fingerprint(data)
        KnowledgeRepository._insert_once(self.collection,{'product_id':product.product_id,'owner_id':self.owner_id},data)
        return product
