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


def retain_source_prerequisites(seeds, rows, *, max_added=4, max_chars=6000):
    """显式隔离对照用：只补原文封面日期及表格最近对象介绍，默认路径不启用。

    rows必须来自调用方已授权的修订快照；不改索引、正文或重排分数。
    日期仅代表封面日期，不推定有效版本/兼容范围；未识别关系不猜填。
    返回的groups必须传给最终prompt预算，前提与依赖证据原子装入。
    """
    import re
    if (len(rows)>1000 or len(seeds)>20 or type(max_added) is not int or not 0<=max_added<=20
        or type(max_chars) is not int or not 0<=max_chars<=12000):
        raise ValueError('来源前提输入或预算超限')
    known={}
    for hit in [*rows,*seeds]:
        if any(ref.get('document_id')!=hit.document_id or ref.get('revision_id')!=hit.revision_id
               for ref in hit.metadata.get('source_refs',[])):
            raise ValueError('来源前提定位跨资料/修订')
        prior=known.get(hit.identity)
        if prior and (prior.text,prior.metadata,prior.ordinal)!=(hit.text,hit.metadata,hit.ordinal):
            raise ValueError('来源前提同身份载荷冲突')
        known[hit.identity]=hit

    def pages(hit):
        refs=hit.metadata.get('source_refs',[])
        return [r['page'] for r in refs if r.get('kind')=='pdf' and r.get('page')]
    def primary(hit):
        refs=hit.metadata.get('source_refs',[])
        return bool(refs and pages(hit) and all(r.get('kind')=='pdf' for r in refs))
    def same_scope(a,b):
        return (a.document_id,a.revision_id,sorted(a.metadata.get('product_ids',[])))==(
            b.document_id,b.revision_id,sorted(b.metadata.get('product_ids',[])))
    date=re.compile(r'(?:19|20)\d{2}\s*年\s*\d{1,2}\s*月(?:\s*\d{1,2}\s*日)?')
    intro=re.compile(r'^(?:了解|认识|介绍)\s+\S[^\n]{0,120}$',re.M)
    result=EvidenceSelection();selected={};added=set();seed_ids={s.identity for s in seeds}
    for seed in seeds:
        eligible=[h for h in known.values() if same_scope(h,seed) and primary(h)] if primary(seed) else []
        prerequisites=[];relations={}
        dates=[h for h in eligible if pages(h)==[1] and len(h.text)<=512
               and any(date.fullmatch(line.strip()) for line in h.text.splitlines())]
        if len(dates)==1:
            prerequisites.append(dates[0]);relations[dates[0].identity]='cover_date'
        if seed.metadata.get('content_kind')=='table' and seed.ordinal is not None:
            preceding=sorted([h for h in eligible if h.ordinal is not None
                and 0<seed.ordinal-h.ordinal<=12],key=lambda h:h.ordinal,reverse=True)
            for candidate in preceding:
                if candidate.metadata.get('heading_path')!=seed.metadata.get('heading_path'):break
                if max(pages(seed))-min(pages(candidate))>1:break
                if intro.search(candidate.text):
                    prerequisites.append(candidate);relations[candidate.identity]='table_object';break
        group=[];seen=set()
        for h in [*prerequisites,seed]:
            if h.identity not in seen:group.append(h);seen.add(h.identity)
        fresh=[h for h in group if h.identity not in selected]
        new_added={h.identity for h in fresh if h.identity not in seed_ids}
        if len(added|new_added)>max_added or not fits_context([*selected.values(),*fresh],max_chars):
            result.excluded.append(dict(chunk_uid=seed.chunk_uid,reason='source_prerequisite_budget'));continue
        for h in fresh:
            if h.identity not in seed_ids:
                h=h.model_copy(deep=True,update={'stages':[*h.stages,StageScore(stage='source_prerequisite',
                    rank=len(result.expanded)+1,score_kind=relations[h.identity])]})
                result.expanded.append(h);added.add(h.identity)
            selected[h.identity]=h;result.selected.append(h)
        result.groups.append([h.chunk_uid for h in group])
    return result
