"""受控原件/图片读取；先授权和校验hash，再返回PDF单段Range。"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from app.api.errors import APIError
from app.identity.api import principal
from app.knowledge.api import gateway
from app.knowledge.models import content_hash, stable_id

router = APIRouter(prefix='/api/v1', tags=['受控资源'])


def original_asset(g, revision, *, media_type, name):
    aid = stable_id('original-asset', revision['revision_id'], [])
    row = {'asset_id': aid, 'document_id': revision['document_id'], 'revision_id': revision['revision_id'],
           'object_key': revision['object_key'], 'sha256': revision['original_sha256'], 'media_type': media_type,
           'kind': 'original', 'name': name}
    g.db.knowledge_original_assets.update_one({'asset_id': aid}, {'$setOnInsert': row}, upsert=True)
    return aid


def asset_record(g, user, aid):
    row = (g.db.knowledge_original_assets.find_one({'asset_id': aid}) or
           g.db.knowledge_assets.find_one({'asset_id': aid}) or g.db.knowledge_legacy_assets.find_one({'asset_id': aid}))
    if row is None:
        raise APIError(404, 'not_found', '资产不存在或不在授权范围。')
    revision = g.revision(user, row['document_id'], row['revision_id'])
    return row, revision


def read_asset(g, row, revision):
    if row.get('kind') == 'original':
        data = g.originals.read(revision)
    else:
        response = g.originals.client.get_object(row.get('bucket', g.originals.bucket), row['object_key'])
        try:
            data = response.read()
        finally:
            response.close()
            response.release_conn()
    if content_hash(data) != row['sha256']:
        raise APIError(502, 'asset_integrity_error', '资产内容校验失败，请联系维护者。')
    return data


def byte_range(header, size):
    if not header.startswith('bytes=') or ',' in header:
        raise ValueError('仅支持单段字节范围')
    value = header[6:]
    if value.count('-') != 1:
        raise ValueError('无效范围')
    start, end = value.split('-')
    if any(v and (not v.isascii() or not v.isdecimal()) for v in (start, end)):
        raise ValueError('无效范围')
    if not start:
        suffix = int(end) if end else 0
        if suffix < 1 or size == 0:
            raise ValueError('无效范围')
        return max(0, size - suffix), size - 1
    first, last = int(start), int(end) if end else size - 1
    if first >= size or last < first:
        raise ValueError('无效范围')
    return first, min(last, size - 1)


@router.get('/assets/{aid}')
def asset(aid: str, request: Request, user=Depends(principal)):
    g = gateway(request)
    row, revision = asset_record(g, user, aid)
    data = read_asset(g, row, revision)
    media = row['media_type']
    headers = {'ETag': '"' + row['sha256'] + '"', 'Cache-Control': 'private, no-store',
               'Content-Disposition': 'inline' if media == 'application/pdf' or media.startswith('image/') else 'attachment'}
    if media == 'application/pdf':
        headers['Accept-Ranges'] = 'bytes'
        if request.headers.get('range'):
            try:
                first, last = byte_range(request.headers['range'], len(data))
            except ValueError:
                return Response(status_code=416, headers=headers | {'Content-Range': f'bytes */{len(data)}'})
            return Response(data[first:last+1], status_code=206, media_type=media,
                            headers=headers | {'Content-Range': f'bytes {first}-{last}/{len(data)}'})
    return Response(data, media_type=media, headers=headers)
