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
COMPARABLE_VALUES_V1 = {
    '以太网': 'ethernet',
    'ethernet': 'ethernet',
    '同轴': 'coaxial',
    'coaxial': 'coaxial',
    '光纤': 'fiber',
    'fiber': 'fiber',
}
_MEDIUM_LABELS = {'ethernet': '以太网', 'coaxial': '同轴', 'fiber': '光纤'}
_CATEGORY_LABELS = {
    'device_uplink': '设备上联',
    'client_access': '客户端访问',
    'management_link': '管理连接',
    'diagnostic_check': '排障检查条件',
    'unknown': '关系类别未能确定',
}


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
    frames: list[SelectedFrame] = Field(max_length=MAX_SELECTED_FRAMES)


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
    from .evidence_attribution import EvidenceAttributionPolicy, evidence_labels

    policy = EvidenceAttributionPolicy.model_validate(attribution)
    if (not policy.enabled or policy.source_relations is None or
            not policy.source_relations.enabled or
            policy.comparison_answer is None or not policy.comparison_answer.enabled):
        raise ValueError('比较答复缺少显式冻结来源策略')
    if docs or reference_map:
        expected = [dict(label, reference_number=n + 1)
            for n, label in enumerate(evidence_labels(docs, policy))]
        if expected != reference_map:
            raise ValueError('比较目录与冻结来源重新派生结果不一致')
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


def prompt_used_identity(question, reference_map, docs, target):
    return fingerprint(dict(question=question, reference_map=reference_map,
        documents=docs, target=target))


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


def _canonical_medium(value):
    if not isinstance(value, str):
        return None
    normalized = value.strip().casefold() if value.isascii() else value.strip()
    return COMPARABLE_VALUES_V1.get(normalized)


def compare_facts(target, product_ids, facts):
    if target != 'device_uplink' or len(product_ids) != 2 or len(set(product_ids)) != len(product_ids):
        raise ValueError('当前比较器只接受两个不同产品的设备上联问题')
    by_product = {product_id: [] for product_id in product_ids}
    for fact in facts:
        product_id = fact.get('product_id')
        if product_id not in by_product:
            raise ValueError('比较事实超出本轮冻结产品范围')
        by_product[product_id].append(fact)
    keys = {product_id: [] for product_id in product_ids}
    normalized = {}
    for product_id, items in by_product.items():
        for item in items:
            if item.get('category') != 'device_uplink':
                continue
            key = item.get('document_id'), item.get('revision_id'), item.get('chunk_uid'), item.get('frame_index')
            keys[product_id].append(key)
            normalized[(product_id, key)] = _canonical_medium(item.get('medium'))
    status = 'insufficient_comparison'
    compared = {}
    if all(len(keys[pid]) == 1 for pid in product_ids):
        values = [normalized[(pid, keys[pid][0])] for pid in product_ids]
        if all(value is not None for value in values):
            status = 'same' if len(set(values)) == 1 else 'different'
            compared = dict(field='medium', canonical_values=dict(zip(product_ids, values)))
    missing = {}
    for product_id in product_ids:
        key = keys[product_id][0] if len(keys[product_id]) == 1 else None
        missing[product_id] = ('uplink_or_comparable_medium'
            if key is None or normalized.get((product_id, key)) is None else None)
    return dict(function_version=VERSION, comparison_target=target, status=status,
        product_ids=list(product_ids), products={pid: by_product[pid] for pid in product_ids},
        compared=compared, missing=missing)


def _citation(fact):
    pages = fact.get('physical_pages') or []
    page_text = '、'.join(str(page) for page in pages) if fact.get('page_status') == 'exact' and pages else '页码未知'
    return f"[{fact['reference_number']}]（{page_text}）"


def _fact_description(fact):
    category = fact.get('category', 'unknown')
    label = _CATEGORY_LABELS.get(category, _CATEGORY_LABELS['unknown'])
    if category == 'device_uplink':
        medium = _canonical_medium(fact.get('medium'))
        if medium:
            return f"资料记载的上联介质为{_MEDIUM_LABELS[medium]}"
        return '资料有上联表述，但介质未能按当前比较范围确认'
    if category == 'management_link':
        return f'资料记载{label}，不能据此认定设备上联方式'
    if category == 'client_access':
        return f'资料记载{label}，不能据此认定设备上联方式'
    if category == 'diagnostic_check':
        return '资料描述的是排障检查条件，不代表链路已经连接'
    return '资料原句的关系类别未能按当前规则确定'


def render_comparison_answer(result, product_labels):
    if result.get('comparison_target') != 'device_uplink':
        raise ValueError('答案渲染目标与已验证比较结果不一致')
    status = result.get('status')
    names = result['product_ids']
    if status == 'same':
        first = '现有资料支持两台设备的上联介质相同。'
    elif status == 'different':
        first = '现有资料支持两台设备的上联介质不同。'
    elif status == 'insufficient_comparison':
        first = '现有证据不足以判断两台设备的上联方式是否相同或不同。'
    else:
        raise ValueError('比较结果状态无效')
    lines = [first]
    for product_id in names:
        label = product_labels.get(product_id, product_id)
        facts = result['products'][product_id]
        usable = [fact for fact in facts if fact.get('category') in _CATEGORY_LABELS]
        if not usable:
            lines.append(f'{label}：本轮引用资料中没有可用的关系记录。')
            continue
        for fact in usable:
            lines.append(f"{label}：{_fact_description(fact)}{_citation(fact)}。")
    if status == 'insufficient_comparison':
        missing = [product_labels.get(pid, pid) for pid, reason in result['missing'].items() if reason]
        if missing:
            lines.append('缺少可比较的设备上联介质证据：' + '、'.join(missing) + '。')
    return '\n'.join(lines)


def create_comparison_proof(target, policy_sha256, prompt_used_sha256,
                            selection, facts, result, answer):
    if target != result.get('comparison_target') or result.get('function_version') != VERSION:
        raise ValueError('比较proof目标或实现版本不一致')
    for value in (policy_sha256, prompt_used_sha256):
        if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
            raise ValueError('比较proof输入身份hash无效')
    expected_facts = fingerprint(facts)
    if result.get('products') is None:
        raise ValueError('比较proof缺少派生事实结果')
    return dict(function_version=VERSION, schema_version=SCHEMA_VERSION,
        classifier_version='source_frame_classifier_v1', comparator_version='same_uplink_medium_v1',
        renderer_version='comparison_answer_renderer_v1', comparison_target=target,
        policy_sha256=policy_sha256, prompt_used_sha256=prompt_used_sha256,
        selection_sha256=fingerprint(selection), facts_sha256=expected_facts,
        result_sha256=fingerprint(result), answer_sha256=fingerprint(answer),
        selected_frames=selection, comparison_status=result['status'])


def bind_comparison_response(raw_json, catalog, product_ids, target,
                             policy_sha256, prompt_used_sha256, product_labels):
    selection = validate_frame_selection(raw_json, catalog)
    return bind_comparison_selection(selection, catalog, product_ids, target,
        policy_sha256, prompt_used_sha256, product_labels, raw_selection=raw_json)


def bind_comparison_selection(selection, catalog, product_ids, target,
                              policy_sha256, prompt_used_sha256, product_labels, *, raw_selection=None):
    if selection and any((item['reference'], item['frame']) not in {
            (row['reference_number'], row['frame_index']) for row in catalog} for item in selection):
        raise ValueError('比较答复选择超出冻结帧目录')
    facts = derive_facts(selection, catalog, product_ids)
    result = compare_facts(target, product_ids, facts)
    answer = render_comparison_answer(result, product_labels)
    proof = create_comparison_proof(target, policy_sha256, prompt_used_sha256,
        selection, facts, result, answer)
    if raw_selection is not None:
        proof['raw_selection'] = raw_selection
    return answer, proof


def validate_saved_comparison(row, catalog, product_ids, target,
                              policy_sha256, prompt_used_sha256, product_labels):
    saved = row.get('comparison_answer') or {}
    raw = saved.get('raw_selection')
    if raw is None and saved.get('selected_frames') == [] and not catalog:
        answer, expected = bind_comparison_selection([], catalog, product_ids, target,
            policy_sha256, prompt_used_sha256, product_labels)
    elif isinstance(raw, str):
        answer, expected = bind_comparison_response(raw, catalog, product_ids, target,
            policy_sha256, prompt_used_sha256, product_labels)
        expected['raw_selection'] = raw
    else:
        raise ValueError('恢复核验缺少原始帧选择')
    if saved != expected or row.get('answer') != answer:
        raise ValueError('恢复比较事实、来源或渲染答案发生漂移')
    return saved


def comparison_failure_record(raw, prompt, reference_map, policy, failure_code):
    raw = raw if isinstance(raw, str) else ''
    from .evidence_attribution import payload
    return dict(function_version=VERSION, raw_selection=raw[:MAX_SELECTION_CHARS],
        received_chars=len(raw), failure_code=failure_code,
        input_sha256=fingerprint(dict(prompt_sha256=fingerprint(prompt),
            reference_map_sha256=fingerprint(reference_map or []),
            evidence_attribution_sha256=fingerprint(payload(policy)))))
