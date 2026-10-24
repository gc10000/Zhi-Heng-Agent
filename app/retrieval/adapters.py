"""Milvus与旧节点的无损适配；未知分数保留未知，不能补造分路排名。"""
import copy
from .models import RetrievalHit, StageScore


def stable_key(entity):
    uid = entity.get('chunk_uid', entity.get('chunk_id', entity.get('id')))
    if uid is None or str(uid) == '':
        raise ValueError('检索证据缺少稳定身份')
    return str(entity.get('document_id') or ''), str(entity.get('revision_id') or ''), str(uid)


def score_record(stage, rank, score, score_kind, query_id='original'):
    return StageScore(stage=stage, rank=rank, score=score, score_kind=score_kind, query_id=query_id).model_dump()


def traced_hybrid(hits, dense, sparse, *, fusion='weighted'):
    branches = []
    for channel, rows in [('dense', dense), ('learned_sparse', sparse)]:
        ranks = {}
        for rank, raw in enumerate(rows, 1):
            ranks.setdefault(stable_key(raw.get('entity', raw)), score_record(channel, rank,
                raw.get('distance', raw.get('score')), 'inner_product'))
        branches.append(ranks)
    result = []
    for rank, raw in enumerate(hits, 1):
        item = copy.deepcopy(raw); key = stable_key(item.get('entity', item))
        item['retrieval_trace'] = [r[key] for r in branches if key in r] + [
            score_record('rrf' if fusion == 'rrf' else 'weighted_fusion', rank,
                raw.get('distance', raw.get('score')), 'reciprocal_rank' if fusion == 'rrf' else 'milvus_weighted_ip')]
        result.append(item)
    return result


def from_index_hits(hits):
    merged = {}
    for rank, raw in enumerate(hits, 1):
        entity = copy.deepcopy(raw.get('entity', raw))
        trace = raw.get('retrieval_trace', entity.get('retrieval_trace'))
        if trace is None:
            trace = [score_record('retrieval', rank, raw.get('distance'), 'backend_unspecified')]
        hit = RetrievalHit(**{k: entity[k] for k in ('chunk_uid', 'document_id', 'revision_id', 'text')},
            ordinal=entity.get('ordinal'), metadata=entity.get('metadata', {}), stages=trace)
        if hit.identity in merged:
            prior = merged[hit.identity]
            if (prior.text, prior.metadata, prior.ordinal) != (hit.text, hit.metadata, hit.ordinal):
                raise ValueError('同证据身份对应不同正文或来源')
            stage_keys = {(s.stage, s.query_id) for s in prior.stages}
            prior.stages.extend(s for s in hit.stages if (s.stage, s.query_id) not in stage_keys)
        else:
            merged[hit.identity] = hit
    return list(merged.values())


def after_rerank(candidates, documents):
    originals = {h.identity: h for h in candidates}
    result, seen = [], set()
    for rank, doc in enumerate(documents, 1):
        key = stable_key(doc)
        if key not in originals or key in seen:
            raise ValueError('重排插入未知或重复证据')
        prior = originals[key]
        if doc['text'] != prior.text or doc.get('metadata', prior.metadata) != prior.metadata:
            raise ValueError('重排不能修改证据原文或来源')
        score = doc.get('rerank_score', doc.get('score'))
        stages = copy.deepcopy(prior.stages) + [StageScore(stage='rerank', rank=rank, score=score,
            score_kind='model_relevance' if score is not None else 'rank_only')]
        result.append(prior.model_copy(deep=True, update={'stages': stages})); seen.add(key)
    return result
