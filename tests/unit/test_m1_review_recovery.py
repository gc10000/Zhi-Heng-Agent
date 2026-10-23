"""恢复审查反例：快照自包含，拒绝路径三存储零写入。"""
import copy
from io import BytesIO
from types import SimpleNamespace
import pytest
from app.knowledge.models import content_hash
from app.knowledge.repository import fingerprint
from app.knowledge.migration import backup_selection, restore_sample


class Mongo:
    def __init__(self, name, docs=()):
        self.database = SimpleNamespace(name=name)
        self.name = 'legacy'
        self.docs = copy.deepcopy(list(docs))
        self.writes = 0

    def find_one(self, query):
        return next((d for d in self.docs if all(d.get(k) == v for k, v in query.items())), None)

    def count_documents(self, query):
        return len(self.docs)

    def find(self, query):
        return self.docs

    def insert_many(self, docs):
        self.writes += 1
        self.docs.extend(copy.deepcopy(docs))


class Objects:
    def __init__(self, values):
        self.values = dict(values)
        self.writes = 0

    def get_object(self, bucket, key):
        stream = BytesIO(self.values[bucket, key])
        stream.release_conn = lambda: None
        return stream

    def list_objects(self, bucket, prefix, recursive=True):
        return iter(SimpleNamespace(object_name=key) for b, key in self.values if b == bucket and key.startswith(prefix))

    def put_object(self, bucket, key, data, length):
        self.writes += 1
        self.values[bucket, key] = data.read()


class Milvus:
    def __init__(self):
        from pymilvus import DataType
        self.schema = {'auto_id': False, 'enable_dynamic_field': True, 'fields': [
            {'name': 'chunk_id', 'type': DataType.INT64, 'is_primary': True, 'params': {}},
            {'name': 'dense_vector', 'type': DataType.FLOAT_VECTOR, 'params': {'dim': 2}},
            {'name': 'sparse_vector', 'type': DataType.SPARSE_FLOAT_VECTOR, 'params': {}},
            {'name': 'label', 'type': DataType.VARCHAR, 'nullable': True, 'params': {'max_length': 80}},
        ]}
        self.indexes = [
            {'field_name': 'dense_vector', 'index_name': 'dense_idx', 'index_type': 'FLAT', 'metric_type': 'L2', 'params': {}},
            {'field_name': 'sparse_vector', 'index_name': 'sparse_idx', 'index_type': 'SPARSE_INVERTED_INDEX', 'metric_type': 'IP', 'params': {}},
        ]
        self.rows = {'source': [{'chunk_id': 1, 'dense_vector': [0.1, 0.2], 'sparse_vector': {2: 0.5},
                                 'label': '业务字段', 'extra': {'source_ref': 'A3'}}]}
        self.block_source = False
        self.writes = 0
        self.created = None

    def guard(self, name):
        if self.block_source and name == 'source':
            raise RuntimeError('合成源服务不可用')

    def describe_collection(self, name):
        self.guard(name)
        return copy.deepcopy(self.schema)

    def list_indexes(self, name):
        self.guard(name)
        return [i['index_name'] for i in self.indexes]

    def describe_index(self, name, index_name):
        self.guard(name)
        return copy.deepcopy(next(i for i in self.indexes if i['index_name'] == index_name))

    def get(self, collection_name, **kwargs):
        self.guard(collection_name)
        return copy.deepcopy(self.rows[collection_name])

    def has_collection(self, name):
        self.guard(name)
        return name in self.rows

    def create_schema(self, **kwargs):
        from pymilvus import MilvusClient
        return MilvusClient.create_schema(**kwargs)

    def prepare_index_params(self):
        from pymilvus import MilvusClient
        return MilvusClient.prepare_index_params()

    def create_collection(self, **kwargs):
        self.writes += 1
        self.created = kwargs
        self.rows[kwargs['collection_name']] = []

    def insert(self, collection_name, data):
        self.writes += 1
        self.rows[collection_name].extend(copy.deepcopy(data))

    def flush(self, name):
        self.writes += 1


@pytest.fixture
def recovery_case(tmp_path):
    raw = b'independent original'
    digest = content_hash(raw)
    key = 'm1-test/source/' + digest
    records = [{'source_id': 's', 'name': 'sample', 'original_key': key, 'original_sha256': digest, 'chunk_ids': ['1']}]
    source = Mongo('m1_test_source', records)
    objects = Objects({('bucket', key): raw})
    milvus = Milvus()
    snapshot = backup_selection(records, mongo_collection=source, milvus=milvus, collection='source',
                                objects=objects, bucket='bucket', directory=tmp_path, active_snapshot=[])
    return SimpleNamespace(snapshot=snapshot, directory=tmp_path, mongo=Mongo('m1_test_target'), milvus=milvus, objects=objects)


def restore(case, prefix='m1-test/new/', bucket='bucket'):
    return restore_sample(case.snapshot, directory=case.directory, mongo_collection=case.mongo, milvus=case.milvus,
                          index='m1_test_restore', objects=case.objects, bucket=bucket, prefix=prefix)


def test_backup_contains_hashed_schema_and_index_metadata(recovery_case):
    case = recovery_case
    assert case.snapshot['version'] == 2
    assert case.snapshot['milvus_schema'] == case.milvus.schema
    assert case.snapshot['milvus_indexes'] == case.milvus.indexes
    case.snapshot['milvus_schema']['enable_dynamic_field'] = False
    with pytest.raises(ValueError, match='hash'):
        restore(case)
    assert (case.mongo.writes, case.milvus.writes, case.objects.writes) == (0, 0, 0)


def test_restore_never_reads_source_and_preserves_dynamic_fields_and_indexes(recovery_case):
    case = recovery_case
    case.milvus.block_source = True
    # 源对象和Mongo同样不再可读；本地blobs是唯一恢复来源。
    case.objects.values.clear()
    report = restore(case)
    assert report['verified'] and report['vectors'] == 1
    assert case.milvus.rows['m1_test_restore'] == case.milvus.rows['source']
    schema = case.milvus.created['schema'].to_dict()
    assert schema['enable_dynamic_field'] is True
    assert next(f for f in schema['fields'] if f['name'] == 'label')['nullable'] is True
    indexes = case.milvus.created['index_params']
    assert next(i.to_dict() for i in indexes if i.index_name == 'dense_idx')['metric_type'] == 'L2'


@pytest.mark.parametrize('conflict', ['same-key', 'existing-key', 'nonempty-prefix', 'nested-source', 'parent-source', 'alias-dot', 'alias-slash', 'mongo', 'milvus'])
def test_restore_conflicts_are_rejected_before_any_storage_write(recovery_case, conflict):
    case = recovery_case
    prefix = 'm1-test/new/'
    digest = case.snapshot['objects'][0]['sha256']
    if conflict == 'same-key':
        prefix = 'm1-test/source/'
    elif conflict == 'nested-source':
        prefix = 'm1-test/source/child/'
    elif conflict == 'parent-source':
        prefix = 'm1-test/'
    elif conflict == 'existing-key':
        case.objects.values['bucket', prefix + digest] = b'different data'
    elif conflict == 'nonempty-prefix':
        case.objects.values['bucket', prefix + 'unrelated'] = b'existing'
    elif conflict == 'alias-dot':
        prefix = 'm1-test/source/../source/'
    elif conflict == 'alias-slash':
        prefix = 'm1-test//source/'
    elif conflict == 'mongo':
        case.mongo.docs.append({'existing': 1})
    elif conflict == 'milvus':
        case.milvus.rows['m1_test_restore'] = []
    with pytest.raises(ValueError):
        restore(case, prefix)
    assert (case.mongo.writes, case.milvus.writes, case.objects.writes) == (0, 0, 0)


def test_restore_reused_prefix_is_rejected_without_additional_writes(recovery_case):
    case = recovery_case
    assert restore(case)['verified']
    previous = case.objects.writes
    case.mongo = Mongo('m1_test_second')
    case.milvus.rows.pop('m1_test_restore')  # 只修改fake，模拟另一独立存储目标。
    case.milvus.writes = 0
    with pytest.raises(ValueError):
        restore(case)
    assert (case.mongo.writes, case.milvus.writes, case.objects.writes) == (0, 0, previous)


def test_old_snapshot_missing_schema_is_rejected_before_writes(recovery_case):
    case = recovery_case
    case.snapshot['version'] = 1
    case.snapshot.pop('milvus_schema', None)
    case.snapshot.pop('milvus_indexes', None)
    case.snapshot['snapshot_sha256'] = fingerprint({k: v for k, v in case.snapshot.items() if k != 'snapshot_sha256'})
    with pytest.raises(ValueError, match='schema|版本'):
        restore(case)
    assert (case.mongo.writes, case.milvus.writes, case.objects.writes) == (0, 0, 0)
