"""拒绝把模型内部处理规则作为产品事实发布；不改写或删减答案。"""
import re

from app.knowledge.repository import fingerprint


VERSION = 'answer_surface_guard_v1'
_INTERNAL_REFERENCES = re.compile(
    r'归属与完整断言(?:合同|规则)|(?:合同|规则)\s*第\s*[0-9一二三四五六七八九十百]+\s*条|'
    r'attributed_assertions_v1|source_relation_spans_v1|'
    r'(?:根据|依据|按照)\s*(?:本)?(?:提示词|内部规则|系统规则|模型规则)'
)


def failure_code(answer, source_docs):
    if not isinstance(answer, str):
        raise ValueError('模型回答必须是文本')
    source_texts = [doc.get('text') or '' for doc in source_docs]
    for match in _INTERNAL_REFERENCES.finditer(answer):
        if not any(match.group() in text for text in source_texts):
            return 'internal_rule_leak'
    return None


def failure_record(answer, prompt, reference_map, policy, code):
    return dict(
        function_version=VERSION,
        failure_code=code,
        answer_sha256=fingerprint(answer),
        input_sha256=fingerprint(dict(
            prompt_sha256=fingerprint(prompt),
            reference_map_sha256=fingerprint(reference_map or []),
            evidence_attribution_sha256=fingerprint(policy.model_dump(mode='json')),
        )),
    )
