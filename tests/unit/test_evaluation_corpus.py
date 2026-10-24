"""冻结基线必须发现活动指针不变但正文、向量、图片或产品已变化。"""
import copy
import hashlib
import json
from types import SimpleNamespace
from contextlib import contextmanager
import pytest

from app.evaluation.query_adapter import RealQueryExecutor


@pytest.fixture
def corpus_context():
    config = {'strategy': 'm3-baseline', 'target': {'database': 'm1_test_m4_corpus',
        'collection': 'm1_test_m4_corpus_v2', 'owner_id': 'm4-test-owner', 'kb_id': 'm4-test-kb',
        'object_prefix': 'm4-test/corpus/', 'bucket': 'existing'},
        'corpus': {'documents': [{'document_id': 'doc', 'revision_id': 'rev',
            'original_sha256': hashlib.sha256(b'original').hexdigest()}],
            'snapshot': {'format': 'm4-corpus-1', 'documents': [], 'products': []}}}
    revision = {'revision_id': 'rev', 'status': 'published', 'original_sha256': hashlib.sha256(b'original').hexdigest()}
    original = {'raw': b'original'}
    row = {'chunk_uid': 'chunk', 'owner_id': 'm4-test-owner', 'kb_id': 'm4-test-kb',
        'document_id': 'doc', 'revision_id': 'rev', 'ordinal': 0, 'text': '额定电压24V',
        'metadata': {'asset_ids': [], 'source_refs': [{'kind': 'pdf', 'page': 1}]},
        'content_sha256': hashlib.sha256('额定电压24V'.encode()).hexdigest(),
        'dense_vector': [1., 0.], 'sparse_vector': {3: .5}}
    products = [{'product_id': 'product', 'model': 'AX', 'owner_id': 'm4-test-owner'}]
    class Rows:
        def find(self, *a, **kw): return copy.deepcopy(products)
        def distinct(self, *a, **kw): return ['product']
    repo = SimpleNamespace(get_revision=lambda rid: revision,
        get_active_revisions=lambda: [{'document_id': 'doc', 'active_revision_id': 'rev'}])
    from app.knowledge.index import V2Index
    index = SimpleNamespace(collection='m1_test_m4_corpus_v2', payload=V2Index.payload,
        revision_rows=lambda *a, **kw: [copy.deepcopy(row)])
    def digest(value):
        return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    config['corpus']['snapshot'] = {'format': 'm4-corpus-1', 'collection': index.collection,
        'documents': [{'document_id': 'doc', 'revision_id': 'rev', 'original_sha256': revision['original_sha256'],
            'chunks': [{'chunk_uid': 'chunk', 'payload_sha256': digest(V2Index.payload(row)),
                        'vectors_sha256': digest({'dense': [1., 0.], 'sparse': {'3': .5}})}], 'assets': []}],
        'products': copy.deepcopy(products)}
    g = SimpleNamespace(repo=lambda kb: repo, owner_id='m4-test-owner',
        index=lambda: index, originals=SimpleNamespace(read=lambda r: original['raw']),
        products=SimpleNamespace(collection=Rows()), product_kbs=Rows())
    @contextmanager
    def resources(cfg): yield {'knowledge': lambda: g}
    executor = RealQueryExecutor(config, resource_factory=resources)
    executor.resources = {'knowledge': lambda: g}
    return executor, row, original, revision, products


@pytest.mark.parametrize('mutate', [
    lambda row, raw, rev, products: row.update(text='误改为220V'),
    lambda row, raw, rev, products: row['metadata'].update(asset_ids=['wrong-image']),
    lambda row, raw, rev, products: row.update(dense_vector=[0., 1.]),
    lambda row, raw, rev, products: row.update(sparse_vector={4: .9}),
    lambda row, raw, rev, products: raw.update(raw=b'corrupted-original'),
    lambda row, raw, rev, products: products[0].update(model='wrong-product'),
])
def test_corpus_mutation_rejected_before_creating_or_resuming_run(corpus_context, mutate):
    executor, row, raw, revision, products = corpus_context
    executor.check_corpus()
    mutate(row, raw, revision, products)
    with pytest.raises(ValueError): executor.check_corpus()


def test_normal_cli_adapter_requires_complete_corpus_freeze_before_resources():
    cfg = {'strategy': 'm3-baseline', 'corpus': {'documents': []}, 'target': {
        'database': 'm1_test_m4_corpus', 'collection': 'm1_test_m4_corpus_v2',
        'owner_id': 'm4-test-owner', 'kb_id': 'm4-test-kb',
        'object_prefix': 'm4-test/corpus/', 'bucket': 'existing'}}
    with pytest.raises(ValueError): RealQueryExecutor(cfg)


def test_real_adapter_requires_frozen_dataset_acceptance_before_resources(corpus_context):
    executor, *_ = corpus_context
    with pytest.raises(ValueError): RealQueryExecutor(executor.config)


def test_real_adapter_rejects_changed_acceptance_artifact_before_resources(corpus_context, tmp_path):
    executor, *_ = corpus_context
    path = tmp_path / 'review.json'; path.write_text('accepted', encoding='utf-8')
    cfg = copy.deepcopy(executor.config)
    cfg['dataset_acceptance'] = [{'path': str(path), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}]
    RealQueryExecutor(cfg)
    path.write_text('changed', encoding='utf-8')
    with pytest.raises(ValueError): RealQueryExecutor(cfg)


@pytest.fixture
def image_context(corpus_context, tmp_path):
    from io import BytesIO
    from PIL import Image
    from app.evaluation.corpus import corpus_snapshot
    executor, row, *_ = corpus_context
    gateway = executor.resources['knowledge']()
    image = BytesIO(); Image.new('RGB', (3, 2), 'blue').save(image, format='PNG')
    image_bytes = {'value': image.getvalue()}
    digest = hashlib.sha256(image_bytes['value']).hexdigest()
    asset = {'asset_id': 'image', 'document_id': 'doc', 'revision_id': 'rev',
        'object_key': 'm4-test/corpus/assets/image', 'sha256': digest, 'media_type': 'image/png',
        'source_refs': [{'kind': 'pdf', 'page': 1}], 'description_status': 'completed',
        'description': '蓝色合成图', 'description_cache_key': 'cache'}
    class Assets:
        def find_one(self, query):
            assert query == {'asset_id': 'image'}
            return copy.deepcopy(asset)
    def get(key, expected):
        assert key == asset['object_key']
        if hashlib.sha256(image_bytes['value']).hexdigest() != expected:
            raise ValueError('对象指纹不一致')
        return image_bytes['value']
    gateway.db = SimpleNamespace(knowledge_assets=Assets())
    gateway.originals.get = get
    row['metadata']['asset_ids'] = ['image']
    executor.config['corpus']['snapshot'] = corpus_snapshot(gateway, executor.config['target'],
        executor.config['corpus']['documents'])
    comparison = tmp_path / 'comparison.png'; comparison.write_bytes(image_bytes['value'])
    expected = tmp_path / 'expected.png'; expected.write_bytes(image_bytes['value'])
    mapping = {'document_sha256': executor.config['corpus']['documents'][0]['original_sha256'],
        'asset_sha256': digest, 'expected_asset_sha256': digest, 'page': 1,
        'method': 'original_page_visual_comparison', 'reviewer': 'synthetic-reviewer',
        'comparison_path': str(comparison), 'comparison_sha256': digest, 'expected_path': str(expected)}
    executor.config['corpus']['asset_equivalences'] = [mapping]
    executor.check_corpus()
    return executor, asset, image_bytes, comparison, expected


@pytest.mark.parametrize('field,value', [
    ('description', '被替换的摘要'), ('description_cache_key', 'other-cache'),
    ('document_id', 'other-doc'), ('revision_id', 'other-rev'),
    ('object_key', 'course/assets/source'), ('description_status', 'failed'),
    ('source_refs', [{'kind': 'pdf', 'page': 2}]),
])
def test_asset_change_rejected_before_run(image_context, field, value):
    executor, asset, *_ = image_context
    asset[field] = value
    with pytest.raises(ValueError): executor.check_corpus()


def test_corrupt_asset_bytes_rejected(image_context):
    executor, _, raw, *_ = image_context
    raw['value'] = b'corrupt'
    with pytest.raises(ValueError): executor.check_corpus()


@pytest.mark.parametrize('position', [3, 4])
def test_changed_visual_comparison_evidence_rejected(image_context, position):
    executor = image_context[0]
    image_context[position].write_bytes(b'replaced')
    with pytest.raises(ValueError): executor.check_corpus()


@pytest.mark.parametrize('field,value', [('page', 2), ('reviewer', ''), ('method', 'same_page_guess')])
def test_invalid_asset_correspondence_rejected(image_context, field, value):
    executor = image_context[0]
    executor.config['corpus']['asset_equivalences'][0][field] = value
    with pytest.raises(ValueError): executor.check_corpus()
