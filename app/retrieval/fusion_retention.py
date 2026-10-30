"""显式隔离对照入口；未接默认策略。保留分路首条后按 weighted 原序填池。"""
from copy import deepcopy

from .adapters import score_record, stable_key, traced_hybrid


def retain_branch_heads(weighted, dense, sparse, *, limit, revision_ids, product_ids):
    """只重选固定池，不重新融合分数；调用方仍负责正式范围与索引授权。"""
    if type(limit) is not int or limit < 1:
        raise ValueError('融合保留预算必须为正整数')
    revisions, products = set(revision_ids), set(product_ids)
    payloads = {}
    for raw in [*weighted, *dense, *sparse]:
        entity = raw.get('entity', raw)
        key = stable_key(entity)
        metadata = entity.get('metadata', {})
        owners = set(metadata.get('product_ids', []))
        if not all(key) or key[1] not in revisions or not owners or not owners <= products:
            raise ValueError('融合保留证据超出授权范围')
        if any(ref.get('revision_id') != key[1] or ref.get('document_id') != key[0]
               for ref in metadata.get('source_refs', [])):
            raise ValueError('融合保留来源超出授权身份')
        if key in payloads and payloads[key] != entity:
            raise ValueError('同一身份对应不同正文或来源')
        payloads[key] = entity
    weighted_traced = traced_hybrid(weighted, dense, sparse)
    by_key = {stable_key(r.get('entity', r)): r for r in reversed(weighted_traced)}
    selected, seen = [], set()
    heads = [rows[0] for rows in (dense, sparse) if rows]
    if len({stable_key(r.get('entity', r)) for r in heads}) > limit:
        raise ValueError('融合预算无法保留非空分路首条')
    for raw in [*heads, *weighted]:
        key = stable_key(raw.get('entity', raw))
        if key in seen:
            continue
        if len(selected) == limit:
            break
        item = deepcopy(by_key.get(key, raw))
        if key not in by_key:
            # 分路 IP 仍为分路 IP，不能冒充后端未返回的 weighted 分数。
            item['retrieval_trace'] = [
                score_record(channel, rank, row.get('distance', row.get('score')), 'inner_product')
                for channel, rows in [('dense', dense), ('learned_sparse', sparse)]
                for rank, row in enumerate(rows, 1) if stable_key(row.get('entity', row)) == key]
        item['retrieval_trace'].append(score_record('branch_heads_v1', len(selected) + 1,
                                                   None, 'rank_only'))
        selected.append(item)
        seen.add(key)
    return selected
