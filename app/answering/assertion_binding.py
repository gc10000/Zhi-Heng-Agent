"""默认关闭的原句选择与程序渲染：模型不能提交自由结论或跨引用组装关系。"""
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.knowledge.models import content_hash
from app.knowledge.repository import fingerprint
from .source_relations import extract_frames

VERSION = 'assertion_binding_v1'
MAX_SELECTION_CHARS = 4096
INSUFFICIENT_ANSWER = '当前授权知识库中没有找到可用证据，请补充资料或明确设备型号。'


class AssertionBindingPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    enabled: bool = Field(default=False, strict=True)
    function_version: Literal['assertion_binding_v1'] = VERSION


class Selection(BaseModel):
    model_config = ConfigDict(extra='forbid')
    references: list[int] = Field(min_length=1, max_length=20)


def checked_sources(reference_map, docs, policy=None):
    """原文、关系跨度及连续编号与实际输入全等；不信任模型自报的关系字段。"""
    if not docs or len(reference_map) != len(docs):
        raise ValueError('原句选择缺少完整输入映射')
    attribution = None
    if policy is not None:
        from .evidence_attribution import EvidenceAttributionPolicy
        attribution = EvidenceAttributionPolicy.model_validate(policy)
        if not attribution.enabled or attribution.source_relations is None or not attribution.source_relations.enabled:
            raise ValueError('恢复核验缺少冻结来源关系策略')
    for number, (row, doc) in enumerate(zip(reference_map, docs), 1):
        relation = row.get('source_relations') or {}
        source = relation.get('source') or {}
        text = doc.get('text') or ''
        uid = doc.get('chunk_uid', doc.get('chunk_id'))
        expected = dict(document_id=doc.get('document_id'), revision_id=doc.get('revision_id'), chunk_uid=uid)
        refs=doc.get('source_refs',(doc.get('metadata') or {}).get('source_refs',[])) or []
        pages=sorted({r['page'] for r in refs if r.get('kind')=='pdf' and type(r.get('page')) is int and r['page']>0})
        exact=bool(refs) and all(r.get('kind')=='pdf' and type(r.get('page')) is int and r['page']>0 for r in refs)
        if (type(row.get('reference_number')) is not int or row['reference_number'] != number or
                any(row.get(k) != v or source.get(k) != v for k, v in expected.items()) or
                source.get('content_sha256') != content_hash(text.encode('utf-8')) or
                source.get('original_sha256') != row.get('original_sha256') or
                source.get('source_refs_sha256') != fingerprint(refs) or
                row.get('physical_pages') != pages or row.get('page_status') != ('exact' if exact else 'unknown') or
                relation.get('frames') != extract_frames(text) or
                (attribution is not None and source.get('payload_sha256') !=
                 attribution.source_relations.frozen_payloads.get(uid))):
            raise ValueError('原句选择的来源、内容或关系跨度漂移')
    return reference_map


def render_assertion_matrix(reference_map):
    """只呈现已有抽取类型，connection不自动升级为上联，不猜测实体类别。"""
    lines = []
    for row in reference_map:
        kinds = list(dict.fromkeys(f['kind'] for f in (row.get('source_relations') or {}).get('frames', [])))
        lines.append(f"[{row['reference_number']}] 原句索引类型=" + ','.join(kinds or ['unknown']) +
                     '；选择该编号时保留整个原段及条件，不拼接其他引用的字段。')
    return '\n'.join(lines)


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('选择协议不接受重复字段')
        value[key] = item
    return value


def bind_response(raw, reference_map, docs, policy=None):
    """只接受严格编号选择JSON；程序引用完整原段，不生成新的网络关系结论。

    通过仅证明没有新增关系断言，不证明所选内容相关、完整或优于旧答案。
    """
    checked_sources(reference_map, docs, policy)
    if not isinstance(raw, str) or len(raw) > MAX_SELECTION_CHARS:
        raise ValueError('原句选择输出缺失或超长')
    value = json.loads(raw, object_pairs_hook=_unique_object)
    if not isinstance(value, dict) or set(value) != {'references'}:
        raise ValueError('只允许原句编号选择，不能附带自由文本')
    numbers = value['references']
    if (not isinstance(numbers, list) or not 1 <= len(numbers) <= 20 or
            any(type(n) is not int or not 1 <= n <= len(reference_map) for n in numbers) or
            len(set(numbers)) != len(numbers)):
        raise ValueError('原句选择须为不重复的实际引用编号')
    Selection.model_validate(value)
    blocks = ['以下为本轮资料中的直接记载。客户端访问、设备连接和条件检查分别保留；原句未明确的关系仍不确定。']
    for number in numbers:
        text = docs[number-1]['text']
        # 动态围栏完整包住原段，避免原文内编号、代码、图片或资料内指令被执行/重配。
        fence = '`' * max(3, max((len(m.group()) for m in re.finditer(r'`+', text)), default=0) + 1)
        blocks.append(f'原文依据 [{number}]：\n{fence}text\n{text}\n{fence}')
    blocks.append('上述原文不据此推断新的上联方式或现场链路状态；摘录本身不代替完整比较结论。')
    blocks.append('资料来源：'+'；'.join(f'[{n}] 物理页：'+(
        '、'.join(str(page) for page in reference_map[n-1]['physical_pages'])
        if reference_map[n-1]['page_status']=='exact' else 'unknown') for n in numbers))
    answer = '\n\n'.join(blocks)
    proof = dict(function_version=VERSION, selected_references=numbers,
                 raw_selection_sha256=fingerprint(raw), reference_map_sha256=fingerprint(reference_map),
                 answer_sha256=fingerprint(answer))
    return answer, proof


def failure_record(raw, prompt, reference_map, policy, failure_code):
    raw = raw if isinstance(raw, str) else ''
    return dict(function_version=VERSION, raw_selection=raw[:MAX_SELECTION_CHARS],
                received_chars=len(raw), failure_code=failure_code,
                input_sha256=fingerprint(dict(prompt_sha256=fingerprint(prompt),
                    reference_map_sha256=fingerprint(reference_map or []),
                    evidence_attribution_sha256=fingerprint(policy.model_dump(mode='json')))))


def insufficient_evidence_binding(answer):
    if answer != INSUFFICIENT_ANSWER:
        raise ValueError('不足证据结果不匹配固定答案')
    return dict(function_version=VERSION, status='insufficient_evidence', selected_references=[],
                raw_selection_sha256=None, reference_map_sha256=fingerprint([]),
                answer_sha256=fingerprint(answer))


def validate_saved_binding(row, current_policy=None):
    """首次投影与恢复复用同一证明；旧配置没有该字段，结果身份保持原样。"""
    policy = (row.get('evidence_attribution') or {}).get('assertion_binding') or {}
    if not policy.get('enabled'):
        return None
    from .evidence_attribution import payload, validate_run_attribution
    current = current_policy if current_policy is not None else row.get('evidence_attribution')
    if current_policy is not None or 'evidence_attribution_sha256' in row:
        validate_run_attribution(row, current)
    saved = row.get('answer_binding') or {}
    if saved.get('status') == 'insufficient_evidence':
        if row.get('prompt_reference_map') != [] or row.get('citations') != []:
            raise ValueError('不足证据结果不得携带虚构来源')
        expected = insufficient_evidence_binding(row.get('answer'))
        if saved != expected:
            raise ValueError('不足证据结果证明漂移')
        return saved
    raw = saved.get('raw_selection')
    from .evidence_attribution import evidence_labels
    docs = row.get('prompt_used_docs')
    if not docs:
        raise ValueError('恢复核验缺少完整原始输入载荷')
    policy_payload = payload(current)
    expected_map = [dict(label, reference_number=n+1) for n,label in enumerate(evidence_labels(docs,policy_payload))]
    if expected_map != row.get('prompt_reference_map'):
        raise ValueError('恢复输入与冻结来源映射不一致')
    citations = row.get('citations') or []
    expected_citations = [(d.get('chunk_uid',d.get('chunk_id')),d.get('document_id'),d.get('revision_id'),d.get('text'),
                           d.get('source_refs',(d.get('metadata') or {}).get('source_refs',[])),d.get('asset_ids',[])) for d in docs]
    actual_citations = [(d.get('chunk_uid'),d.get('document_id'),d.get('revision_id'),d.get('text'),d.get('source_refs'),d.get('asset_ids')) for d in citations]
    if expected_citations != actual_citations:
        raise ValueError('恢复引用与冻结原始输入不一致')
    answer, proof = bind_response(raw, row.get('prompt_reference_map') or [], docs, policy_payload)
    if saved != proof | dict(raw_selection=raw) or answer != row.get('answer'):
        raise ValueError('原句约束结果或证明漂移，不允许恢复复用')
    return saved
