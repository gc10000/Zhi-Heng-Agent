"""按范围、分支/查询分层轮转；异量纲分数不参与跨池比较。"""
from collections import deque
import json


def select_context(ranked, *, limit, scope_groups, mode='global'):
    """保持实际重排分数及来源，在总数不变时先保留各比较对象的首条。

    不为缺少召回的对象补造证据，也不将入选解释为相关性达标。
    """
    if mode not in {'global','scope_first_v1'} or type(limit) is not int or limit<1:
        raise ValueError('上下文选择策略或预算无效')
    if mode=='global' or len(scope_groups)<2:return list(ranked[:limit])
    allowed={pid for scope in scope_groups for pid in scope}
    if any(not hit.metadata.get('product_ids') or not set(hit.metadata['product_ids'])<=allowed for hit in ranked):
        raise ValueError('比较上下文证据产品超出授权范围')
    selected=[];seen=set()
    for scope in scope_groups:
        best=next((h for h in ranked if set(h.metadata['product_ids']) & set(scope)),None)
        if best is not None and best.identity not in seen:
            selected.append(best);seen.add(best.identity)
    if len(selected)>limit:raise ValueError('上下文预算不能覆盖已召回比较范围')
    for hit in ranked:
        if len(selected)>=limit:break
        if hit.identity not in seen:selected.append(hit);seen.add(hit.identity)
    return selected


def select_candidates(candidates, limit):
    """每个非空范围先获一个机会，再轮流消费各池的未选身份。

    重复证据保留全部来源追踪，范围内由首个规范池负责（本地优先，再
    HyDE/分解及查询序号），避免多个增强池用共享前缀耗尽唯一证据的
    机会。跨范围仍按全局身份去重。兼容输入保留原顺序，不伪造排名。
    """
    scopes = {}
    branches = {'local': 0, 'hyde': 1, 'decomposition': 2}
    for ordinal, hit in enumerate(candidates):
        pools = [s for s in hit.stages if s.stage == 'candidate_pool']
        memberships = []
        for stage in pools:
            branch, payload = 'local', stage.query_id
            if payload.startswith('branch:'):
                prefix, payload = payload.split('/', 1)
                branch = prefix.removeprefix('branch:')
            value = json.loads(payload)
            if branch not in branches or stage.rank is None:
                raise ValueError('候选池追踪无效')
            memberships.append((tuple(value['scope']), (branches[branch], value['query']), stage.rank))
        if not memberships:
            memberships = [((), (0, 0), ordinal + 1)]
        owners = {}
        for scope, pool, rank in memberships:
            if scope not in owners or (pool, rank) < owners[scope]:
                owners[scope] = (pool, rank)
        for scope, (pool, rank) in owners.items():
            scopes.setdefault(scope, {}).setdefault(pool, []).append((rank, ordinal, hit))
    if len(scopes) > limit:
        raise ValueError('重排上限小于非空证据范围数，无法保留各范围取证机会')
    queues = [deque(deque(h for _, _, h in sorted(rows, key=lambda r: (r[0], r[1])))
        for _, rows in sorted(pools.items())) for _, pools in sorted(scopes.items())]
    selected, seen = [], set()
    while queues and len(selected) < limit:
        remaining = []
        for pools in queues:
            while pools:
                pool = pools.popleft()
                while pool and pool[0].identity in seen:
                    pool.popleft()
                if not pool:
                    continue
                hit = pool.popleft()
                selected.append(hit); seen.add(hit.identity)
                if pool:
                    pools.append(pool)
                break
            if pools:
                remaining.append(pools)
            if len(selected) == limit:
                break
        queues = remaining
    return selected
