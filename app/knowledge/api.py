"""资料管理端点复用M1领域仓储、验证和发布，不绕过维护权限。"""
import asyncio
import re
from fastapi import APIRouter, Depends, Query, Request
from starlette.datastructures import UploadFile
from starlette.requests import Request as FormRequest
from pydantic import BaseModel, ConfigDict, Field
from app.api.errors import APIError
from app.identity.api import principal, require_kb, require_writer
from app.knowledge.gateway import page, DOCUMENT_FIELDS, REVISION_FIELDS
from app.knowledge.upload import UploadService, product_list
from app.runs.commands import VersionInput
from app.ingestion.jobs import job_view

router = APIRouter(prefix='/api/v1', tags=['知识资料'])


def gateway(request):
    return request.app.state.resources['knowledge']()


class ProductInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kb_id: str = Field(min_length=1, max_length=128)
    model: str = Field(min_length=1, max_length=200)
    brand: str | None = Field(default=None, max_length=100)
    series: str | None = Field(default=None, max_length=100)
    aliases: list[str] = Field(default_factory=list, max_length=50)


class PublishInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_active_revision_id: str | None


class RollbackInput(PublishInput):
    target_revision_id: str = Field(min_length=1)


@router.get('/products')
def products(request: Request, kb_id: str, search: str = Query('', max_length=200), cursor: str | None = None,
             limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    require_kb(user, kb_id)
    g = gateway(request)
    ids = g.product_kbs.distinct('product_id', {'owner_id': g.owner_id, 'kb_id': kb_id})
    query = {'owner_id': g.owner_id, 'product_id': {'$in': ids}}
    if search:
        query['model'] = {'$regex': re.escape(search), '$options': 'i'}
    # 分页范围与游标同时限制，不能用游标覆盖授权ID过滤条件。
    if cursor:
        query['product_id']['$gt'] = cursor
    return page(g.products.collection, query, 'product_id', limit=limit,
                fields=('product_id', 'model', 'brand', 'series', 'aliases'))


@router.post('/products', status_code=201)
def create_product(data: ProductInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return gateway(request).add_product(user, data.kb_id, data)


@router.get('/products/{pid}/documents')
def product_documents(pid: str, request: Request, kb_id: str, cursor: str | None = None,
                      limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    g = gateway(request)
    g.product(user, pid, kb_id)
    return page(g.repo(kb_id).documents, {'owner_id': g.owner_id, 'kb_id': kb_id, 'product_ids': pid},
                'document_id', cursor=cursor, limit=limit, fields=DOCUMENT_FIELDS)


@router.get('/documents')
def documents(request: Request, kb_id: str, cursor: str | None = None,
              limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    require_kb(user, kb_id)
    g = gateway(request)
    return page(g.repo(kb_id).documents, {'owner_id': g.owner_id, 'kb_id': kb_id},
                'document_id', cursor=cursor, limit=limit, fields=DOCUMENT_FIELDS)


@router.post('/documents', status_code=202)
async def upload(request: Request, user=Depends(principal)):
    require_writer(user)
    g = gateway(request)
    # 在multipart解析前限制整条请求，避免只检查已读完的文件大小。
    cap, body = g.max_upload_bytes + 65536, bytearray()
    if not request.headers.get('content-type', '').startswith('multipart/form-data;'):
        raise APIError(415, 'unsupported_media', '上传须使用multipart/form-data。')
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > cap:
            raise APIError(413, 'upload_too_large', '上传请求超过大小限制。')
    async def receive():
        return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
    parsed = FormRequest(request.scope, receive=receive)
    async with parsed.form(max_files=1, max_fields=8, max_part_size=65536) as form:
        allowed = {'file', 'kb_id', 'product_ids', 'client_request_id', 'document_id', 'purpose'}
        if any(key not in allowed or len(form.getlist(key)) != 1 for key in form):
            raise APIError(422, 'invalid_upload', '上传字段重复或不受支持。')
        file = form.get('file')
        if not isinstance(file, UploadFile) or not isinstance(form.get('kb_id'), str) or not isinstance(form.get('client_request_id'), str):
            raise APIError(422, 'invalid_upload', '请提供原件、kb_id及client_request_id。')
        data = await file.read(g.max_upload_bytes + 1)
        return await asyncio.to_thread(UploadService(g).upload, user,
            kb_id=form['kb_id'], client_request_id=form['client_request_id'], name=file.filename,
            media_type=file.content_type or '', data=data, product_ids=product_list(form.get('product_ids', '[]')),
            document_id=form.get('document_id'), purpose=form.get('purpose', 'unknown'))


@router.get('/documents/{did}/revisions')
def revisions(did: str, request: Request, cursor: str | None = None,
              limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    g = gateway(request)
    document = g.document(user, did)
    return page(g.repo(document['kb_id']).revisions,
                {'owner_id': g.owner_id, 'kb_id': document['kb_id'], 'document_id': did},
                'revision_id', cursor=cursor, limit=limit, fields=REVISION_FIELDS)


@router.get('/documents/{did}/revisions/{rid}/chunks')
def chunks(did: str, rid: str, request: Request, cursor: int = Query(0, ge=0),
           limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    require_writer(user)
    g = gateway(request)
    revision = g.revision(user, did, rid)
    rows = [r for r in g.index().revision_rows(g.repo(revision['kb_id']), rid) if r['ordinal'] >= cursor]
    return {'items': rows[:limit], 'next_cursor': str(rows[limit-1]['ordinal'] + 1) if len(rows) > limit else None}


@router.post('/documents/{did}/revisions/{rid}/publish')
def publish(did: str, rid: str, data: PublishInput, request: Request, user=Depends(principal)):
    require_writer(user)
    g = gateway(request)
    revision = g.revision(user, did, rid)
    try:
        result = g.publisher(revision['kb_id']).publish(rid, expected_active=data.expected_active_revision_id)
    except ValueError:
        raise APIError(409, 'revision_invalid', '修订验证未通过，请检查原件、来源和索引产物。') from None
    return {'document_id': did, 'active_revision_id': rid, 'transition_id': result['id']}


@router.post('/documents/{did}/rollback')
def rollback(did: str, data: RollbackInput, request: Request, user=Depends(principal)):
    return publish(did, data.target_revision_id, data, request, user)


@router.post('/documents/{did}/withdraw')
def withdraw(did: str, data: PublishInput, request: Request, user=Depends(principal)):
    require_writer(user)
    g = gateway(request)
    doc = g.document(user, did)
    result = g.repo(doc['kb_id']).documents.update_one({'document_id': did, 'owner_id': g.owner_id,
        'kb_id': doc['kb_id'], 'active_revision_id': data.expected_active_revision_id},
        {'$set': {'active_revision_id': None}, '$inc': {'active_generation': 1}, '$unset': {'publish_outbox': ''}})
    if not result.matched_count:
        raise APIError(409, 'version_conflict', '活动修订已改变，请刷新。')
    return {'document_id': did, 'active_revision_id': None}


@router.get('/import-jobs/{jid}')
def job(jid: str, request: Request, user=Depends(principal)):
    return job_view(gateway(request).jobs.get(user, jid))


@router.post('/import-jobs/{jid}/retry')
def retry(jid: str, data: VersionInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return gateway(request).jobs.retry(user, jid, data.expected_version)
