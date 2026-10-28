"""内部显式配置及授权装载；不从环境或公开请求启用来源前提。"""
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.api.errors import APIError
from app.knowledge.repository import fingerprint
from .models import RetrievalHit
from .expansion import retain_source_prerequisites


class SourcePrerequisiteScope(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    owner_id: str = Field(min_length=1)
    kb_id: str = Field(min_length=1)
    database: str = Field(pattern=r'^m1_test_[A-Za-z0-9_]+$')
    collection: str = Field(pattern=r'^m1_test_[A-Za-z0-9_]+$')
    revisions: dict[str, str] = Field(min_length=1, max_length=20)
    product_ids: tuple[str, ...] = Field(min_length=1, max_length=50)

    @model_validator(mode='after')
    def valid_ids(self):
        if (any(not d or not r for d,r in self.revisions.items()) or
                any(not p for p in self.product_ids) or len(set(self.product_ids))!=len(self.product_ids) or
                len(set(self.revisions.values()))!=len(self.revisions)):
            raise ValueError('来源前提范围必须具有唯一非空身份')
        return self


class SourcePrerequisitePolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    enabled: bool = Field(default=False, strict=True)
    function_version: Literal['1'] = '1'
    max_added: int = Field(default=4, ge=0, le=4, strict=True)
    max_chars: int = Field(default=6000, ge=0, le=6000, strict=True)
    max_rows: int = Field(default=1000, ge=1, le=1000, strict=True)
    scope: SourcePrerequisiteScope | None = None

    @model_validator(mode='after')
    def explicit_scope(self):
        if self.enabled and self.scope is None:
            raise ValueError('启用来源前提须显式冻结授权范围')
        return self


def policy_payload(value=None):
    return SourcePrerequisitePolicy.model_validate({} if value is None else value).model_dump(mode='json')


def validate_run_policy(row, current):
    """旧缺省Run仅兼容缺省关闭；不得给旧Run事后启用或换预算。"""
    expected=policy_payload(current)
    saved=policy_payload(row.get('source_prerequisites'))
    if saved!=expected or ('source_prerequisites_sha256' in row and row['source_prerequisites_sha256']!=fingerprint(saved)):
        raise APIError(409,'execution_config_conflict','运行来源前提配置与冻结请求不一致。')
    return SourcePrerequisitePolicy.model_validate(expected)


def validate_scope(policy, *, owner_id, kb_id, revisions, product_ids):
    scope=policy.scope
    if (scope is None or (scope.owner_id,scope.kb_id)!=(owner_id,kb_id) or
            set(scope.revisions.items())!={(r['document_id'],r['active_revision_id']) for r in revisions} or
            not product_ids or not set(product_ids)<=set(scope.product_ids)):
        raise ValueError('来源前提超出冻结归属/知识库/修订/产品范围')


def authorized_source_selection(seeds, *, loader, policy, owner_id, kb_id, revisions, product_ids):
    policy=SourcePrerequisitePolicy.model_validate(policy)
    if not policy.enabled:
        raise ValueError('关闭路径不能装载来源前提')
    validate_scope(policy,owner_id=owner_id,kb_id=kb_id,revisions=revisions,product_ids=product_ids)
    allowed=set(policy.scope.revisions.items())
    def valid_hit(hit):
        products=hit.metadata.get('product_ids',[])
        return (hit.document_id,hit.revision_id) in allowed and bool(products) and set(products)<=set(product_ids)
    if len(seeds)>20 or any(not valid_hit(h) for h in seeds):
        raise ValueError('来源前提种子超出冻结范围')
    # 读取端须实施limit；再防御被替换或返回越界数据的端口。
    rows=loader(seeds=seeds,revision_snapshot=revisions,product_ids=product_ids,max_rows=policy.max_rows) if seeds else []
    if len(rows)>policy.max_rows:
        raise ValueError('来源前提装载超过行上限')
    hits=[]
    for row in rows:
        if (row.get('owner_id'),row.get('kb_id'))!=(owner_id,kb_id):
            raise ValueError('来源前提装载归属/知识库越界')
        hit=RetrievalHit(**{k:row[k] for k in ('document_id','revision_id','chunk_uid','text')},ordinal=row.get('ordinal'),metadata=row.get('metadata',{}))
        if not valid_hit(hit):raise ValueError('来源前提装载修订/产品越界')
        hits.append(hit)
    return retain_source_prerequisites(seeds,hits,max_added=policy.max_added,max_chars=policy.max_chars)
