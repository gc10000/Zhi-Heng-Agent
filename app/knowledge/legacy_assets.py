"""旧图只按维护者显式对象清单映射，绝不按答案URL请求任意网络。"""
from io import BytesIO
from PIL import Image
from app.knowledge.models import content_hash, stable_id
from app.knowledge.repository import ConflictError
from app.identity.api import require_writer


def map_legacy_image(gateway, user, *, document_id, revision_id, bucket, object_key, expected_sha256):
    require_writer(user)
    gateway.revision(user, document_id, revision_id)
    if not bucket or not object_key or object_key.startswith('/') or any(p in object_key for p in ('..', '\\', '//', '%')):
        raise ValueError('旧图对象范围非法')
    response = gateway.originals.client.get_object(bucket, object_key)
    try:
        data = response.read()
    finally:
        response.close()
        response.release_conn()
    digest = content_hash(data)
    if digest != expected_sha256:
        raise ValueError('旧图对象hash与显式清单不符')
    with Image.open(BytesIO(data)) as image:
        media = Image.MIME[image.format]
        image.verify()
    with Image.open(BytesIO(data)) as image:
        image.load()
    aid = stable_id('legacy-asset', revision_id, [bucket, object_key, digest])
    item = {'asset_id': aid, 'document_id': document_id, 'revision_id': revision_id, 'bucket': bucket,
            'object_key': object_key, 'sha256': digest, 'media_type': media, 'kind': 'legacy'}
    gateway.db.knowledge_legacy_assets.update_one({'asset_id': aid}, {'$setOnInsert': item}, upsert=True)
    return aid
