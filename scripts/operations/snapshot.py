"""隔离命名空间的跨存储快照；源只读，目标拒绝覆盖，失败保留现场。

当前交付仅放行m1_test_m4_小样，不将本机演练冒称生产热备。备份期间必须停写；
前后双读拒绝变化，不能替代跨Mongo/对象/向量的分布式事务。
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

from bson import json_util

VERSION = 'zhi_heng_backup_v1'
EPHEMERAL = {'login_sessions', 'login_attempts', 'm7_restore_control'}
LIMIT = 10000


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json_util.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


@dataclass(frozen=True)
class Namespace:
    database: str
    bucket: str
    collection: str
    prefix: str

    def __post_init__(self):
        if not re.fullmatch(r'm1_test_m4_[a-z0-9_]{1,45}', self.database):
            raise ValueError('本轮只允许随机m1_test_m4_隔离数据库')
        if not re.fullmatch(r'zh-(?:preview|restore)-[a-z0-9-]{2,40}', self.bucket):
            raise ValueError('本轮只允许独立预览或恢复桶')
        if not re.fullmatch(r'm1_test_m4_[a-z0-9_]{1,60}', self.collection):
            raise ValueError('本轮只允许独立测试向量集合')
        if not self.prefix or not self.prefix.endswith('/') or any(x in self.prefix for x in ('..', '\\', ':', '//', '%')) or self.prefix.startswith('/'):
            raise ValueError('对象前缀非法')


def validate_target(source, target):
    if any(getattr(source, field) == getattr(target, field) for field in ('database', 'bucket', 'collection')):
        raise ValueError('恢复必须分别使用新的数据库、桶和集合，禁止覆盖源')
    if target.prefix != source.prefix:
        raise ValueError('保留对象键，命名空间迁移只更换独立桶')


def validate_files(directory, manifest):
    directory = Path(directory).resolve()
    for name, expected in manifest['files'].items():
        p = PurePosixPath(name)
        if not name or p.is_absolute() or any(x in name for x in ('..', '\\', ':', '%')):
            raise ValueError('备份清单路径非法')
        path = directory / name
        if not path.resolve().is_relative_to(directory) or path.is_symlink():
            raise ValueError('备份路径越界')
        if digest(path.read_bytes()) != expected:
            raise ValueError('备份文件hash不匹配')


def mongo_dump(db):
    result = {}
    for name in sorted(db.list_collection_names()):
        if name in EPHEMERAL or name.startswith('system.'):
            continue
        rows = list(db[name].find().limit(LIMIT + 1))
        if len(rows) > LIMIT:
            raise ValueError('演练清单超过小样上限，拒绝截断')
        rows.sort(key=canonical)
        # BSON复合索引的字段顺序有语义，不能作为sort_keys JSON中的普通字典保存。
        indexes = [dict(spec) | {'key': list(spec['key'].items())} for spec in db[name].list_indexes()]
        options = db[name].options()
        if set(options) - {'validator', 'validationLevel', 'validationAction', 'collation'}:
            raise ValueError('当前恢复不支持该集合选项')
        result[name] = dict(rows=rows, indexes=indexes, options=options)
    return result


def vector_dump(client, collection):
    rows = []
    iterator = client.query_iterator(collection_name=collection, filter='', batch_size=256, output_fields=['*'], consistency_level='Strong')
    try:
        while batch := iterator.next():
            rows.extend(batch)
            if len(rows) > LIMIT:
                raise ValueError('向量超过小样上限，拒绝截断')
    finally:
        iterator.close()
    rows.sort(key=lambda row: row['chunk_uid'])
    return rows


def registry_check(data, vectors):
    revisions = {r['revision_id']: r for r in data.get('knowledge_revisions', {}).get('rows', [])}
    for doc in data.get('knowledge_documents', {}).get('rows', []):
        if doc.get('active_revision_id'):
            revision = revisions.get(doc['active_revision_id'])
            if not revision or any(revision[k] != doc[k] for k in ('document_id', 'owner_id', 'kb_id')):
                raise ValueError('活动修订或权限关系损坏')
    from app.knowledge.index import V2Index
    for row in vectors:
        revision = revisions.get(row['revision_id'])
        if not revision or any(row[k] != revision[k] for k in ('document_id', 'owner_id', 'kb_id')):
            raise ValueError('向量超出登记修订或权限')
        if digest(row['text'].encode()) != row['content_sha256']:
            raise ValueError('向量正文hash不符')
        V2Index.validate_vectors(row['dense_vector'], row['sparse_vector'], len(row['dense_vector']))


def backup(directory, source, mongo, objects, vectors, *, source_commit):
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    files = {}
    def write(name, data):
        p = directory / name
        p.parent.mkdir(parents=True, exist_ok=True)
        with p.open('xb') as stream:
            stream.write(data)
        p.chmod(0o600)
        files[name] = digest(data)
    db = mongo[source.database]
    data = mongo_dump(db)
    rows = vector_dump(vectors, source.collection)
    registry_check(data, rows)
    description = vectors.describe_collection(source.collection)
    dimension = int(next(f for f in description['fields'] if f['name'] == 'dense_vector')['params']['dim'])
    from minio.error import S3Error
    try:
        policy = objects.get_bucket_policy(source.bucket)
    except S3Error as error:
        if error.code != 'NoSuchBucketPolicy':
            raise
        policy = None
    if policy:
        raise ValueError('演练仅支持私有桶，不隐式复制公开策略')
    write('mongo.json', canonical(data))
    write('vectors.json', canonical(rows))
    stored = []
    listed = list(objects.list_objects(source.bucket, prefix=source.prefix, recursive=True))
    if len(listed) > LIMIT:
        raise ValueError('对象超过小样上限')
    for item in listed:
        if item.size > 50_000_000:
            raise ValueError('对象超过演练字节上限')
        response = objects.get_object(source.bucket, item.object_name)
        try:
            raw = response.read()
        finally:
            response.close()
            response.release_conn()
        h = digest(raw)
        name = 'objects/' + h + '.bin'
        if name not in files:
            write(name, raw)
        stat = objects.stat_object(source.bucket, item.object_name)
        stored.append(dict(key=item.object_name, sha256=h, file=name, size=len(raw),
                           content_type=stat.content_type, version_id=stat.version_id, etag=stat.etag))
    object_hashes = {item['key']: item['sha256'] for item in stored}
    for revision in data.get('knowledge_revisions', {}).get('rows', []):
        if object_hashes.get(revision['object_key']) != revision['original_sha256']:
            raise ValueError('原件缺失或登记hash不符')
    # 必须停写；双读覆盖注册关系、权限和索引，变化时不生成完成清单。
    if canonical(mongo_dump(db)) != canonical(data) or canonical(vector_dump(vectors, source.collection)) != canonical(rows):
        raise ValueError('备份期间源变化，请停写后以新目录重做')
    latest = {item.object_name: item.etag for item in objects.list_objects(source.bucket, prefix=source.prefix, recursive=True)}
    if latest != {item['key']: item['etag'] for item in stored}:
        raise ValueError('备份期间对象变化')
    manifest = dict(version=VERSION, source=asdict(source), source_commit=source_commit,
                    created_at=datetime.now(timezone.utc).isoformat(), files=files, objects=stored,
                    dense_dimension=dimension, schema=description, private_bucket=True, index_key_format='ordered_pairs_v1',
                    excluded=sorted(EPHEMERAL), mongo_collections=len(data), vector_rows=len(rows))
    raw = canonical(manifest)
    with (directory / 'manifest.json').open('xb') as stream:
        stream.write(raw)
    return dict(manifest_sha256=digest(raw), collections=len(data), objects=len(stored), vectors=len(rows))


def remap_mongo(name, value, source, target):
    row = deepcopy(value)
    from app.knowledge.repository import fingerprint
    if name == 'knowledge_revisions':
        manifest = row.get('stages', {}).get('indexed')
        if manifest and manifest.get('collection') == source.collection:
            manifest['collection'] = target.collection
            if 'index_identity' in row:
                row['index_identity'] = fingerprint(dict(collection=target.collection, payload_hashes=manifest['payload_hashes']))
    if name == 'knowledge_chunk_claims':
        row['_id'] = fingerprint([target.collection, row.get('chunk_uid')]) if row.get('chunk_uid') else row['_id']
        # 旧claims不带uid；它们是写入并发护栏而非已发布来源，保留源记录用于审计，另在目标重建。
    if name in {'knowledge_assets', 'knowledge_legacy_assets', 'knowledge_original_assets'} and row.get('bucket') == source.bucket:
        row['bucket'] = target.bucket
    return row


def restore(directory, target, mongo, objects, vectors, *, expected_sha256):
    directory = Path(directory).resolve()
    raw = (directory / 'manifest.json').read_bytes()
    if digest(raw) != expected_sha256:
        raise ValueError('顶层清单hash不符')
    manifest = json_util.loads(raw)
    if manifest['version'] != VERSION or not manifest.get('private_bucket') or manifest.get('index_key_format') != 'ordered_pairs_v1':
        raise ValueError('清单版本或桶权限不支持')
    source = Namespace(**manifest['source'])
    validate_target(source, target)
    validate_files(directory, manifest)
    if not {'mongo.json', 'vectors.json'} <= manifest['files'].keys():
        raise ValueError('缺少完整数据库或向量文件')
    seen_keys = set()
    for item in manifest['objects']:
        if (item['file'] not in manifest['files'] or item['sha256'] != manifest['files'][item['file']]
                or not item['key'].startswith(source.prefix) or item['key'] in seen_keys
                or any(x in item['key'] for x in ('..', '\\', ':', '%', '//'))):
            raise ValueError('对象清单路径、hash或唯一性不符')
        seen_keys.add(item['key'])
    data = json_util.loads((directory / 'mongo.json').read_bytes())
    rows = json_util.loads((directory / 'vectors.json').read_bytes())
    for value in data.values():
        for spec in value['indexes']:
            pairs = spec.get('key')
            if (not isinstance(pairs, list) or not pairs or any(not isinstance(p, list) or len(p) != 2 or not isinstance(p[0], str) for p in pairs)
                    or len({p[0] for p in pairs}) != len(pairs)):
                raise ValueError('复合索引必须保留有序键对')
    registry_check(data, rows)
    object_hashes = {item['key']: item['sha256'] for item in manifest['objects']}
    for revision in data.get('knowledge_revisions', {}).get('rows', []):
        if object_hashes.get(revision['object_key']) != revision['original_sha256']:
            raise ValueError('恢复清单缺少精确原件')
    if mongo[target.database].list_collection_names() or objects.bucket_exists(target.bucket) or vectors.has_collection(target.collection):
        raise ValueError('恢复目标已存在，拒绝覆盖或自动继续')
    db = mongo[target.database]
    # 原子预留，失败保留控制记录与部分产物；不能删除锁或改状态来复用目标。
    db.m7_restore_control.insert_one({'_id': 'exclusive', 'manifest_sha256': expected_sha256, 'state': 'started'})
    try:
        objects.make_bucket(target.bucket)
        from io import BytesIO
        for item in manifest['objects']:
            if not item['key'].startswith(target.prefix):
                raise ValueError('对象越界')
            content = (directory / item['file']).read_bytes()
            objects.put_object(target.bucket, item['key'], BytesIO(content), len(content), content_type=item['content_type'])
        from app.knowledge.index import V2Index
        index = V2Index(vectors, target.collection, dense_dim=manifest['dense_dimension'])
        index.ensure_collection()
        for i in range(0, len(rows), 64):
            vectors.upsert(collection_name=target.collection, data=rows[i:i + 64])
        vectors.flush(target.collection)
        for name, value in data.items():
            if name in EPHEMERAL or name.startswith('system.'):
                raise ValueError('不允许恢复会话或内部集合')
            collection = db.create_collection(name, **value['options'])
            changed = [remap_mongo(name, row, source, target) for row in value['rows']]
            if changed:
                collection.insert_many(changed)
            for spec in value['indexes']:
                if spec['name'] == '_id_':
                    continue
                allowed = {'name', 'unique', 'sparse', 'expireAfterSeconds', 'partialFilterExpression', 'collation', 'wildcardProjection'}
                collection.create_index([tuple(pair) for pair in spec['key']], **{k: v for k, v in spec.items() if k in allowed})
            if canonical(sorted(collection.find(), key=canonical)) != canonical(sorted(changed, key=canonical)):
                raise ValueError('Mongo恢复读回不一致')
        restored_rows = vector_dump(vectors, target.collection)
        if canonical(restored_rows) != canonical(rows):
            raise ValueError('向量恢复读回不一致')
        from app.knowledge.repository import fingerprint
        for row in restored_rows:
            db.knowledge_chunk_claims.update_one({'_id': fingerprint([target.collection, row['chunk_uid']])},
                {'$setOnInsert': {'request_fingerprint': fingerprint(V2Index.payload(row)), 'revision_id': row['revision_id']}}, upsert=True)
        for item in manifest['objects']:
            response = objects.get_object(target.bucket, item['key'])
            try:
                if digest(response.read()) != item['sha256']:
                    raise ValueError('对象恢复读回hash不符')
            finally:
                response.close()
                response.release_conn()
        registry_check(mongo_dump(db), restored_rows)
        receipt = dict(state='completed', manifest_sha256=expected_sha256, target=asdict(target),
                       collections=len(data), vectors=len(rows), objects=len(manifest['objects']),
                       sessions_restored=False, source_mutated=False)
        db.m7_restore_control.update_one({'_id': 'exclusive'}, {'$set': receipt})
        return receipt
    except Exception:
        db.m7_restore_control.update_one({'_id': 'exclusive'}, {'$set': {'state': 'failed'}})
        raise
