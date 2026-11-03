"""从冻结来源帧派生比较事实；模型只选择帧，不提交语义断言。"""
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.knowledge.repository import fingerprint

VERSION = 'comparison_answer_v1'
VERSION_V2 = 'comparison_answer_v2'
VERSION_V3 = 'comparison_answer_v3'
_VERSION_V2_PLUS = (VERSION_V2, VERSION_V3)
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
    function_version: Literal['comparison_answer_v1', 'comparison_answer_v2', 'comparison_answer_v3'] = VERSION


def _checked_version(version):
    if version not in (VERSION, VERSION_V2, VERSION_V3):
        raise ValueError('比较解释版本不受支持')
    return version


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


def _exact_product_endpoint(endpoint, product_id, source_product_ids, product_label):
    # 简称仅来自冻结品牌+型号的末项，且必须是唯一产品来源中的完整端点。
    if not endpoint or not product_label or source_product_ids != [product_id]:
        return False
    words = product_label.split()
    model = words[-1]
    if endpoint.strip() == product_label:
        return True
    return (len(words) > 1 and bool(re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', model)) and
            bool(re.search(r'[A-Za-z]', model)) and bool(re.search(r'\d', model)) and
            endpoint.strip() == model)


def classify_frame(frame, clause, product_id, source_product_ids, product_label=None, *, version=VERSION):
    """按冻结原句帧分类；不能把连接、访问或检查推成设备上联。"""
    _checked_version(version)
    if not isinstance(frame, dict) or not isinstance(clause, str) or not product_id:
        raise ValueError('比较事实缺少有效帧、原句或产品身份')
    origin, destination = _field_text(frame, 'origin'), _field_text(frame, 'destination')
    medium, purpose = _field_text(frame, 'medium'), _field_text(frame, 'purpose')
    category = 'unknown'
    condition_text = clause
    if version in _VERSION_V2_PLUS:
        condition_text += '\n' + str((frame.get('scope') or {}).get('text') or '')
    belongs = _belongs_to_product(clause, product_id, source_product_ids, product_label)
    origin_matches = _origin_is_product(origin, clause, product_id, source_product_ids, product_label)
    if version in _VERSION_V2_PLUS:
        origin_matches = (_exact_product_endpoint(origin, product_id, source_product_ids, product_label) or
            bool(origin and (origin.strip() in _GENERIC_DEVICE_ORIGIN or
                 _GENERIC_UPLINK_ORIGIN.fullmatch(origin.strip())) and
                 (source_product_ids == [product_id] or bool(product_label and product_label in clause))))
    if belongs and frame.get('kind') == 'physical_check':
        category = 'diagnostic_check'
    elif belongs and not _NEGATION_OR_CONDITION.search(condition_text):
        if frame.get('kind') in {'access', 'login'} and destination:
            category = 'client_access'
        elif (version in _VERSION_V2_PLUS and frame.get('kind') == 'connection' and
              origin in {'您', '用户', '客户端', '电脑', '计算机', 'PC'} and
              _exact_product_endpoint(destination, product_id, source_product_ids, product_label)):
            category = 'client_access'
        elif (frame.get('kind') in {'service', 'connection'} and purpose and '管理' in purpose and
              origin and destination and
              origin_matches):
            category = 'management_link'
        elif (frame.get('kind') == 'connection' and
                re.search(r'上联|\buplink\b', clause, re.IGNORECASE) and
                not _NEGATION_OR_CONDITION.search(clause) and
                origin_matches and
                medium and destination):
            category = 'device_uplink'
    fact = dict(category=category, product_id=product_id, origin=origin,
        destination=destination, medium=medium, purpose=purpose,
        operational_status='unknown' if category == 'diagnostic_check' else None,
        clause=clause, scope=frame.get('scope'), frame_sha256=fingerprint(frame))
    if version == VERSION_V3:
        # 复述同一检查帧中已冻结的接线字段，不推断接入角色或现场状态。
        fact['documented_path'] = (dict(origin=origin, medium=medium, destination=destination,
            basis='diagnostic_instruction', operational_status='unknown')
            if category == 'diagnostic_check' and all((origin, medium, destination)) else None)
    return fact


def derive_facts(selection, catalog, product_ids, *, version=VERSION):
    _checked_version(version)
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
                item['source_product_ids'], label, version=version)
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


def compare_facts(target, product_ids, facts, *, version=VERSION):
    _checked_version(version)
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
    return dict(function_version=version, comparison_target=target, status=status,
        product_ids=list(product_ids), products={pid: by_product[pid] for pid in product_ids},
        compared=compared, missing=missing)


def _citation(fact):
    pages = fact.get('physical_pages') or []
    page_text = '、'.join(str(page) for page in pages) if fact.get('page_status') == 'exact' and pages else '页码未知'
    return f"[{fact['reference_number']}]（{page_text}）"


def _literal_field(value):
    """动态来源字段置于足够长的行内代码中，换行按JSON字面量显示。"""
    text = json.dumps(value, ensure_ascii=False)
    fence = '`' * max(1, 1 + max((len(m.group()) for m in re.finditer(r'`+', text)), default=0))
    return fence + text + fence


def _fact_description(fact, *, version=VERSION):
    category = fact.get('category', 'unknown')
    label = _CATEGORY_LABELS.get(category, _CATEGORY_LABELS['unknown'])
    if category == 'device_uplink':
        medium = _canonical_medium(fact.get('medium'))
        if medium:
            description = f"资料记载的上联介质为{_MEDIUM_LABELS[medium]}"
            return description
        return '资料有上联表述，但介质未能按当前比较范围确认'
    if category == 'management_link':
        if version == VERSION_V3:
            medium = fact.get('medium')
            destination = fact.get('destination')
            purpose = fact.get('purpose')
            details = []
            if medium and destination:
                details.append(f'通过{_literal_field(medium)}连接到{_literal_field(destination)}')
            if purpose:
                details.append(f'用于{_literal_field(purpose)}')
            if details:
                return f"资料记载{'，'.join(details)}，但这是管理连接证据，不等同设备上联"
        return f'资料记载{label}，不能据此认定设备上联方式'
    if category == 'client_access':
        return f'资料记载{label}，不能据此认定设备上联方式'
    if category == 'diagnostic_check':
        if version == VERSION_V3 and fact.get('documented_path'):
            path = fact['documented_path']
            return (f"排障条目涉及{_literal_field(path['origin'])}经"
                f"{_literal_field(path['medium'])}至{_literal_field(path['destination'])}的接线；"
                '这是资料描述的物理接线路径，不代表现场链路已经建立；条件与限制见原文')
        if version == VERSION_V3:
            return '资料描述的是排障检查条件，不代表现场链路已经建立'
        return '资料描述的是排障检查条件，不代表链路已经连接'
    return '资料原句的关系类别未能按当前规则确定'


def render_comparison_answer(result, product_labels):
    version = _checked_version(result.get('function_version'))
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
    if version == VERSION_V3 and status == 'insufficient_comparison':
        management = {pid for pid, facts in result['products'].items()
            if any(f.get('category') == 'management_link' for f in facts)}
        paths = {pid for pid, facts in result['products'].items()
            if any(f.get('documented_path') for f in facts)}
        if any(left != right for left in management for right in paths):
            lines.append('两份资料明确描述的关系不同：一方为管理连接，另一方为排障指令中的物理接线路径。'
                '资料未说明该排障路径是否已建立或其是否承担设备上联。'
                '下面只列资料明确写出的介质、对端和管理用途；这些证据仍不足以比较双方同一用途的设备上联。')
    if version in _VERSION_V2_PLUS:
        categories = {f.get('category') for facts in result['products'].values() for f in facts}
        if {'client_access', 'management_link'} <= categories:
            lines.append('资料中的客户端接入与管理连接属于不同关系，不能据此认定两台设备的上联方式相同或不同。')
    for product_id in names:
        label = product_labels.get(product_id, product_id)
        if version == VERSION_V3:
            label = _literal_field(label)
        facts = result['products'][product_id]
        usable = [fact for fact in facts if fact.get('category') in _CATEGORY_LABELS]
        if version in _VERSION_V2_PLUS:
            usable = sorted(usable, key=lambda f: (f['reference_number'], f['frame_index']))
        shown_scopes = set()
        if not usable:
            lines.append(f'{label}：本轮引用资料中没有可用的关系记录。')
            continue
        for fact in usable:
            description = _fact_description(fact, version=version)
            if version in _VERSION_V2_PLUS and fact.get('category') == 'unknown':
                description = '资料记载如下，现有信息不足以将其作为设备上联依据'
            lines.append(f"{label}：{description}{_citation(fact)}。")
            if version in _VERSION_V2_PLUS:
                text = fact.get('scoped_text')
                if not isinstance(text, str) or not text:
                    raise ValueError('新比较呈现缺少完整来源范围')
                source_key = (fact['reference_number'], text)
                if source_key in shown_scopes:
                    continue
                shown_scopes.add(source_key)
                fence = '`' * max(3, 1 + max((len(m.group()) for m in re.finditer(r'`+', text)), default=0))
                lines.append(f'\n{fence}text\n{text}\n{fence}\n')
    if status == 'insufficient_comparison':
        missing = [(_literal_field(product_labels.get(pid, pid)) if version == VERSION_V3
                    else product_labels.get(pid, pid)) for pid, reason in result['missing'].items() if reason]
        if missing:
            lines.append('缺少可比较的设备上联介质证据：' + '、'.join(missing) + '。')
    return '\n'.join(lines)


def create_comparison_proof(target, policy_sha256, prompt_used_sha256,
                            selection, facts, result, answer, *, version=VERSION):
    _checked_version(version)
    if target != result.get('comparison_target') or result.get('function_version') != version:
        raise ValueError('比较proof目标或实现版本不一致')
    for value in (policy_sha256, prompt_used_sha256):
        if not isinstance(value, str) or not re.fullmatch(r'[a-f0-9]{64}', value):
            raise ValueError('比较proof输入身份hash无效')
    expected_facts = fingerprint(facts)
    if result.get('products') is None:
        raise ValueError('比较proof缺少派生事实结果')
    suffix = 'v3' if version == VERSION_V3 else 'v2' if version == VERSION_V2 else 'v1'
    return dict(function_version=version, schema_version=SCHEMA_VERSION,
        classifier_version='source_frame_classifier_' + suffix, comparator_version='same_uplink_medium_v1',
        renderer_version='comparison_answer_renderer_' + suffix, comparison_target=target,
        policy_sha256=policy_sha256, prompt_used_sha256=prompt_used_sha256,
        selection_sha256=fingerprint(selection), facts_sha256=expected_facts,
        result_sha256=fingerprint(result), answer_sha256=fingerprint(answer),
        selected_frames=selection, comparison_status=result['status'])


def bind_comparison_response(raw_json, catalog, product_ids, target,
                             policy_sha256, prompt_used_sha256, product_labels, *, version=VERSION):
    selection = validate_frame_selection(raw_json, catalog)
    return bind_comparison_selection(selection, catalog, product_ids, target,
        policy_sha256, prompt_used_sha256, product_labels, raw_selection=raw_json, version=version)


def bind_comparison_selection(selection, catalog, product_ids, target,
                              policy_sha256, prompt_used_sha256, product_labels, *, raw_selection=None, version=VERSION):
    if selection and any((item['reference'], item['frame']) not in {
            (row['reference_number'], row['frame_index']) for row in catalog} for item in selection):
        raise ValueError('比较答复选择超出冻结帧目录')
    rendered = list(selection)
    supplemental = []
    if version in _VERSION_V2_PLUS:
        # 完整性由冻结目录的已识别关系保证，不依赖模型恰好选中必要帧。
        selected_ids = {(x['reference'], x['frame']) for x in selection}
        all_selection = [dict(reference=x['reference_number'], frame=x['frame_index']) for x in catalog]
        known_ids = {(f['reference_number'], f['frame_index']) for f in
            derive_facts(all_selection, catalog, product_ids, version=version) if f['category'] != 'unknown'}
        supplemental = [x for x in all_selection if
            (x['reference'], x['frame']) in known_ids - selected_ids]
        rendered += supplemental
    facts = derive_facts(rendered, catalog, product_ids, version=version)
    result = compare_facts(target, product_ids, facts, version=version)
    answer = render_comparison_answer(result, product_labels)
    proof = create_comparison_proof(target, policy_sha256, prompt_used_sha256,
        selection, facts, result, answer, version=version)
    if version in _VERSION_V2_PLUS:
        proof.update(coverage_version='known_frozen_relations_v1', catalog_sha256=fingerprint(catalog),
            supplemental_frames=supplemental, rendered_frames=rendered)
    if raw_selection is not None:
        proof['raw_selection'] = raw_selection
    return answer, proof


def validate_saved_comparison(row, catalog, product_ids, target,
                              policy_sha256, prompt_used_sha256, product_labels, *, version=VERSION):
    saved = row.get('comparison_answer') or {}
    raw = saved.get('raw_selection')
    if raw is None and saved.get('selected_frames') == [] and not catalog:
        answer, expected = bind_comparison_selection([], catalog, product_ids, target,
            policy_sha256, prompt_used_sha256, product_labels, version=version)
    elif isinstance(raw, str):
        answer, expected = bind_comparison_response(raw, catalog, product_ids, target,
            policy_sha256, prompt_used_sha256, product_labels, version=version)
        expected['raw_selection'] = raw
    else:
        raise ValueError('恢复核验缺少原始帧选择')
    if saved != expected or row.get('answer') != answer:
        raise ValueError('恢复比较事实、来源或渲染答案发生漂移')
    return saved


def comparison_failure_record(raw, prompt, reference_map, policy, failure_code):
    raw = raw if isinstance(raw, str) else ''
    from .evidence_attribution import payload
    from .evidence_attribution import EvidenceAttributionPolicy
    comparison = EvidenceAttributionPolicy.model_validate(policy).comparison_answer
    version = comparison.function_version if comparison else VERSION
    return dict(function_version=version, raw_selection=raw[:MAX_SELECTION_CHARS],
        received_chars=len(raw), failure_code=failure_code,
        input_sha256=fingerprint(dict(prompt_sha256=fingerprint(prompt),
            reference_map_sha256=fingerprint(reference_map or []),
            evidence_attribution_sha256=fingerprint(payload(policy)))))
