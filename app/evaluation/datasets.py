"""M6 题集标签版本、稳定证据跨度与新切片映射。"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import unicodedata
from collections.abc import Mapping, Sequence

from .validate_dataset import Question, SourceSpan, fingerprint, source_span_fingerprint

_LABEL_FIELDS = {'expected', 'allowed_evidence'}
_VERSION = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$')


def label_fingerprint(question: Mapping) -> str:
    """只对可评分标签计算指纹；问题内容与审核记录由题目/清单单独绑定。"""
    return fingerprint({key: question[key] for key in ('expected', 'allowed_evidence')})


def make_source_span(evidence: Mapping) -> dict:
    """从已存在的引文标签构造不依赖切片ID的稳定原件跨度。"""
    if not isinstance(evidence, Mapping):
        raise ValueError('来源标签格式错误')
    document_sha256 = evidence.get('document_sha256')
    page = evidence.get('page')
    quote = evidence.get('quote')
    asset_sha256 = evidence.get('asset_sha256')
    if (not isinstance(document_sha256, str) or not re.fullmatch(r'[0-9a-f]{64}', document_sha256) or
            isinstance(page, bool) or not isinstance(page, int) or page < 1 or
            not isinstance(quote, str) or not quote.strip()):
        raise ValueError('来源标签缺少有效原件指纹、物理页或引文')
    if asset_sha256 is not None and (not isinstance(asset_sha256, str) or
                                     not re.fullmatch(r'[0-9a-f]{64}', asset_sha256)):
        raise ValueError('图像资产指纹格式错误')
    kind = 'image' if asset_sha256 else 'text'
    quote_sha256 = hashlib.sha256(quote.encode('utf-8')).hexdigest()
    return {'span_id': source_span_fingerprint(document_sha256, page, quote_sha256,
                                                kind=kind, asset_sha256=asset_sha256),
            'kind': kind, 'document_sha256': document_sha256, 'page': page,
            'quote': quote, 'quote_sha256': quote_sha256, 'asset_sha256': asset_sha256}


def attach_source_spans(question: Mapping) -> dict:
    """为现有引用标签补充确定性跨度，绝不改写调用方题目或审核状态。"""
    enriched = copy.deepcopy(dict(question))
    Question.model_validate(enriched)
    for group in enriched['allowed_evidence']:
        for evidence in group:
            expected = make_source_span(evidence)
            existing = evidence.get('source_span')
            if existing is not None and existing != expected:
                raise ValueError('已有来源跨度与原件/引文不一致')
            evidence['source_span'] = expected
    Question.model_validate(enriched)
    return enriched


def serialize_dataset(questions: Sequence[Mapping]) -> bytes:
    """生成确定性JSONL字节，供manifest记录文件和逐题哈希。"""
    output = []
    for question in questions:
        Question.model_validate(dict(question))
        output.append(json.dumps(question, ensure_ascii=False, sort_keys=True,
                                 separators=(',', ':'), allow_nan=False))
    return (''.join(line + '\n' for line in output)).encode('utf-8')


def build_dataset_manifest(questions: Sequence[Mapping], *, version: str, dataset_bytes: bytes,
                           parent_version: str, parent_dataset_sha256: str,
                           parent_manifest_sha256: str, sources: Sequence[Mapping],
                           assets: Sequence[Mapping] = (),
                           cohorts: Mapping) -> dict:
    """冻结题集父版本、题目指纹、来源清单及不泄漏的M6新划分。"""
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ValueError('题集版本格式无效')
    for digest in (parent_dataset_sha256, parent_manifest_sha256):
        if not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest):
            raise ValueError('父题集与父manifest必须绑定SHA256')
    rows = [dict(question) for question in questions]
    expected_bytes = serialize_dataset(rows)
    if not isinstance(dataset_bytes, bytes) or dataset_bytes != expected_bytes:
        raise ValueError('冻结题集字节与待登记题目不一致')
    validate_evaluation_cohorts(rows, cohorts)
    if any(evidence.get('source_span') is None
           for question in rows for group in question['allowed_evidence'] for evidence in group):
        raise ValueError('M6冻结题集中的每条允许证据都必须记录稳定来源跨度')
    clean_sources = []
    seen_sources = set()
    for source in sources:
        if not isinstance(source, Mapping):
            raise ValueError('来源登记格式错误')
        path, digest, pages = source.get('path'), source.get('sha256'), source.get('pages')
        if (not isinstance(path, str) or not path or not isinstance(digest, str) or
                not re.fullmatch(r'[0-9a-f]{64}', digest) or isinstance(pages, bool) or
                not isinstance(pages, int) or pages < 1 or digest in seen_sources):
            raise ValueError('来源登记缺少唯一原件指纹或有效页数')
        seen_sources.add(digest)
        clean_sources.append({'path': path, 'sha256': digest, 'pages': pages})
    allowed_sources = set(seen_sources)
    for question in rows:
        if not set(question['source_scope']) <= allowed_sources:
            raise ValueError('题目引用了冻结来源清单外的原件')
    clean_assets = []
    seen_assets = set()
    source_pages = {item['sha256']: item['pages'] for item in clean_sources}
    for asset in assets:
        if not isinstance(asset, Mapping):
            raise ValueError('图像资产登记格式错误')
        digest, document_sha256, page = asset.get('sha256'), asset.get('document_sha256'), asset.get('page')
        if (not isinstance(digest, str) or not re.fullmatch(r'[0-9a-f]{64}', digest) or
                not isinstance(document_sha256, str) or document_sha256 not in source_pages or
                isinstance(page, bool) or not isinstance(page, int) or page < 1 or
                page > source_pages[document_sha256] or not isinstance(asset.get('path'), str) or not asset.get('path')):
            raise ValueError('图像资产缺少唯一hash、有效来源或物理页')
        key = (document_sha256, page, digest)
        if key in seen_assets:
            raise ValueError('图像资产登记重复')
        seen_assets.add(key)
        clean_assets.append(copy.deepcopy(dict(asset)))
    declared_assets = {(item['document_sha256'], item['page'], item['sha256']) for item in clean_assets}
    for question in rows:
        for group in question['allowed_evidence']:
            for evidence in group:
                if evidence.get('asset_sha256') is not None and (
                        evidence['document_sha256'], evidence['page'], evidence['asset_sha256']) not in declared_assets:
                    raise ValueError('图像来源跨度没有精确登记原件、物理页和资产指纹')
    return {
        'version': version,
        'parent_version': parent_version,
        'parent_dataset_sha256': parent_dataset_sha256,
        'parent_manifest_sha256': parent_manifest_sha256,
        'dataset_sha256': hashlib.sha256(dataset_bytes).hexdigest(),
        'rows': [{'id': row['id'], 'split': row['split'], 'group_id': row['group_id'],
                  'sha256': fingerprint(row)} for row in rows],
        'sources': sorted(clean_sources, key=lambda item: item['sha256']),
        'assets': sorted(clean_assets, key=lambda item: (item['document_sha256'], item['page'], item['sha256'])),
        'evaluation_cohorts': {
            name: sorted(cohorts[name]) for name in
            ('legacy_exposed_ids', 'fresh_dev_ids', 'fresh_heldout_ids')},
        'split_policy': '同一问题族固定在单一划分；M4旧题仅保留为历史曝光参考，fresh heldout使用未进入旧题集的新来源，策略冻结前不得执行。',
        'annotation_notice': 'source_checked_assistant_draft 仅为待审候选；未审标签不得计入标准质量指标。',
        'revision_changes': [],
    }


def _normalized(value: str) -> str:
    return ' '.join(unicodedata.normalize('NFKC', value).casefold().split())


def _normalized_text_with_owners(parts: Sequence[str]) -> tuple[str, list[int]]:
    """规范化连续切片文本，同时保留每个字符所属的切片序号。"""
    output, owners = [], []
    for owner, part in enumerate(parts):
        for char in part:
            for normalized_char in unicodedata.normalize('NFKC', char).casefold():
                if normalized_char.isspace():
                    if output and output[-1] != ' ':
                        output.append(' ')
                        owners.append(owner)
                else:
                    output.append(normalized_char)
                    owners.append(owner)
    if output and output[-1] == ' ':
        output.pop()
        owners.pop()
    return ''.join(output), owners


def _as_mapping(value):
    """兼容Mongo字典快照与M1冻结Pydantic领域实体。"""
    if isinstance(value, Mapping):
        return value
    dump = getattr(value, 'model_dump', None)
    if callable(dump):
        projected = dump(mode='python')
        return projected if isinstance(projected, Mapping) else None
    return None


def _page_reference(chunk: Mapping, page: int) -> bool:
    refs = chunk.get('source_refs')
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)):
        return False
    document_id, revision_id = chunk.get('document_id'), chunk.get('revision_id')
    return any(isinstance(ref, Mapping) and ref.get('page') == page and
               ref.get('document_id') == document_id and ref.get('revision_id') == revision_id
               for ref in refs)


def map_source_span_to_chunks(span: Mapping, chunks: Sequence[Mapping], *, assets: Sequence[Mapping] = (),
                              revision_sha256: Mapping[tuple[str, str], str] | None = None) -> dict:
    """按原件hash/物理页/引文或图像hash映射新revision的chunk身份。

    M1的Chunk不重复存储原件hash，实际领域对象需由资料仓储传入(document_id,
    revision_id)->original_sha256；序列化快照若已带document_sha256则同时核对。
    未映射项显式标记为invalid，调用方不得把它记成检索失败或答案错误。
    """
    validated = SourceSpan.model_validate(dict(span))
    mapped = set()
    revision_sha256 = revision_sha256 or {}
    normalized_assets = tuple(item for item in (_as_mapping(asset) for asset in assets) if item is not None)
    text_groups = {}
    for candidate in chunks:
        chunk = _as_mapping(candidate)
        if chunk is None:
            continue
        doc_id, revision_id, chunk_uid = (chunk.get('document_id'), chunk.get('revision_id'), chunk.get('chunk_uid'))
        if (not all(isinstance(value, str) and value for value in (doc_id, revision_id, chunk_uid)) or
                not _page_reference(chunk, validated.page)):
            continue
        chunk_sha256 = chunk.get('document_sha256')
        revision_hash = revision_sha256.get((doc_id, revision_id))
        if chunk_sha256 is None:
            chunk_sha256 = revision_hash
        elif revision_hash is not None and revision_hash != chunk_sha256:
            continue
        if chunk_sha256 != validated.document_sha256:
            continue
        if validated.kind == 'text':
            text = chunk.get('text')
            if not isinstance(text, str):
                continue
            block_id = chunk.get('parent_chunk_uid') or chunk_uid
            text_groups.setdefault((doc_id, revision_id, block_id), []).append((chunk, text))
            if _normalized(validated.quote) in _normalized(text):
                mapped.add((doc_id, revision_id, chunk_uid))
        else:
            chunk_assets = set(chunk.get('asset_ids') or ())
            asset_match = any(
                asset.get('asset_id') in chunk_assets and
                asset.get('document_id') == doc_id and asset.get('revision_id') == revision_id and
                asset.get('sha256') == validated.asset_sha256 and
                any(isinstance(ref, Mapping) and ref.get('page') == validated.page
                    for ref in (asset.get('source_refs') or ()))
                for asset in normalized_assets
            )
            if not asset_match:
                continue
            mapped.add((doc_id, revision_id, chunk_uid))
    for (doc_id, revision_id, _), members in text_groups.items():
        members.sort(key=lambda item: (item[0].get('ordinal', 0), item[0].get('chunk_uid', '')))
        normalized_text, owners = _normalized_text_with_owners([text for _, text in members])
        needle = _normalized(validated.quote)
        start = 0
        while needle and (found := normalized_text.find(needle, start)) >= 0:
            end = found + len(needle)
            for owner in set(owners[found:end]):
                mapped.add((doc_id, revision_id, members[owner][0]['chunk_uid']))
            start = found + 1
    mapped = sorted(mapped)
    chunk_ids = [{'document_id': doc, 'revision_id': revision, 'chunk_uid': uid}
                 for doc, revision, uid in mapped]
    return {'span_id': validated.span_id, 'status': 'mapped' if chunk_ids else 'unmapped',
            'scoring_status': 'eligible' if chunk_ids else 'invalid',
            'reason': None if chunk_ids else 'source_span_not_found', 'mapped_chunks': chunk_ids}


def revise_label(question: Mapping, *, changes: Mapping, version: str, reason: str) -> tuple[dict, dict]:
    """创建不可变题目副本；标签变化必须带新版本、理由和前后指纹。"""
    if not isinstance(version, str) or not _VERSION.fullmatch(version):
        raise ValueError('标签版本格式无效')
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError('标签修订必须说明原因')
    if not isinstance(changes, Mapping) or not changes or not set(changes) <= _LABEL_FIELDS:
        raise ValueError('标签修订只允许修改期望答案或允许证据')
    revised = copy.deepcopy(dict(question))
    Question.model_validate(revised)
    old_label_sha256 = label_fingerprint(revised)
    prior_revisions = revised.get('label_revisions', [])
    if any(item['version'] == version for item in prior_revisions):
        raise ValueError('标签修订版本重复')
    if prior_revisions and prior_revisions[-1]['current_label_sha256'] != old_label_sha256:
        raise ValueError('已有标签修订指纹链与当前标签不一致')
    for key, value in changes.items():
        revised[key] = copy.deepcopy(value)
    current_label_sha256 = label_fingerprint(revised)
    if current_label_sha256 == old_label_sha256:
        raise ValueError('标签修订没有改变标签内容')
    change = {'version': version, 'reason': reason.strip(),
              'previous_label_sha256': old_label_sha256, 'current_label_sha256': current_label_sha256}
    revised.setdefault('label_revisions', []).append(change)
    # 旧审核仅对旧标签有效，新版本必须重新审阅；保留历史由不可变父版本承担。
    revised['annotation'] = {'method': 'source_checked_assistant_draft', 'status': 'draft'}
    Question.model_validate(revised)
    return revised, change


def is_label_eligible(question: Mapping) -> bool:
    """只有明确审阅的标签进入标准指标；反馈/助手草稿不默认当作真值。"""
    try:
        annotation = Question.model_validate(dict(question)).annotation.model_dump(mode='json')
    except Exception:
        return False
    reviewer = annotation.get('reviewer') if isinstance(annotation, Mapping) else None
    return (isinstance(annotation, Mapping) and annotation.get('status') == 'reviewed' and
            annotation.get('method') in {'independent_assistant_review', 'human_reviewed'} and
            isinstance(reviewer, str) and bool(reviewer.strip()))


def validate_evaluation_cohorts(questions: Sequence[Mapping], cohorts: Mapping) -> bool:
    """验证M6新划分完整互斥，并阻止历史曝光题集/来源流入新heldout。"""
    required = {'legacy_exposed_ids', 'fresh_dev_ids', 'fresh_heldout_ids'}
    if not isinstance(cohorts, Mapping) or set(cohorts) != required:
        raise ValueError('评测划分必须显式列出历史题、fresh dev与fresh heldout')
    question_ids = [row.get('id') for row in questions]
    if any(not isinstance(qid, str) or not qid for qid in question_ids) or len(set(question_ids)) != len(question_ids):
        raise ValueError('题集ID无效或重复')
    groups = {name: cohorts[name] for name in required}
    if any(not isinstance(ids, Sequence) or isinstance(ids, (str, bytes)) or
           any(not isinstance(qid, str) or not qid for qid in ids) or len(set(ids)) != len(ids)
           for ids in groups.values()):
        raise ValueError('评测划分成员必须为不重复题目ID列表')
    members = [set(ids) for ids in groups.values()]
    if any(members[i] & members[j] for i in range(len(members)) for j in range(i + 1, len(members))):
        raise ValueError('评测划分成员重叠')
    if set.union(*members) != set(question_ids):
        raise ValueError('评测划分必须覆盖题集且不能引用未知题目')
    by_id = dict(zip(question_ids, questions))
    for qid in groups['fresh_dev_ids']:
        if by_id[qid].get('split') != 'dev':
            raise ValueError('fresh dev题目划分不匹配')
    for qid in groups['fresh_heldout_ids']:
        if by_id[qid].get('split') != 'heldout':
            raise ValueError('fresh heldout题目划分不匹配')
    legacy_rows = [by_id[qid] for qid in groups['legacy_exposed_ids']]
    old_sources = {sha for row in legacy_rows for sha in row.get('source_scope', [])}
    old_pages = {(evidence.get('document_sha256'), evidence.get('page'))
                 for row in legacy_rows for group in row.get('allowed_evidence', []) for evidence in group}
    for qid in groups['fresh_heldout_ids']:
        row = by_id[qid]
        if old_sources & set(row.get('source_scope', [])):
            raise ValueError('fresh heldout复用了历史曝光来源')
        if old_pages & {(e.get('document_sha256'), e.get('page'))
                        for group in row.get('allowed_evidence', []) for e in group}:
            raise ValueError('fresh heldout复用了历史曝光页')
    fresh_dev_sources = {sha for qid in groups['fresh_dev_ids'] for sha in by_id[qid].get('source_scope', [])}
    fresh_heldout_sources = {sha for qid in groups['fresh_heldout_ids']
                             for sha in by_id[qid].get('source_scope', [])}
    if fresh_dev_sources & fresh_heldout_sources:
        raise ValueError('fresh heldout不得与fresh dev共享原件来源')
    return True


def build_evaluation_cohorts(questions: Sequence[Mapping], *, legacy_exposed_ids: Sequence[str],
                             fresh_dev_ids: Sequence[str], fresh_heldout_ids: Sequence[str]) -> dict:
    cohorts = {'legacy_exposed_ids': sorted(legacy_exposed_ids),
               'fresh_dev_ids': sorted(fresh_dev_ids),
               'fresh_heldout_ids': sorted(fresh_heldout_ids)}
    validate_evaluation_cohorts(questions, cohorts)
    return cohorts
