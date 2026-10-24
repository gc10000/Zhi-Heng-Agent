"""检索阶段分数与证据身份分开保存，不能把融合分当模型重排分。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StageScore(BaseModel):
    model_config = ConfigDict(extra='forbid', allow_inf_nan=False)
    stage: str = Field(min_length=1)
    rank: int | None = Field(default=None, ge=1)
    score: float | None = None
    score_kind: str = Field(min_length=1)
    query_id: str = 'original'


class QueryPlan(BaseModel):
    model_config = ConfigDict(extra='forbid')
    original_query: str
    search_queries: tuple[str, ...] = ()
    product_ids: tuple[str, ...] = ()
    revision_ids: tuple[str, ...] = ()
    route: Literal['answer', 'clarify', 'compare', 'insufficient'] = 'answer'
    slots: dict[str, str] = Field(default_factory=dict)


class RetrievalHit(BaseModel):
    model_config = ConfigDict(extra='forbid')
    chunk_uid: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    text: str
    ordinal: int | None = None
    metadata: dict = Field(default_factory=dict)
    stages: list[StageScore] = Field(default_factory=list)

    @property
    def identity(self):
        return self.document_id, self.revision_id, self.chunk_uid

    def document(self):
        value = self.model_dump(exclude={'stages'})
        if self.stages and self.stages[-1].stage == 'rerank' and self.stages[-1].score is not None:
            value['score'] = self.stages[-1].score
        return value | {'chunk_id': self.chunk_uid, 'source': 'local',
            'title': '/'.join(self.metadata.get('heading_path', [])),
            'asset_ids': list(self.metadata.get('asset_ids', [])),
            'source_refs': list(self.metadata.get('source_refs', [])),
            'retrieval_trace': [s.model_dump() for s in self.stages]}


class EvidencePack(BaseModel):
    model_config = ConfigDict(extra='forbid')
    plan: QueryPlan
    candidates: list[RetrievalHit] = Field(default_factory=list)
    reranked: list[RetrievalHit] = Field(default_factory=list)
    selected: list[RetrievalHit] = Field(default_factory=list)
    strategy: str = 'm3-baseline'
    degraded: list[str] = Field(default_factory=list)

    @model_validator(mode='after')
    def selected_must_be_candidates(self):
        candidates = {h.identity: h for h in self.candidates}
        if len(candidates) != len(self.candidates):
            raise ValueError('候选身份重复，须先稳定去重')
        ranked = {h.identity: h for h in self.reranked}
        if len(ranked) != len(self.reranked) or not ranked.keys() <= candidates.keys():
            raise ValueError('重排结果包含重复或未知证据')
        if len({h.identity for h in self.selected}) != len(self.selected):
            raise ValueError('上下文证据身份重复')
        for hit in self.selected:
            if hit.identity not in ranked:
                raise ValueError('上下文证据不在实际重排结果中')
        for hit in self.reranked + self.selected:
            original = candidates[hit.identity]
            if hit.text != original.text or hit.metadata != original.metadata:
                raise ValueError('后续阶段不能改写原证据正文或来源')
        return self

    def trace(self):
        ranked = {h.identity: h for h in self.reranked}
        chosen = {h.identity for h in self.selected}
        return [{'chunk_uid': h.chunk_uid, 'document_id': h.document_id, 'revision_id': h.revision_id,
                 'stages': [s.model_dump() for s in ranked.get(h.identity, h).stages],
                 'selected': h.identity in chosen} for h in self.candidates]
