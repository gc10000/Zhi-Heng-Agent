"""为独立预览登记自制资料与合成向量；不生成答案，不加载模型。"""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


def seed(mongo, objects, vectors, scope):
    from app.identity.service import IdentityService, MongoIdentityStore
    from app.knowledge.originals import OriginalStore
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.models import content_hash
    from app.knowledge.index import V2Index
    from app.knowledge.asset_api import original_asset
    from app.knowledge.publishing import RevisionPublisher
    from app.ingestion.parsers.markdown import MarkdownParser
    from app.ingestion.stages.chunking import chunk_document
    from types import SimpleNamespace
    from app.products.repository import ProductRepository
    from app.products.models import Product

    if os.getenv('M7_GENERATION_ENABLED') != 'false':
        raise ValueError('演练初始化要求显式禁用真实生成')
    db = mongo[scope.database]
    if not objects.bucket_exists(scope.bucket):
        objects.make_bucket(scope.bucket)
    index = V2Index(vectors, scope.collection)
    index.ensure_collection()
    owner, kb = os.environ['M2_KNOWLEDGE_OWNER_ID'], 'preview-kb'
    identity = IdentityService(MongoIdentityStore(db))
    username = os.environ['M7_PREVIEW_USERNAME']
    if identity.store.user(username) is None:
        identity.add_user(username, os.environ['M7_PREVIEW_PASSWORD'], role='admin', kb_ids=[kb])
    product_id = 'm7-preview-selfauthored-device'
    ProductRepository(db, owner_id=owner).register(Product(product_id=product_id, owner_id=owner, model='ZH-DEMO-1'))
    db.knowledge_product_kbs.update_one({'owner_id': owner, 'kb_id': kb, 'product_id': product_id},
        {'$setOnInsert': {'owner_id': owner, 'kb_id': kb, 'product_id': product_id}}, upsert=True)
    repo = KnowledgeRepository(db, kb_id=kb, owner_id=owner)
    path = Path(__file__).resolve().parents[2] / 'examples/preview/manual.md'
    data = path.read_bytes()
    document = repo.register_document('m7-selfauthored-v1', name='知衡自制预览资料.md', product_ids=[product_id], purpose='technical')
    originals = OriginalStore(objects, bucket=scope.bucket, prefix=scope.prefix)
    key = originals.key(document.document_id, content_hash(data))
    originals.put(key, data, 'text/markdown')
    revision = repo.create_revision(document.document_id, 'm7-selfauthored-v1', original_sha256=content_hash(data),
                                    object_key=key, parser_version='markdown-2')
    original_asset(SimpleNamespace(db=db), repo.get_revision(revision.revision_id), media_type='text/markdown', name=path.name)
    if repo.get_document(document.document_id)['active_revision_id'] is None:
        attempt = repo.claim_attempt(revision.revision_id, expected_attempt=0)
        parsed = MarkdownParser(purpose='technical').parse(path, document_id=document.document_id, revision_id=revision.revision_id)
        chunks = chunk_document(parsed, default_product_ids=[product_id])
        def synthetic(texts):
            return {'dense': [[1.0] + [0.0] * 1023 for _ in texts], 'sparse': [{1: 1.0} for _ in texts]}
        index.write_revision(repo, revision.revision_id, chunks, attempt=attempt, embedder=synthetic)
        publisher = RevisionPublisher(repo, index, read_original=originals.read)
        publisher.validate(revision.revision_id, attempt=attempt)
        publisher.publish(revision.revision_id, expected_active=None)
    return dict(database=scope.database, kb_id=kb, document_id=document.document_id,
                revision_id=revision.revision_id, model_calls=0, vectors='synthetic_not_retrieval_quality',
                answers_created=0)


if __name__ == '__main__':
    from scripts.operations.connections import connections, namespace
    with connections() as clients:
        print(json.dumps(seed(*clients, namespace()), ensure_ascii=False))
