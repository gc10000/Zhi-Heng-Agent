"""受信内部的版本化证据归属；默认关闭，不推断对象或页码。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.api.errors import APIError
from app.knowledge.repository import fingerprint
from app.retrieval.prerequisites import SourcePrerequisiteScope, validate_scope


class AttributionDocument(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    document_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    original_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')


class EvidenceAttributionPolicy(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    enabled: bool = Field(default=False,strict=True)
    function_version: Literal['attributed_assertions_v1'] = 'attributed_assertions_v1'
    scope: SourcePrerequisiteScope | None = None
    corpus_snapshot_sha256: str | None = Field(default=None,pattern=r'^[0-9a-f]{64}$')
    documents: list[AttributionDocument] = Field(default_factory=list,max_length=20)
    products: dict[str,str] = Field(default_factory=dict,max_length=50)

    @model_validator(mode='after')
    def complete(self):
        if self.enabled and (not self.scope or not self.corpus_snapshot_sha256 or
                len({d.document_id for d in self.documents})!=len(self.documents) or
                {d.document_id:d.revision_id for d in self.documents}!=self.scope.revisions or
                set(self.products)!=set(self.scope.product_ids) or any(not v.strip() for v in self.products.values())):
            raise ValueError('证据归属须绑定完整冻结范围、修订及真实产品快照')
        return self


def payload(value=None):
    return EvidenceAttributionPolicy.model_validate({} if value is None else value).model_dump(mode='json')


def validate_run_attribution(row,current):
    expected=payload(current);saved=payload(row.get('evidence_attribution'))
    if saved!=expected or (('evidence_attribution' in row or 'evidence_attribution_sha256' in row) and
            row.get('evidence_attribution_sha256')!=fingerprint(saved)):
        raise APIError(409,'execution_config_conflict','运行证据归属策略与冻结请求不一致。')
    return EvidenceAttributionPolicy.model_validate(expected)


def validate_config(config,policy):
    """不信任手填名称；与正式冻结语料投影全等，先于Run持久写入。"""
    if not policy.enabled:return
    corpus=config.get('corpus',{});snapshot=corpus.get('snapshot',{});target=config['target']
    docs=[{k:d[k] for k in ('document_id','revision_id','original_sha256')} for d in snapshot.get('documents',[])]
    if (any(target.get(k)!=getattr(policy.scope,k) for k in ('owner_id','kb_id','database','collection')) or
            fingerprint(snapshot)!=policy.corpus_snapshot_sha256 or
            sorted(docs,key=lambda d:d['document_id'])!=sorted([d.model_dump() for d in policy.documents],key=lambda d:d['document_id']) or
            policy.products!={p['product_id']:p['model'] for p in snapshot.get('products',[])} or
            any(p.get('owner_id')!=target['owner_id'] for p in snapshot.get('products',[])) or
            {d['document_id']:d['revision_id'] for d in corpus.get('documents',[])}!=policy.scope.revisions):
        raise ValueError('证据归属与目标/冻结语料快照不一致')


def authorize(policy,*,repo,products,revisions,product_ids,database,collection):
    if not policy.enabled:return
    validate_scope(policy,owner_id=repo.owner_id,kb_id=repo.kb_id,revisions=revisions,product_ids=product_ids)
    if (database,collection)!=(policy.scope.database,policy.scope.collection):
        raise ValueError('证据归属目标命名空间不一致')
    current={p['product_id']:p['model'] for p in products if p['product_id'] in policy.scope.product_ids}
    if current!=policy.products:raise ValueError('证据归属产品快照变化')
    for source in policy.documents:
        revision=repo.get_revision(source.revision_id)
        if (revision['document_id']!=source.document_id or revision['original_sha256']!=source.original_sha256):
            raise ValueError('证据归属原件/修订变化')


def evidence_labels(docs,value):
    policy=EvidenceAttributionPolicy.model_validate(value)
    if not policy.enabled:return None
    sources={d.document_id:d for d in policy.documents}
    result=[]
    for doc in docs:
        source=sources.get(doc.get('document_id'))
        if not source or source.revision_id!=doc.get('revision_id'):
            raise ValueError('证据归属文档/修订越界')
        meta=doc.get('metadata') or {};ids=meta.get('product_ids') or []
        if not isinstance(ids,list) or any(p not in policy.products for p in ids):
            raise ValueError('证据归属产品越界')
        refs=doc.get('source_refs',meta.get('source_refs',[])) or []
        if any((r.get('document_id'),r.get('revision_id'))!=(source.document_id,source.revision_id) for r in refs):
            raise ValueError('证据引用映射跨文档/修订')
        pages=sorted({r['page'] for r in refs if r.get('kind')=='pdf' and type(r.get('page')) is int and r['page']>0})
        exact=bool(refs) and all(r.get('kind')=='pdf' and type(r.get('page')) is int and r['page']>0 for r in refs)
        result.append(dict(document_id=source.document_id,revision_id=source.revision_id,original_sha256=source.original_sha256,
            chunk_uid=doc.get('chunk_uid',doc.get('chunk_id')),products=[policy.products[p] for p in ids],
            product_status='snapshot' if ids else 'unknown',physical_pages=pages,page_status='exact' if exact else 'unknown'))
    return result
