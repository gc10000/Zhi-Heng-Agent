"""重排输入与上下文上限分离；输出必须来自本次实际重排输入。"""
from .adapters import after_rerank
from .search import RetrievalPolicy
from .selection import select_candidates


def rank_hits(question, candidates, *, ranker, policy):
    policy = RetrievalPolicy.model_validate(policy)
    inputs = select_candidates(candidates, policy.rerank_limit)
    documents = ranker(question, [h.document() for h in inputs]) if inputs else []
    return after_rerank(inputs, documents)
