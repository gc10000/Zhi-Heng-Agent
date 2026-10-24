"""只展开同授权/资料/修订/型号的父块和有限相邻块，不递归整章。"""
import os
from pydantic import BaseModel, ConfigDict, Field
from .models import RetrievalHit, StageScore
from app.answering.evidence import EvidenceSelection, fits_context, diverse_seeds


class ExpansionPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    enabled: bool = Field(default=False, strict=True)
    max_chars: int = Field(default=6000, ge=1, le=12000, strict=True)
    max_added: int = Field(default=4, ge=0, le=20, strict=True)
    radius: int = Field(default=1, ge=0, le=2, strict=True)
    max_seeds: int = Field(default=10, ge=1, le=20, strict=True)

    @classmethod
    def load(cls):
        raw = os.getenv('EVIDENCE_EXPANSION_JSON', '').strip()
        if not raw: return cls()
        try: return cls.model_validate_json(raw)
        except ValueError:
            raise ValueError('EVIDENCE_EXPANSION_JSON必须为有效有界JSON，详见配置文档') from None


def _relation(seed, hit, radius):
    if (hit.document_id, hit.revision_id) != (seed.document_id, seed.revision_id): return None
    if sorted(hit.metadata.get('product_ids', [])) != sorted(seed.metadata.get('product_ids', [])): return None
    section = seed.metadata.get('section_id')
    same_section = bool(section and section == hit.metadata.get('section_id'))
    heading = seed.metadata.get('heading_path')
    same_heading = bool(heading and heading == hit.metadata.get('heading_path'))
    if hit.chunk_uid == seed.metadata.get('parent_chunk_uid') and same_section: return 'parent'
    if hit.metadata.get('parent_chunk_uid') == seed.chunk_uid and same_section: return 'child'
    if (seed.ordinal is not None and hit.ordinal is not None
        and 0 < abs(seed.ordinal-hit.ordinal) <= radius and (same_section or same_heading)):
        return 'adjacent'
    return None


def expand_evidence(ranked, *, loader, owner_id, kb_id, policy):
    policy = ExpansionPolicy.model_validate(policy)
    if not policy.enabled: return EvidenceSelection(selected=list(ranked))
    seeds = diverse_seeds(ranked, policy.max_seeds)
    rows = loader(seeds, radius=policy.radius) if seeds else []
    known = {h.identity: h for h in ranked}
    loaded = {}
    for raw in rows:
        if raw.get('owner_id') != owner_id or raw.get('kb_id') != kb_id:
            raise ValueError('扩展候选超出归属/知识库')
        hit = RetrievalHit(**{k: raw[k] for k in ('document_id','revision_id','chunk_uid','text')},
            ordinal=raw.get('ordinal'), metadata=raw.get('metadata', {}))
        if any(ref.get('document_id') not in (None,hit.document_id) or ref.get('revision_id') not in (None,hit.revision_id)
               for ref in hit.metadata.get('source_refs', [])):
            raise ValueError('扩展来源跨资料/修订')
        if not any(_relation(seed, hit, policy.radius) or seed.identity == hit.identity for seed in seeds):
            # 防御不可信/过宽的加载端口，不能将整修订或相邻型号塞入。
            continue
        prior = known.get(hit.identity) or loaded.get(hit.identity)
        if prior and (prior.text,prior.metadata,prior.ordinal) != (hit.text,hit.metadata,hit.ordinal):
            raise ValueError('扩展同身份载荷不一致')
        loaded[hit.identity] = prior or hit
    result = EvidenceSelection()
    chosen, expanded = set(), set()
    for seed in seeds:
        related = [(h, _relation(seed,h,policy.radius)) for h in loaded.values() if h.identity != seed.identity]
        related = [(h, relation) for h,relation in related if relation]
        related.sort(key=lambda pair:(0 if pair[1]=='parent' else 1, pair[0].ordinal or 0, pair[0].chunk_uid))
        parent_uid = seed.metadata.get('parent_chunk_uid')
        required = [(h,r) for h,r in related if r == 'parent']
        if parent_uid and parent_uid != seed.chunk_uid and not required:
            result.excluded.append(dict(chunk_uid=seed.chunk_uid, reason='parent_unavailable')); continue
        prerequisites = [h for h,_ in required if h.identity not in chosen]
        group = prerequisites + ([] if seed.identity in chosen else [seed])
        new_parent = sum(h.identity not in known and h.identity not in expanded for h in prerequisites)
        if len(expanded)+new_parent > policy.max_added or not fits_context(result.selected+group,policy.max_chars):
            result.excluded.append(dict(chunk_uid=seed.chunk_uid, reason='prerequisite_budget')); continue
        relations = {h.identity:r for h,r in related}
        # 前提是必需组；相邻证据逐个有界尝试，不妨碍后续不同资料种子。
        for hit in group:
            if hit.identity not in known:
                hit = hit.model_copy(deep=True,update={'stages':[StageScore(stage='expansion',
                    rank=len(result.expanded)+1,score_kind=relations.get(hit.identity,'related'))]})
                result.expanded.append(hit); expanded.add(hit.identity)
            result.selected.append(hit); chosen.add(hit.identity)
        result.groups.append([h.chunk_uid for h in group])
    # 所有种子优先获得预算，最后才添加可选相邻块，避免一条资料独占。
    for seed in seeds:
        if seed.identity not in chosen: continue
        for hit in sorted(loaded.values(),key=lambda h:(h.ordinal or 0,h.chunk_uid)):
            relation = _relation(seed,hit,policy.radius)
            if not relation or hit.identity in chosen: continue
            parent_uid = hit.metadata.get('parent_chunk_uid')
            if parent_uid and parent_uid != hit.chunk_uid and (hit.document_id,hit.revision_id,parent_uid) not in chosen:
                # 相邻块也受前提约束，不能从另一条链的中间片绕过父块。
                continue
            if hit.identity not in known and len(expanded) >= policy.max_added: continue
            if not fits_context(result.selected+[hit],policy.max_chars): continue
            if hit.identity not in known:
                hit = hit.model_copy(deep=True,update={'stages':[StageScore(stage='expansion',
                    rank=len(result.expanded)+1,score_kind=relation)]})
                result.expanded.append(hit); expanded.add(hit.identity)
            result.selected.append(hit); chosen.add(hit.identity)
    return result
