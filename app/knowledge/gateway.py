"""单组织资料资源，按kb授权；不自动读取历史课程owner的数据。"""
from uuid import uuid4
from app.api.errors import APIError
from app.identity.api import require_kb
from app.knowledge.repository import KnowledgeRepository
from app.knowledge.publishing import RevisionPublisher
from app.products.models import Product
from app.products.repository import ProductRepository
from app.ingestion.jobs import JobRepository


def page(collection, query, id_field, *, cursor=None, limit=50, fields=None):
    query = dict(query)
    if cursor:
        query[id_field] = {'$gt': cursor}
    rows = list(collection.find(query).sort(id_field, 1).limit(limit + 1))
    clean = lambda row: {k: row[k] for k in fields if k in row} if fields else {k: v for k, v in row.items() if k != '_id'}
    return {'items': [clean(r) for r in rows[:limit]], 'next_cursor': rows[limit-1][id_field] if len(rows) > limit else None}


DOCUMENT_FIELDS = ('document_id', 'kb_id', 'name', 'purpose', 'product_ids', 'active_revision_id', 'active_generation')
REVISION_FIELDS = ('revision_id', 'document_id', 'kb_id', 'status', 'attempt', 'parser_version', 'quality_flags')


class KnowledgeGateway:
    def __init__(self, db, originals, *, owner_id, index_factory=None, max_upload_bytes=100_000_000):
        self.db, self.originals, self.owner_id = db, originals, owner_id
        self.index_factory, self.max_upload_bytes = index_factory, max_upload_bytes
        self.jobs = JobRepository(db)
        self.products = ProductRepository(db, owner_id=owner_id)
        self.product_kbs = db.knowledge_product_kbs
        self.product_kbs.create_index([('owner_id', 1), ('kb_id', 1), ('product_id', 1)], unique=True)
        db.knowledge_original_assets.create_index('asset_id', unique=True)
        db.knowledge_legacy_assets.create_index('asset_id', unique=True)

    def repo(self, kb):
        return KnowledgeRepository(self.db, kb_id=kb, owner_id=self.owner_id)

    def document(self, user, did):
        row = self.db.knowledge_documents.find_one({'document_id': did, 'owner_id': self.owner_id, 'kb_id': {'$in': list(user.kb_ids)}})
        if row is None:
            raise APIError(404, 'not_found', '资料不存在或不在授权范围。')
        return row

    def revision(self, user, did, rid):
        doc = self.document(user, did)
        row = self.repo(doc['kb_id']).get_revision(rid)
        if row['document_id'] != did:
            raise APIError(404, 'not_found', '修订不属于此资料。')
        return row

    def product(self, user, pid, kb):
        require_kb(user, kb)
        found = self.product_kbs.find_one({'owner_id': self.owner_id, 'kb_id': kb, 'product_id': pid})
        if found is None:
            raise APIError(404, 'not_found', '产品不存在或不在授权范围。')
        return found

    def add_product(self, user, kb, data):
        require_kb(user, kb)
        product = Product(owner_id=self.owner_id, model=data.model, brand=data.brand, series=data.series, aliases=tuple(data.aliases))
        self.products.register(product)
        self.product_kbs.insert_one({'owner_id': self.owner_id, 'kb_id': kb, 'product_id': product.product_id})
        return product.model_dump(mode='json')

    def index(self):
        if self.index_factory is None:
            raise APIError(503, 'configuration_missing', '请在根目录.env填写M2_MILVUS_COLLECTION和MILVUS_URL，用于修订索引与发布。')
        return self.index_factory()

    def publisher(self, kb):
        from app.knowledge.assets import AssetStore
        assets = AssetStore(self.db, self.originals.client, bucket=self.originals.bucket, prefix=self.originals.prefix + 'assets/')
        return RevisionPublisher(self.repo(kb), self.index(), read_original=self.originals.read, asset_store=assets)
