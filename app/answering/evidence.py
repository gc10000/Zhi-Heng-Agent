"""证据组完整装入预算；去重按身份，不能为省字截断表格或图片。"""
from dataclasses import dataclass, field
from app.retrieval.models import RetrievalHit
from .context_budget import pack_prompt_inputs


@dataclass
class EvidenceSelection:
    selected: list[RetrievalHit] = field(default_factory=list)
    expanded: list[RetrievalHit] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    groups: list[list[str]] = field(default_factory=list)


def fits_context(hits, max_chars):
    packed = pack_prompt_inputs([h.document() for h in hits], [], max_chars)
    return len(packed['used_doc_indices']) == len(hits)


def diverse_seeds(hits, limit):
    """保持单资料排名；多资料轮流取首条，避免单资料独占扩展预算。"""
    groups = {}
    for hit in hits:
        groups.setdefault((hit.document_id, hit.revision_id), []).append(hit)
    result = []
    while groups and len(result) < limit:
        for key in list(groups):
            result.append(groups[key].pop(0))
            if not groups[key]: del groups[key]
            if len(result) == limit: break
    return result
