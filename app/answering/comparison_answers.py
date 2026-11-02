"""从冻结来源帧派生比较事实；模型只选择帧，不提交语义断言。"""
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.knowledge.repository import fingerprint

VERSION = 'comparison_answer_v1'
SCHEMA_VERSION = 'comparison_frame_selection_v1'
MAX_SELECTION_CHARS = 4096
MAX_SELECTED_FRAMES = 100


class ComparisonAnswerPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    enabled: bool = Field(default=False, strict=True)
    function_version: Literal['comparison_answer_v1'] = VERSION


class SelectedFrame(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    reference: int = Field(strict=True, ge=1)
    frame: int = Field(strict=True, ge=0)


class FrameSelection(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    schema_version: Literal[SCHEMA_VERSION]
    frames: list[SelectedFrame] = Field(min_length=1, max_length=MAX_SELECTED_FRAMES)


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('帧选择不接受重复JSON字段')
        result[key] = value
    return result


def validate_frame_selection(raw_json, catalog):
    if not isinstance(raw_json, str) or len(raw_json) > MAX_SELECTION_CHARS:
        raise ValueError('帧选择缺失或超出长度限制')
    parsed = json.loads(raw_json, object_pairs_hook=_unique_object)
    selection = FrameSelection.model_validate(parsed)
    available = {(item['reference_number'], item['frame_index']) for item in catalog}
    selected = [(item.reference, item.frame) for item in selection.frames]
    if len(set(selected)) != len(selected) or any(pair not in available for pair in selected):
        raise ValueError('帧选择含重复或不存在的来源帧')
    return [dict(reference=reference, frame=frame) for reference, frame in selected]


def build_frame_catalog(reference_map, docs, attribution):
    """校验既有冻结归属和帧跨度后，建立稳定的引用号/帧号目录。"""
    from .assertion_binding import checked_sources
    from .evidence_attribution import EvidenceAttributionPolicy

    policy = EvidenceAttributionPolicy.model_validate(attribution)
    if (not policy.enabled or policy.source_relations is None or
            not policy.source_relations.enabled or
            policy.comparison_answer is None or not policy.comparison_answer.enabled):
        raise ValueError('比较答复缺少显式冻结来源策略')
    checked_sources(reference_map, docs, policy)
    catalog = []
    for row, doc in zip(reference_map, docs):
        relation = row['source_relations']
        metadata = doc.get('metadata') or {}
        product_ids = metadata.get('product_ids') or []
        for frame_index, frame in enumerate(relation['frames']):
            start, end = frame['scope']['start'], frame['scope']['end']
            catalog.append(dict(
                reference_number=row['reference_number'],
                frame_index=frame_index,
                document_id=row['document_id'],
                revision_id=row['revision_id'],
                chunk_uid=row['chunk_uid'],
                original_sha256=row['original_sha256'],
                source_product_ids=list(product_ids),
                product_labels={pid: policy.products[pid] for pid in product_ids if pid in policy.products},
                physical_pages=list(row['physical_pages']),
                page_status=row['page_status'],
                frame=frame,
                frame_sha256=fingerprint(frame),
                source_text=doc.get('text') or '',
                scoped_text=(doc.get('text') or '')[start:end],
                source_refs=doc.get('source_refs', metadata.get('source_refs', [])),
            ))
    return catalog


def render_frame_catalog(catalog):
    """以数据序列化呈现原文，避免将资料标记解释成目录结构。"""
    rows = []
    for item in catalog:
        rows.append(dict(reference=item['reference_number'], frame=item['frame_index'],
            products=item['product_labels'], original_sentence=item['scoped_text']))
    return json.dumps(rows, ensure_ascii=False, separators=(',', ':'))


_NEGATION_OR_CONDITION = re.compile(r'若|如果|除非|只有|不支持|不能|无法|未|不|是否|仅')
_GENERIC_DEVICE_ORIGIN = {'设备', '本设备', '该设备', '网关', '本网关', '路由器', '本路由器'}
_GENERIC_UPLINK_ORIGIN = re.compile(r'^(?:本|该)?(?:设备|网关|路由器)上联$')


def _field_text(frame, name):
    span = (frame.get('fields') or {}).get(name)
    return span.get('text') if isinstance(span, dict) else None


def _belongs_to_product(clause, product_id, source_product_ids, product_label):
    if product_id not in source_product_ids:
        return False
    if source_product_ids == [product_id]:
        return True
    return bool(product_label and product_label in clause)


def _origin_is_product(origin, clause, product_id, source_product_ids, product_label):
    if not origin:
        return False
    if product_label and product_label in origin:
        return True
    names_target = bool(product_label and product_label in clause)
    return ((source_product_ids == [product_id] or names_target) and
            (origin.strip() in _GENERIC_DEVICE_ORIGIN or
             bool(_GENERIC_UPLINK_ORIGIN.fullmatch(origin.strip()))))


def classify_frame(frame, clause, product_id, source_product_ids, product_label=None):
    """按冻结原句帧分类；不能把连接、访问或检查推成设备上联。"""
    if not isinstance(frame, dict) or not isinstance(clause, str) or not product_id:
        raise ValueError('比较事实缺少有效帧、原句或产品身份')
    origin, destination = _field_text(frame, 'origin'), _field_text(frame, 'destination')
    medium, purpose = _field_text(frame, 'medium'), _field_text(frame, 'purpose')
    category = 'unknown'
    belongs = _belongs_to_product(clause, product_id, source_product_ids, product_label)
    if belongs and frame.get('kind') == 'physical_check':
        category = 'diagnostic_check'
    elif belongs and not _NEGATION_OR_CONDITION.search(clause):
        if frame.get('kind') in {'access', 'login'} and destination:
            category = 'client_access'
        elif (frame.get('kind') in {'service', 'connection'} and purpose and '管理' in purpose and
              origin and destination and
              _origin_is_product(origin, clause, product_id, source_product_ids, product_label)):
            category = 'management_link'
        elif (frame.get('kind') == 'connection' and
                re.search(r'上联|\buplink\b', clause, re.IGNORECASE) and
                not _NEGATION_OR_CONDITION.search(clause) and
                _origin_is_product(origin, clause, product_id, source_product_ids, product_label) and
                medium and destination):
            category = 'device_uplink'
    return dict(category=category, product_id=product_id, origin=origin,
        destination=destination, medium=medium, purpose=purpose,
        operational_status='unknown' if category == 'diagnostic_check' else None,
        clause=clause, scope=frame.get('scope'), frame_sha256=fingerprint(frame))


def derive_facts(selection, catalog, product_ids):
    by_identity = {(item['reference_number'], item['frame_index']): item for item in catalog}
    facts = []
    seen = set()
    for selected in selection:
        identity = selected['reference'], selected['frame']
        if identity in seen or identity not in by_identity:
            raise ValueError('派生事实含重复或不存在的来源帧')
        seen.add(identity)
        item = by_identity[identity]
        clause = item['frame']['clause']['text']
        for product_id in product_ids:
            label = item['product_labels'].get(product_id)
            fact = classify_frame(item['frame'], clause, product_id,
                item['source_product_ids'], label)
            if (fact['category'] == 'unknown' and product_id not in item['source_product_ids'] and
                    not (label and label in clause)):
                continue
            fact.update(reference_number=item['reference_number'], frame_index=item['frame_index'],
                document_id=item['document_id'], revision_id=item['revision_id'], chunk_uid=item['chunk_uid'],
                original_sha256=item['original_sha256'], physical_pages=item['physical_pages'],
                page_status=item['page_status'], scoped_text=item['scoped_text'],
                source_refs=item['source_refs'])
            facts.append(fact)
    return facts
