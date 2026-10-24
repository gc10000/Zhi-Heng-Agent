"""真实评测语料的只读完整快照；不从题集答案构造任何正文。"""
from .validate_dataset import file_sha, fingerprint
from app.knowledge.models import content_hash


def vector_fingerprint(row):
    return fingerprint({'dense': [float(v) for v in row['dense_vector']],
                        'sparse': {str(int(k)): float(v) for k, v in row['sparse_vector'].items()}})


def corpus_snapshot(gateway, target, documents, *, expected=None):
    """读取原件/索引完整载荷与向量/图片字节；每个范围均显式限定。"""
    repo = gateway.repo(target['kb_id'])
    index = gateway.index()
    if index.collection != target['collection']:
        raise ValueError('语料快照集合与独立目标不一致')
    frozen = []
    for item in sorted(documents, key=lambda d: d['document_id']):
        revision = repo.get_revision(item['revision_id'])
        digest = content_hash(gateway.originals.read(revision))
        if digest != item['original_sha256']:
            raise ValueError('语料原件字节与冻结指纹不一致')
        rows = index.revision_rows(repo, item['revision_id'], vectors=True)
        if not rows or len({r['chunk_uid'] for r in rows}) != len(rows):
            raise ValueError('语料索引为空或存在重复身份')
        chunks, asset_ids = [], set()
        for row in sorted(rows, key=lambda r: r['chunk_uid']):
            if row['document_id'] != item['document_id'] or row['revision_id'] != item['revision_id']:
                raise ValueError('语料切片超出冻结资料或修订')
            if row['owner_id'] != target['owner_id'] or row['kb_id'] != target['kb_id']:
                raise ValueError('语料索引归属不一致')
            chunks.append({'chunk_uid': row['chunk_uid'], 'payload_sha256': fingerprint(index.payload(row)),
                           'vectors_sha256': vector_fingerprint(row)})
            asset_ids.update(row['metadata'].get('asset_ids', []))
            asset_ids.update(r['asset_id'] for r in row['metadata'].get('source_refs', []) if r.get('asset_id'))
        if expected is not None:
            prior = next((d for d in expected['documents'] if d['document_id'] == item['document_id']), None)
            if prior is None or prior['chunks'] != chunks:
                raise ValueError('语料切片完整载荷或向量与冻结快照不一致')
        assets = []
        if asset_ids:
            for aid in sorted(asset_ids):
                asset = gateway.db.knowledge_assets.find_one({'asset_id': aid})
                if (asset is None or asset['document_id'] != item['document_id'] or asset['revision_id'] != item['revision_id']
                        or not asset['object_key'].startswith(target['object_prefix'] + 'assets/')):
                    raise ValueError('语料图片归属或对象前缀不一致')
                raw = gateway.originals.get(asset['object_key'], asset['sha256'])
                if asset['description_status'] not in {'completed', 'not_required'}:
                    raise ValueError('语料图片摘要未就绪')
                from io import BytesIO
                from PIL import Image
                with Image.open(BytesIO(raw)) as image: image.verify()
                with Image.open(BytesIO(raw)) as image: image.load()
                assets.append({k: asset.get(k) for k in ('asset_id', 'document_id', 'revision_id', 'sha256',
                    'object_key', 'media_type', 'source_refs', 'description_status', 'description_cache_key')} |
                    {'description_sha256': content_hash((asset.get('description') or '').encode())})
        frozen.append({'document_id': item['document_id'], 'revision_id': item['revision_id'],
                       'original_sha256': digest, 'chunks': chunks, 'assets': assets})
    pids = gateway.product_kbs.distinct('product_id', {'owner_id': gateway.owner_id, 'kb_id': target['kb_id']})
    products = [{k: v for k, v in p.items() if k != '_id'} for p in
                gateway.products.collection.find({'owner_id': gateway.owner_id, 'product_id': {'$in': pids}})]
    return {'format': 'm4-corpus-1', 'collection': index.collection, 'documents': frozen,
            'products': sorted(products, key=lambda p: p['product_id'])}


def validate_asset_equivalences(snapshot, mappings):
    """只接受目视比对后、绑定两端字节与相同物理页的精确图像对应。"""
    assets = {(d['original_sha256'], a['sha256'], ref['page'])
              for d in snapshot['documents'] for a in d['assets']
              for ref in a['source_refs'] if ref.get('page')}
    seen = set()
    for mapping in mappings:
        key = (mapping['document_sha256'], mapping['asset_sha256'], mapping['page'])
        if key not in assets or key in seen or mapping.get('method') != 'original_page_visual_comparison':
            raise ValueError('图像对应不属于冻结语料、重复或缺少原件目视核对')
        if not mapping.get('reviewer') or file_sha(mapping['comparison_path']) != mapping['comparison_sha256']:
            raise ValueError('图像对应缺少真实核对人或比对证据不符')
        if file_sha(mapping['expected_path']) != mapping['expected_asset_sha256']:
            raise ValueError('预期原图裁图指纹不一致')
        seen.add(key)
