"""固定检索策略；各数量独立且有界，默认保持已接受的加权路径。"""
import copy
import json
import os
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from .adapters import score_record


class RetrievalPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True, allow_inf_nan=False)
    dense_limit: int = Field(default=20, ge=1, le=1000, strict=True)
    sparse_limit: int = Field(default=20, ge=1, le=1000, strict=True)
    fusion_limit: int = Field(default=20, ge=1, le=1000, strict=True)
    rerank_limit: int = Field(default=20, ge=1, le=1000, strict=True)
    context_limit: int = Field(default=10, ge=1, le=1000, strict=True)
    fusion: Literal['weighted', 'rrf', 'dense', 'learned_sparse'] = 'weighted'
    dense_weight: float = Field(default=.5, ge=0, le=1)
    sparse_weight: float = Field(default=.5, ge=0, le=1)
    rrf_k: int = Field(default=60, ge=1, le=16384, strict=True)
    # 隔离不可信派生图摘要；原PDF正文、正文引用的图片与资产授权不受此开关替代。
    exclude_image_descriptions: bool = Field(default=False, strict=True)
    # 仅显式配置启用，不增加查询、候选数量或改变融合。
    query_projection: Literal['original', 'scoped_subject_v1'] = 'original'
    # 默认保持全局排序；隔离对照可显式为比较双方各保留一个已重排证据。
    comparison_context: Literal['global', 'scope_first_v1'] = 'global'

    @model_validator(mode='after')
    def limits(self):
        if not self.context_limit <= self.rerank_limit <= self.fusion_limit:
            raise ValueError('上下文数量≤重排输入数量≤融合池数量')
        available = {'dense': self.dense_limit, 'learned_sparse': self.sparse_limit}.get(
            self.fusion, self.dense_limit + self.sparse_limit)
        if self.fusion_limit > available:
            raise ValueError('融合池不能超过初召回上限')
        if self.fusion == 'weighted' and self.dense_weight + self.sparse_weight <= 0:
            raise ValueError('加权融合至少有一路正权重')
        return self

    @classmethod
    def load(cls):
        raw = os.getenv('RETRIEVAL_POLICY_JSON', '').strip()
        if not raw:
            return cls()
        try:
            return cls.model_validate_json(raw)
        except ValueError:
            raise ValueError('RETRIEVAL_POLICY_JSON必须为有效且有界的检索策略JSON，详见配置文档') from None


def retrieve(index, repo, plan, *, embedder, revision_snapshot, policy):
    policy = RetrievalPolicy.model_validate(policy)
    hits = []
    for scope in plan.scope_groups:
        for query_number, query in enumerate(plan.search_queries):
            args = dict(embedder=embedder, revision_snapshot=revision_snapshot,
                product_ids=list(scope), limit=policy.fusion_limit)
            # 默认调用保持旧索引端口，便于回切与兼容接入。
            if policy != RetrievalPolicy():
                args['policy'] = policy.model_dump()
            found = index.search(repo, query, **args)
            for rank, raw in enumerate(found, 1):
                hit = copy.deepcopy(raw)
                trace = hit.get('retrieval_trace') or hit.get('entity', hit).get('retrieval_trace') or [
                    score_record('retrieval', rank, hit.get('distance'), 'backend_unspecified')]
                if plan.route == 'compare' or query_number:
                    prefix = f'product:{scope[0]}/' if plan.route == 'compare' else ''
                    trace = [t | {'query_id': f'{prefix}query:{query_number}/{t["query_id"]}'} for t in trace]
                # 独立记录池内名次与真实范围；不改写后端各阶段的分数含义。
                hit['retrieval_trace'] = trace + [score_record('candidate_pool', rank, None,
                    'rank_only', json.dumps(dict(scope=sorted(scope), query=query_number),
                        ensure_ascii=False, sort_keys=True))]
                hits.append(hit)
    return hits
