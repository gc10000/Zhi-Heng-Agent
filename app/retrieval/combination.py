"""受信执行器显式授予的隔离组合；无环境开关、公开请求或隐式升级。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.api.errors import APIError
from app.knowledge.repository import fingerprint
from .prerequisites import SourcePrerequisiteScope, validate_scope
from .source_terms import collect_network_terms

def rows_digest(rows):
    """绑定正文、结构、出处与归属；不把向量序列化差异当正文变化。"""
    keys=('owner_id','kb_id','document_id','revision_id','chunk_uid','ordinal','text','metadata')
    return fingerprint(sorted(({k:r[k] for k in keys} for r in rows),
        key=lambda r:(r['document_id'],r['revision_id'],r['chunk_uid'])))


class ReviewedSource(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    document_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    chunk_uid: str = Field(min_length=1)
    row_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    proof_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')


class CombinationPolicy(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    enabled: bool = Field(default=False,strict=True)
    function_version: Literal['source_branch_compare_v1'] = 'source_branch_compare_v1'
    source_terms_version: Literal['source_network_terms_v1'] = 'source_network_terms_v1'
    fusion_version: Literal['branch_heads_v1'] = 'branch_heads_v1'
    context_version: Literal['compare_branch_context_v1'] = 'compare_branch_context_v1'
    scope: SourcePrerequisiteScope | None = None
    corpus_snapshot_sha256: str | None = Field(default=None,pattern=r'^[a-f0-9]{64}$')
    corpus_rows_sha256: str | None = Field(default=None,pattern=r'^[a-f0-9]{64}$')
    terms: list[dict] = Field(default_factory=list,max_length=4)
    reviewed_sources: list[ReviewedSource] = Field(default_factory=list,max_length=20)

    @model_validator(mode='after')
    def binding(self):
        if self.enabled and (self.scope is None or not self.corpus_snapshot_sha256 or
                not self.corpus_rows_sha256 or not self.terms or not self.reviewed_sources):
            raise ValueError('组合必须绑定完整隔离范围、语料快照、术语与已审出处证明')
        return self


def payload(value=None):
    return CombinationPolicy.model_validate({} if value is None else value).model_dump(mode='json')


def validate_run_combination(row,current):
    expected=payload(current);saved=payload(row.get('retrieval_combination'))
    if saved!=expected or (('retrieval_combination' in row or 'retrieval_combination_sha256' in row) and
            row.get('retrieval_combination_sha256')!=fingerprint(saved)):
        raise APIError(409,'execution_config_conflict','运行内部组合与冻结请求不一致。')
    return CombinationPolicy.model_validate(expected)


def validate_policies(combination,retrieval,source,expansion,enhancement):
    """只开放已审组合；不借此放宽其他策略或预算。"""
    if not combination.enabled:return
    from .search import RetrievalPolicy
    from .routing import EnhancementPolicy
    expected=RetrievalPolicy(exclude_image_descriptions=True,query_projection='scoped_subject_v1',
                             comparison_context='scope_first_v1')
    if (retrieval!=expected or not source.enabled or source.scope!=combination.scope or
            expansion.enabled or enhancement!=EnhancementPolicy()):
        raise ValueError('内部组合只允许已审weighted固定预算、来源前提及关闭增强')


def authorize_combination(value,*,loader,owner_id,kb_id,database,collection,revisions,product_ids):
    policy=CombinationPolicy.model_validate(value)
    if not policy.enabled:raise ValueError('关闭组合不能读取语料')
    validate_scope(policy,owner_id=owner_id,kb_id=kb_id,revisions=revisions,product_ids=product_ids)
    if (database,collection)!=(policy.scope.database,policy.scope.collection):
        raise ValueError('内部组合目标数据库/集合与冻结范围不同')
    rows=loader()
    if not rows or len(rows)>1000 or len({r['chunk_uid'] for r in rows})!=len(rows):
        raise ValueError('组合语料缺失、重复或超过读取预算')
    allowed=set(policy.scope.revisions.items());products=set(policy.scope.product_ids)
    for row in rows:
        meta=row['metadata'];owners=meta.get('product_ids',[])
        if ((row.get('owner_id'),row.get('kb_id'))!=(owner_id,kb_id) or
                (row['document_id'],row['revision_id']) not in allowed or not owners or not set(owners)<=products or
                any((r.get('document_id'),r.get('revision_id'))!=(row['document_id'],row['revision_id'])
                    for r in meta.get('source_refs',[]))):
            raise ValueError('组合语料归属/修订/产品/出处越界')
    if rows_digest(rows)!=policy.corpus_rows_sha256:raise ValueError('组合语料载荷变化')
    terms=collect_network_terms(rows,revision_ids=list(policy.scope.revisions.values()),product_ids=list(products))
    if terms!=policy.terms:raise ValueError('组合术语与授权原文不一致')
    for proof in policy.reviewed_sources:
        matching=[r for r in rows if (r['document_id'],r['revision_id'],r['chunk_uid'])==
                  (proof.document_id,proof.revision_id,proof.chunk_uid)]
        if len(matching)!=1 or rows_digest(matching)!=proof.row_sha256 or any(
                r.get('page') is None for r in matching[0]['metadata'].get('source_refs',[])) or not matching[0]['metadata'].get('source_refs'):
            raise ValueError('组合已审出处的目标载荷/页码变化')
    return policy
