"""零推理比较上下文隔离对照；不接入默认策略，不更改分数或原始追踪。"""
from dataclasses import dataclass, field
import json
import re

from .selection import select_context


@dataclass
class CompareContextSelection:
    selected: list
    applied: bool = False
    protected: list[dict] = field(default_factory=list)
    missing_heads: list[dict] = field(default_factory=list)


def _pools(hit, scopes, query_count):
    pools = set()
    for stage in hit.stages:
        if stage.stage != 'candidate_pool':
            continue
        try:
            value = json.loads(stage.query_id)
            scope, query = value['scope'], value['query']
            if (set(value) != {'scope', 'query'} or not isinstance(scope, list)
                    or not all(isinstance(p, str) for p in scope)
                    or scope != sorted(set(scope)) or tuple(scope) not in scopes
                    or type(query) is not int or not 0 <= query < query_count
                    or stage.rank is None):
                raise ValueError()
        except (ValueError, KeyError, TypeError):
            raise ValueError('比较候选scope/query追踪无效') from None
        if not set(hit.metadata['product_ids']) & set(scope):
            raise ValueError('比较候选scope与产品不一致')
        pools.add((tuple(scope), query))
    if not pools:
        raise ValueError('比较候选缺少scope/query追踪')
    return pools


def select_compare_branch_context(ranked, *, candidates, plan, limit=10):
    """先各scope重排首证，再真实分路rank1，最后原重排顺序填充。

    调用方必须提供同次已授权检索的规范候选快照；本函数不创建授权，
    仅核验快照内的完整身份与追踪。未进重排的首证只记缺失，不补取。
    """
    if type(limit) is not int or limit < 1:
        raise ValueError('比较上下文预算必须为正整数')
    if plan.route != 'compare' or len(plan.scope_groups) < 2:
        return CompareContextSelection(selected=select_context(
            ranked, limit=limit, scope_groups=plan.scope_groups if plan.route == 'compare' else (),
            mode='scope_first_v1'))
    scopes = [tuple(sorted(scope)) for scope in plan.scope_groups]
    allowed = set(plan.product_ids)
    if (plan.unconfirmed_tokens or not plan.search_queries or not plan.revision_ids
            or any(not scope or len(set(scope)) != len(scope) for scope in scopes)
            or len({p for scope in scopes for p in scope}) != sum(map(len, scopes))
            or {p for scope in scopes for p in scope} != allowed):
        raise ValueError('比较主体或授权范围未确认')
    originals, heads, trace_ranks = {}, {}, {}
    scope_by_prefix = {scope[0]: scope for scope in scopes}
    for hit in candidates:
        if hit.identity in originals:
            raise ValueError('比较候选身份重复或载荷冲突')
        owners = set(hit.metadata.get('product_ids', []))
        refs = hit.metadata.get('source_refs', [])
        if (hit.revision_id not in plan.revision_ids or not owners or not owners <= allowed
                or not refs or any(ref.get('document_id') != hit.document_id
                    or ref.get('revision_id') != hit.revision_id for ref in refs)):
            raise ValueError('比较候选产品/修订/来源超出授权')
        pools = _pools(hit, scopes, len(plan.search_queries))
        originals[hit.identity] = hit
        seen_stages = set()
        for stage in hit.stages:
            if stage.stage == 'candidate_pool':
                continue
            if stage.stage not in {'dense', 'learned_sparse', 'weighted_fusion', 'branch_heads_v1'}:
                raise ValueError('比较候选包含非本次加权检索追踪')
            match = re.fullmatch(r'product:([^/]+)/query:(0|[1-9]\d*)/original', stage.query_id)
            if match is None or stage.rank is None:
                raise ValueError('比较分路scope/query追踪不完整')
            prefix, query = match[1], int(match[2])
            scope = scope_by_prefix.get(prefix)
            if (scope, query) not in pools:
                raise ValueError('比较分路scope/query与候选池冲突')
            key = scope, query, stage.stage
            if key in seen_stages:
                raise ValueError('比较分路追踪重复或冲突')
            seen_stages.add(key)
            if stage.stage in {'dense', 'learned_sparse'}:
                if stage.score_kind != 'inner_product' or stage.score is None:
                    raise ValueError('比较分路缺少原始分数')
                rank_key = (*key, stage.rank)
                if rank_key in trace_ranks and trace_ranks[rank_key] != hit.identity:
                    raise ValueError('比较分路原始名次冲突')
                trace_ranks[rank_key] = hit.identity
                if stage.rank == 1:
                    heads[key] = hit
    reranked = {}
    for rank, hit in enumerate(ranked, 1):
        original = originals.get(hit.identity)
        if original is None or hit.identity in reranked:
            raise ValueError('比较重排包含未知或重复身份')
        if ((hit.text, hit.metadata, hit.ordinal) != (original.text, original.metadata, original.ordinal)
                or not hit.stages or hit.stages[:-1] != original.stages
                or hit.stages[-1].stage != 'rerank' or hit.stages[-1].rank != rank
                or hit.stages[-1].score_kind != 'model_relevance' or hit.stages[-1].score is None):
            raise ValueError('比较重排载荷、原始追踪或实际名次变化')
        reranked[hit.identity] = hit
    protected, reasons = [], {}

    def reserve(hit, reason):
        if hit.identity not in reasons:
            protected.append(hit)
            reasons[hit.identity] = []
        reasons[hit.identity].append(reason)

    for scope in scopes:
        best = next((h for h in ranked if set(h.metadata['product_ids']) & set(scope)), None)
        if best is not None:
            reserve(best, dict(kind='scope_rerank_head', scope=list(scope)))
    missing = []
    for scope in sorted(scopes):
        for query in range(len(plan.search_queries)):
            for channel in ('dense', 'learned_sparse'):
                head = heads.get((scope, query, channel))
                reason = dict(scope=list(scope), query=query, channel=channel, original_rank=1)
                if head is None:
                    missing.append(reason | dict(reason='head_unavailable_in_candidate_snapshot'))
                elif head.identity not in reranked:
                    missing.append(reason | dict(reason='head_not_reranked',
                        document_id=head.document_id, revision_id=head.revision_id, chunk_uid=head.chunk_uid))
                else:
                    reserve(reranked[head.identity], reason | dict(kind='branch_head'))
    if len(protected) > limit:
        raise ValueError('比较上下文预算无法覆盖全部保护首证')
    selected = list(protected)
    for hit in ranked:
        if len(selected) == limit:
            break
        if hit.identity not in reasons:
            selected.append(hit)
    return CompareContextSelection(selected=selected, applied=True,
        protected=[dict(document_id=h.document_id, revision_id=h.revision_id, chunk_uid=h.chunk_uid,
                        reasons=reasons[h.identity]) for h in protected], missing_heads=missing)
