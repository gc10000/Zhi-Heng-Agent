"""用本机原件文本和正式 M1 切片器离线复核 M6-01 来源跨度；不访问在线服务。"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path

import fitz

from app.evaluation.datasets import map_source_span_to_chunks
from app.evaluation.validate_dataset import file_sha, validate_dataset
from app.ingestion.models import Block, ParsedDocument
from app.ingestion.stages.chunking import chunk_document
from app.knowledge.models import SourceRef


ROOT = Path(__file__).resolve().parents[2]


def map_text_spans(dataset_path: Path, manifest_path: Path) -> dict:
    """按真实PDF物理页和生产 M1 chunk_document 的切片边界映射文本跨度。"""
    dataset_path = dataset_path.resolve()
    manifest_path = manifest_path.resolve()
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    rows = validate_dataset(dataset_path, manifest=manifest_path, minimum=1)
    root = ROOT.resolve()
    sources = {source['sha256']: source for source in manifest['sources']}
    chunks_by_sha = {}
    revision_sha256 = {}

    for sha, source in sources.items():
        relative = Path(source['path'])
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file() or path.suffix.lower() != '.pdf':
            raise ValueError('题集来源必须是仓库内存在的PDF原件')
        if hashlib.sha256(path.read_bytes()).hexdigest() != sha:
            raise ValueError('来源PDF的原件SHA256不匹配')
        pdf = fitz.open(path)
        if len(pdf) != source['pages']:
            raise ValueError('来源PDF物理页数与冻结manifest不匹配')
        document_id, revision_id = f'm6-{sha[:16]}', f'r-{sha[:16]}'
        blocks = tuple(
            Block(block_id=f'page-{index + 1}', kind='text', text=page.get_text(),
                  source_refs=(SourceRef(document_id=document_id, revision_id=revision_id,
                                         kind='pdf', page=index + 1),))
            for index, page in enumerate(pdf)
        )
        parsed = ParsedDocument(document_id=document_id, revision_id=revision_id,
                                original_sha256=sha, parser='fitz-readonly-map-check',
                                parser_version=fitz.VersionBind, blocks=blocks)
        chunks_by_sha[sha] = chunk_document(parsed, max_chars=2000)
        revision_sha256[(document_id, revision_id)] = sha

    mapped_by_source = Counter()
    unmapped_text = 0
    image_spans = 0
    for row in rows:
        for group in row['allowed_evidence']:
            for evidence in group:
                span = evidence['source_span']
                if span['kind'] == 'image':
                    image_spans += 1
                    continue
                result = map_source_span_to_chunks(
                    span, chunks_by_sha[span['document_sha256']], revision_sha256=revision_sha256)
                if result['status'] == 'mapped':
                    mapped_by_source[span['document_sha256']] += 1
                else:
                    unmapped_text += 1

    verified_assets = 0
    for asset in manifest.get('assets', []):
        path = (root / asset['path']).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise ValueError('冻结图像资产文件缺失或路径越界')
        if hashlib.sha256(path.read_bytes()).hexdigest() != asset['sha256']:
            raise ValueError('冻结图像资产SHA256不匹配')
        verified_assets += 1

    return {
        'dataset_sha256': file_sha(dataset_path),
        'manifest_sha256': file_sha(manifest_path),
        'source_count': len(sources),
        'chunk_count': sum(len(chunks) for chunks in chunks_by_sha.values()),
        'text_span_count': sum(mapped_by_source.values()) + unmapped_text,
        'mapped_text_span_count': sum(mapped_by_source.values()),
        'unmapped_text_span_count': unmapped_text,
        'mapped_text_spans_by_source_sha256': dict(sorted(mapped_by_source.items())),
        'image_span_count': image_spans,
        'image_asset_files_hash_verified': verified_assets,
        'image_asset_chunk_mapping': 'not_verified_against_persisted_M1_index',
        'database_or_object_store_accessed': False,
        'provider_calls': 0,
        'fresh_heldout_executed': False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('输出证据已存在；请使用独立的新路径，不覆盖旧报告')
    result = map_text_spans(args.dataset, args.manifest)
    if result['unmapped_text_span_count']:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'passed': False, **result}, ensure_ascii=False, sort_keys=True))
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'passed': True, **result}, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
