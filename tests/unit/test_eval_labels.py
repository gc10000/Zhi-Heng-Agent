"""M6-01：稳定来源跨度与可审计标签版本。"""
import json
import hashlib
import importlib
import importlib.util

import pytest

from app.evaluation.validate_dataset import source_span_fingerprint, validate_dataset


def question_row(*, qid='m6-synthetic-001', split='dev', page=2, document='a' * 64,
                 question='合成验证：设备额定电压是多少？'):
    return {
        'id': qid,
        'category': 'parameter',
        'group_id': f'{qid}-group',
        'split': split,
        'question': question,
        'product_names': ['合成设备'],
        'history': [],
        'expected': {'behavior': 'answer', 'key_points': ['24 V'], 'forbidden_claims': []},
        'allowed_evidence': [[{'document_sha256': document, 'page': page, 'quote': '额定电压：24 V'}]],
        'source_scope': [document],
        'annotation': {'method': 'source_checked_assistant_draft', 'status': 'draft'},
    }


def evaluation_datasets():
    name = 'app.evaluation.datasets'
    spec = importlib.util.find_spec(name)
    assert spec is not None, 'M6-01 题集版本与跨度映射模块尚未实现'
    return importlib.import_module(name)


def test_dataset_accepts_stable_source_span_bound_to_exact_original_and_quote(tmp_path):
    row = question_row()
    quote_sha256 = hashlib.sha256('额定电压：24 V'.encode('utf-8')).hexdigest()
    row['allowed_evidence'][0][0]['source_span'] = {
        'span_id': source_span_fingerprint('a' * 64, 2, quote_sha256, kind='text'),
        'kind': 'text',
        'document_sha256': 'a' * 64,
        'page': 2,
        'quote': '额定电压：24 V',
        'quote_sha256': quote_sha256,
    }
    dataset = tmp_path / 'support-v2.jsonl'
    dataset.write_text(json.dumps(row, ensure_ascii=False) + '\n', encoding='utf-8')
    validated = validate_dataset(dataset, minimum=1)
    assert validated[0]['allowed_evidence'][0][0]['source_span']['quote_sha256'] == quote_sha256


def test_derived_span_does_not_invalidate_prior_semantic_review(tmp_path):
    from app.evaluation.validate_dataset import fingerprint

    row = question_row()
    row['annotation'] = {
        'method': 'independent_assistant_review', 'status': 'reviewed', 'reviewer': 'synthetic-reviewer',
        'review': {'artifact': 'docs/development/reviews/synthetic-dataset-review.md',
                   'artifact_sha256': 'b' * 64, 'commit': 'c' * 40,
                   'method': 'independent_source_audit',
                   'subject_sha256': fingerprint({key: value for key, value in row.items() if key != 'annotation'})}}
    row['allowed_evidence'][0][0]['source_span'] = {
        'span_id': 'b' * 64, 'kind': 'text', 'document_sha256': 'a' * 64, 'page': 2,
        'quote': '额定电压：24 V',
        'quote_sha256': hashlib.sha256('额定电压：24 V'.encode('utf-8')).hexdigest(),
    }
    row['allowed_evidence'][0][0]['source_span']['span_id'] = source_span_fingerprint(
        'a' * 64, 2, row['allowed_evidence'][0][0]['source_span']['quote_sha256'], kind='text')
    dataset = tmp_path / 'reviewed-with-derived-span.jsonl'
    dataset.write_text(json.dumps(row, ensure_ascii=False) + '\n', encoding='utf-8')
    assert validate_dataset(dataset, minimum=1)[0]['annotation']['status'] == 'reviewed'


def test_unreviewed_feedback_is_not_eligible_for_gold_scoring():
    # M6 将提供明确的标注资格判断；缺少此能力时必须失败，不能默认把草稿当真值。
    datasets = evaluation_datasets()
    eligibility = getattr(datasets, 'is_label_eligible', None)
    assert callable(eligibility), '题集必须公开标注资格门禁'
    assert eligibility(question_row()) is False


def test_label_revision_requires_reason_version_and_does_not_mutate_prior_label():
    datasets = evaluation_datasets()
    revise = getattr(datasets, 'revise_label', None)
    assert callable(revise), '题集必须提供带版本和理由的标签修订入口'
    original = question_row()
    revised, change = revise(
        original,
        changes={'expected': {'behavior': 'clarify', 'key_points': ['先确认型号'], 'forbidden_claims': []}},
        version='support-v2.1',
        reason='合成验证：测试标签变更必须可追溯',
    )
    assert original['expected']['behavior'] == 'answer'
    assert revised['expected']['behavior'] == 'clarify'
    assert change['version'] == 'support-v2.1'
    assert change['reason'] == '合成验证：测试标签变更必须可追溯'
    assert change['previous_label_sha256'] != change['current_label_sha256']


@pytest.mark.parametrize('missing', ['version', 'reason'])
def test_label_revision_refuses_missing_audit_metadata(missing):
    datasets = evaluation_datasets()
    revise = getattr(datasets, 'revise_label', None)
    assert callable(revise), '题集必须提供带版本和理由的标签修订入口'
    kwargs = {
        'changes': {'expected': {'behavior': 'clarify', 'key_points': ['先确认型号'], 'forbidden_claims': []}},
        'version': 'support-v2.1',
        'reason': '合成验证原因',
    }
    kwargs.pop(missing)
    with pytest.raises((TypeError, ValueError)):
        revise(question_row(), **kwargs)


def test_stable_span_maps_to_new_chunk_only_when_document_page_and_quote_match():
    datasets = evaluation_datasets()
    make_span = getattr(datasets, 'make_source_span', None)
    map_span = getattr(datasets, 'map_source_span_to_chunks', None)
    assert callable(make_span) and callable(map_span), '必须支持来源跨度重切片映射'
    evidence = {'document_sha256': 'a' * 64, 'page': 2, 'quote': '额定电压：24 V'}
    span = make_span(evidence)
    chunks = [{
        'document_sha256': 'a' * 64,
        'document_id': 'doc-1',
        'revision_id': 'revision-2',
        'chunk_uid': 'chunk-after-resplit',
        'text': '设备参数\n额定电压：24 V\n输入范围：20–28 V',
        'source_refs': [{'document_id': 'doc-1', 'revision_id': 'revision-2', 'kind': 'pdf', 'page': 2}],
    }]
    result = map_span(span, chunks)
    assert result['status'] == 'mapped'
    assert result['mapped_chunks'] == [{'document_id': 'doc-1', 'revision_id': 'revision-2', 'chunk_uid': 'chunk-after-resplit'}]

    wrong_source = [{**chunks[0], 'document_sha256': 'd' * 64}]
    assert map_span(span, wrong_source)['status'] == 'unmapped'
    wrong_page = [{**chunks[0], 'source_refs': [{**chunks[0]['source_refs'][0], 'page': 3}]}]
    assert map_span(span, wrong_page)['status'] == 'unmapped'
    wrong_quote = [{**chunks[0], 'text': '额定电流：24 A'}]
    assert map_span(span, wrong_quote)['status'] == 'unmapped'


def test_image_span_requires_exact_asset_hash_page_and_chunk_membership():
    datasets = evaluation_datasets()
    make_span = getattr(datasets, 'make_source_span', None)
    map_span = getattr(datasets, 'map_source_span_to_chunks', None)
    assert callable(make_span) and callable(map_span), '必须支持图示来源跨度映射'
    span = make_span({'document_sha256': 'a' * 64, 'page': 5, 'quote': '接线拓扑图', 'asset_sha256': 'b' * 64})
    chunks = [{
        'document_sha256': 'a' * 64,
        'document_id': 'doc-1',
        'revision_id': 'revision-2',
        'chunk_uid': 'diagram-chunk',
        'text': '接线拓扑图',
        'asset_ids': ['asset-1'],
        'source_refs': [{'document_id': 'doc-1', 'revision_id': 'revision-2', 'kind': 'pdf', 'page': 5}],
    }]
    assets = [{'asset_id': 'asset-1', 'document_id': 'doc-1', 'revision_id': 'revision-2',
               'sha256': 'b' * 64, 'source_refs': [{'page': 5}]}]
    assert map_span(span, chunks, assets=assets)['status'] == 'mapped'
    wrong_asset = [{**assets[0], 'sha256': 'c' * 64}]
    assert map_span(span, chunks, assets=wrong_asset)['status'] == 'unmapped'


def test_source_span_maps_to_real_m1_chunk_and_sourceref_models():
    from app.knowledge.models import Chunk, SourceRef

    datasets = evaluation_datasets()
    make_span = getattr(datasets, 'make_source_span', None)
    map_span = getattr(datasets, 'map_source_span_to_chunks', None)
    assert callable(make_span) and callable(map_span)
    span = make_span({'document_sha256': 'a' * 64, 'page': 2, 'quote': '额定电压：24 V'})
    chunk = Chunk(
        section_id='section-1', document_id='doc-1', revision_id='revision-2',
        chunk_uid='chunk-1', ordinal=0, text='设备参数：额定电压：24 V',
        source_refs=(SourceRef(document_id='doc-1', revision_id='revision-2', kind='pdf', page=2),),
    )

    result = map_span(span, [chunk], revision_sha256={('doc-1', 'revision-2'): 'a' * 64})

    assert result['status'] == 'mapped'
    assert result['mapped_chunks'] == [{'document_id': 'doc-1', 'revision_id': 'revision-2', 'chunk_uid': 'chunk-1'}]
    assert map_span(span, [chunk], revision_sha256={('doc-1', 'revision-2'): 'c' * 64})['status'] == 'unmapped'


def test_source_span_maps_quote_split_across_rechunked_m1_children():
    from app.knowledge.models import Chunk, SourceRef

    datasets = evaluation_datasets()
    span = datasets.make_source_span(
        {'document_sha256': 'a' * 64, 'page': 2, 'quote': '额定电压：24 V'})
    ref = SourceRef(document_id='doc-1', revision_id='revision-2', kind='pdf', page=2)
    chunks = [
        Chunk(section_id='section-1', document_id='doc-1', revision_id='revision-2',
              chunk_uid='chunk-root', ordinal=0, text='设备参数：额定电压：', source_refs=(ref,)),
        Chunk(section_id='section-1', document_id='doc-1', revision_id='revision-2',
              chunk_uid='chunk-child', parent_chunk_uid='chunk-root', ordinal=1,
              text='24 V', source_refs=(ref,)),
    ]

    result = datasets.map_source_span_to_chunks(
        span, chunks, revision_sha256={('doc-1', 'revision-2'): 'a' * 64})

    assert result['status'] == 'mapped'
    assert result['mapped_chunks'] == [
        {'document_id': 'doc-1', 'revision_id': 'revision-2', 'chunk_uid': 'chunk-child'},
        {'document_id': 'doc-1', 'revision_id': 'revision-2', 'chunk_uid': 'chunk-root'},
    ]


def test_split_quote_maps_only_children_intersecting_source_span():
    from app.knowledge.models import Chunk, SourceRef

    datasets = evaluation_datasets()
    span = datasets.make_source_span({'document_sha256': 'a' * 64, 'page': 2, 'quote': 'AAA BBB'})
    ref = SourceRef(document_id='doc-1', revision_id='revision-2', kind='pdf', page=2)
    chunks = [
        Chunk(section_id='s', document_id='doc-1', revision_id='revision-2', chunk_uid='root',
              ordinal=0, text='start AAA', source_refs=(ref,)),
        Chunk(section_id='s', document_id='doc-1', revision_id='revision-2', chunk_uid='relevant-child',
              parent_chunk_uid='root', ordinal=1, text=' BBB end', source_refs=(ref,)),
        Chunk(section_id='s', document_id='doc-1', revision_id='revision-2', chunk_uid='unrelated-child',
              parent_chunk_uid='root', ordinal=2, text='other details', source_refs=(ref,)),
    ]

    result = datasets.map_source_span_to_chunks(
        span, chunks, revision_sha256={('doc-1', 'revision-2'): 'a' * 64})

    assert [item['chunk_uid'] for item in result['mapped_chunks']] == ['relevant-child', 'root']


def test_image_span_maps_to_real_m1_chunk_and_asset_models():
    from app.knowledge.models import Asset, Chunk, SourceRef

    datasets = evaluation_datasets()
    make_span = getattr(datasets, 'make_source_span', None)
    map_span = getattr(datasets, 'map_source_span_to_chunks', None)
    assert callable(make_span) and callable(map_span)
    span = make_span({'document_sha256': 'a' * 64, 'page': 5,
                      'quote': '操作面板示意图', 'asset_sha256': 'b' * 64})
    chunk = Chunk(
        section_id='section-1', document_id='doc-1', revision_id='revision-2',
        chunk_uid='diagram-1', ordinal=0, text='操作面板示意图', asset_ids=('asset-1',),
        source_refs=(SourceRef(document_id='doc-1', revision_id='revision-2', kind='pdf', page=5),),
    )
    asset = Asset(
        asset_id='asset-1', document_id='doc-1', revision_id='revision-2',
        sha256='b' * 64, object_key='local/asset-1.png', media_type='image/png',
        source_refs=(SourceRef(document_id='doc-1', revision_id='revision-2', kind='image',
                               page=5, asset_id='asset-1'),),
    )

    result = map_span(span, [chunk], assets=[asset],
                      revision_sha256={('doc-1', 'revision-2'): 'a' * 64})

    assert result['status'] == 'mapped'
    assert result['mapped_chunks'][0]['chunk_uid'] == 'diagram-1'


def test_fresh_heldout_cohort_excludes_legacy_exposed_source_pages():
    datasets = evaluation_datasets()
    validate_cohorts = getattr(datasets, 'validate_evaluation_cohorts', None)
    assert callable(validate_cohorts), '新冻结必须隔离历史已曝光题与来源页'

    legacy = question_row(qid='legacy-001', split='heldout', page=2)
    new_heldout = question_row(qid='fresh-001', split='heldout', page=9, document='d' * 64)
    cohorts = {'legacy_exposed_ids': ['legacy-001'], 'fresh_dev_ids': [],
               'fresh_heldout_ids': ['fresh-001']}
    assert validate_cohorts([legacy, new_heldout], cohorts) is True

    reused_page = question_row(qid='fresh-002', split='heldout', page=9)
    leaking = {'legacy_exposed_ids': ['legacy-001'], 'fresh_dev_ids': [],
               'fresh_heldout_ids': ['fresh-002']}
    with pytest.raises(ValueError, match='历史曝光'):
        validate_cohorts([legacy, reused_page], leaking)


def test_fresh_heldout_cannot_share_a_source_document_with_fresh_dev():
    datasets = evaluation_datasets()
    legacy = question_row(qid='legacy-001', split='heldout', page=2)
    dev = question_row(qid='fresh-dev-001', split='dev', page=3, document='d' * 64)
    heldout = question_row(qid='fresh-heldout-001', split='heldout', page=9, document='d' * 64)
    cohorts = {'legacy_exposed_ids': ['legacy-001'], 'fresh_dev_ids': ['fresh-dev-001'],
               'fresh_heldout_ids': ['fresh-heldout-001']}

    with pytest.raises(ValueError, match='fresh dev'):
        datasets.validate_evaluation_cohorts([legacy, dev, heldout], cohorts)


def test_attaching_derived_spans_is_immutable_and_idempotent():
    datasets = evaluation_datasets()
    attach = getattr(datasets, 'attach_source_spans', None)
    assert callable(attach), '冻结题集需要可重复生成稳定来源跨度'
    original = question_row()
    enriched = attach(original)
    assert 'source_span' not in original['allowed_evidence'][0][0]
    assert enriched['allowed_evidence'][0][0]['source_span']['span_id'] == attach(enriched)['allowed_evidence'][0][0]['source_span']['span_id']


def test_frozen_manifest_binds_parent_bytes_rows_and_fresh_cohorts(tmp_path):
    datasets = evaluation_datasets()
    attach = getattr(datasets, 'attach_source_spans', None)
    serialize = getattr(datasets, 'serialize_dataset', None)
    build_manifest = getattr(datasets, 'build_dataset_manifest', None)
    assert all(callable(item) for item in (attach, serialize, build_manifest)), '需提供可复核的版本冻结元数据'
    rows = [
        attach(question_row(qid='legacy-001', split='heldout', page=2,
                            question='合成历史题：设备额定电压是多少？')),
        attach(question_row(qid='fresh-dev-001', split='dev', page=2,
                            question='合成开发题：设备额定电压是多少？')),
        attach(question_row(qid='fresh-heldout-001', split='heldout', page=9, document='d' * 64,
                            question='合成盲测题：设备额定电压是多少？')),
    ]
    cohorts = {'legacy_exposed_ids': ['legacy-001'], 'fresh_dev_ids': ['fresh-dev-001'],
               'fresh_heldout_ids': ['fresh-heldout-001']}
    raw = serialize(rows)
    manifest = build_manifest(
        rows, version='support-v2', dataset_bytes=raw,
        parent_version='support-v1-r2', parent_dataset_sha256='e' * 64,
        parent_manifest_sha256='f' * 64,
        sources=[{'path': 'local-source.pdf', 'sha256': 'a' * 64, 'pages': 10},
                 {'path': 'new-local-source.pdf', 'sha256': 'd' * 64, 'pages': 10}],
        cohorts=cohorts,
    )
    dataset = tmp_path / 'support-v2.jsonl'
    dataset.write_bytes(raw)
    manifest_path = tmp_path / 'support-v2-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')
    assert len(validate_dataset(dataset, manifest=manifest_path, minimum=1)) == 3
    assert manifest['evaluation_cohorts']['fresh_heldout_ids'] == ['fresh-heldout-001']
    assert manifest['parent_version'] == 'support-v1-r2'


def test_frozen_manifest_rejects_any_evidence_without_stable_source_span():
    datasets = evaluation_datasets()
    row = question_row()
    rows = [row]
    with pytest.raises(ValueError, match='稳定来源跨度'):
        datasets.build_dataset_manifest(
            rows, version='support-v2', dataset_bytes=datasets.serialize_dataset(rows),
            parent_version='support-v1-r2', parent_dataset_sha256='e' * 64,
            parent_manifest_sha256='f' * 64,
            sources=[{'path': 'local-source.pdf', 'sha256': 'a' * 64, 'pages': 10}],
            cohorts={'legacy_exposed_ids': [], 'fresh_dev_ids': ['m6-synthetic-001'],
                     'fresh_heldout_ids': []},
        )


def test_frozen_manifest_validator_rejects_tampered_cohort_membership(tmp_path):
    datasets = evaluation_datasets()
    rows = [
        datasets.attach_source_spans(question_row(
            qid='legacy-001', split='heldout', page=2,
            question='合成历史题：设备额定电压是多少？')),
        datasets.attach_source_spans(question_row(
            qid='fresh-dev-001', split='dev', page=2, document='d' * 64,
            question='合成开发题：设备额定电压是多少？')),
        datasets.attach_source_spans(question_row(
            qid='fresh-heldout-001', split='heldout', page=9, document='e' * 64,
            question='合成盲测题：设备额定电压是多少？')),
    ]
    raw = datasets.serialize_dataset(rows)
    manifest = datasets.build_dataset_manifest(
        rows, version='support-v2', dataset_bytes=raw, parent_version='support-v1-r2',
        parent_dataset_sha256='e' * 64, parent_manifest_sha256='f' * 64,
        sources=[{'path': 'old.pdf', 'sha256': 'a' * 64, 'pages': 10},
                 {'path': 'dev.pdf', 'sha256': 'd' * 64, 'pages': 10},
                 {'path': 'heldout.pdf', 'sha256': 'e' * 64, 'pages': 10}],
        cohorts={'legacy_exposed_ids': ['legacy-001'], 'fresh_dev_ids': ['fresh-dev-001'],
                 'fresh_heldout_ids': ['fresh-heldout-001']},
    )
    manifest['evaluation_cohorts']['fresh_heldout_ids'] = ['legacy-001']
    dataset = tmp_path / 'support-v2.jsonl'
    dataset.write_bytes(raw)
    manifest_path = tmp_path / 'support-v2-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')

    with pytest.raises(ValueError, match='划分'):
        validate_dataset(dataset, manifest=manifest_path, minimum=1)


def test_frozen_m6_manifest_validator_requires_stable_spans_on_every_evidence(tmp_path):
    datasets = evaluation_datasets()
    row = datasets.attach_source_spans(question_row())
    rows = [row]
    raw = datasets.serialize_dataset(rows)
    manifest = datasets.build_dataset_manifest(
        rows, version='support-v2', dataset_bytes=raw, parent_version='support-v1-r2',
        parent_dataset_sha256='e' * 64, parent_manifest_sha256='f' * 64,
        sources=[{'path': 'local-source.pdf', 'sha256': 'a' * 64, 'pages': 10}],
        cohorts={'legacy_exposed_ids': [], 'fresh_dev_ids': [row['id']], 'fresh_heldout_ids': []},
    )
    raw_row = json.loads(raw.decode('utf-8'))
    raw_row['allowed_evidence'][0][0].pop('source_span')
    dataset = tmp_path / 'support-v2-no-span.jsonl'
    dataset.write_text(json.dumps(raw_row, ensure_ascii=False) + '\n', encoding='utf-8')
    manifest['dataset_sha256'] = hashlib.sha256(dataset.read_bytes()).hexdigest()
    manifest['rows'] = [{'id': raw_row['id'], 'split': raw_row['split'], 'group_id': raw_row['group_id'],
                         'sha256': datasets.fingerprint(raw_row)}]
    manifest_path = tmp_path / 'support-v2-no-span-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')

    with pytest.raises(ValueError, match='稳定来源跨度'):
        validate_dataset(dataset, manifest=manifest_path, minimum=1)


def test_image_evidence_manifest_binds_asset_digest_to_exact_source_page(tmp_path):
    datasets = evaluation_datasets()
    row = question_row()
    row['category'] = 'diagram'
    row['allowed_evidence'][0][0]['asset_sha256'] = 'b' * 64
    row = datasets.attach_source_spans(row)
    rows = [row]
    raw = datasets.serialize_dataset(rows)
    asset = {'path': 'local/redacted-crop.png', 'document_sha256': 'a' * 64,
             'page': 2, 'sha256': 'b' * 64}
    manifest = datasets.build_dataset_manifest(
        rows, version='support-v2', dataset_bytes=raw, parent_version='support-v1-r2',
        parent_dataset_sha256='e' * 64, parent_manifest_sha256='f' * 64,
        sources=[{'path': 'local-source.pdf', 'sha256': 'a' * 64, 'pages': 10}], assets=[asset],
        cohorts={'legacy_exposed_ids': [], 'fresh_dev_ids': [row['id']], 'fresh_heldout_ids': []},
    )
    assert manifest['assets'] == [asset]
    manifest['assets'] = []
    dataset = tmp_path / 'image-span.jsonl'
    dataset.write_bytes(raw)
    manifest_path = tmp_path / 'image-span-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')

    with pytest.raises(ValueError, match='精确资产登记'):
        validate_dataset(dataset, manifest=manifest_path, minimum=1)


def test_unanswerable_draft_without_evidence_can_be_frozen_but_is_not_gold(tmp_path):
    datasets = evaluation_datasets()
    row = question_row()
    row['category'] = 'unanswerable'
    row['question'] = '合成验证：这台设备当前剩余电量是多少？'
    row['expected'] = {'behavior': 'insufficient', 'key_points': ['应说明手册不能提供当前设备的实时电量'],
                       'forbidden_claims': ['不得编造当前电量']}
    row['allowed_evidence'] = []
    rows = [row]
    raw = datasets.serialize_dataset(rows)
    manifest = datasets.build_dataset_manifest(
        rows, version='support-v2', dataset_bytes=raw, parent_version='support-v1-r2',
        parent_dataset_sha256='e' * 64, parent_manifest_sha256='f' * 64,
        sources=[{'path': 'local-source.pdf', 'sha256': 'a' * 64, 'pages': 10}],
        cohorts={'legacy_exposed_ids': [], 'fresh_dev_ids': [row['id']], 'fresh_heldout_ids': []},
    )
    dataset = tmp_path / 'unanswerable.jsonl'
    dataset.write_bytes(raw)
    manifest_path = tmp_path / 'unanswerable-manifest.json'
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding='utf-8')

    assert validate_dataset(dataset, manifest=manifest_path, minimum=1) == rows
    assert datasets.is_label_eligible(row) is False
