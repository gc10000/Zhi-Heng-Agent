"""运行API只返回持久快照；执行与订阅不持有HTTP会话内存。"""
import time
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from app.api.errors import APIError
from app.identity.api import principal
from app.runs.models import RunInput, snapshot, TERMINAL
from app.runs.events import frame
from app.runs.commands import VersionInput, ConfirmInput

router = APIRouter(prefix='/api/v1', tags=['运行'])


@router.post('/conversations/{cid}/runs', status_code=202)
def create_run(cid: str, data: RunInput, request: Request, user=Depends(principal)):
    return request.app.state.resources['run_service'].create(user, cid, data)


@router.get('/runs/{rid}')
def get_run(rid: str, request: Request, user=Depends(principal)):
    return snapshot(request.app.state.resources['runs'].get(user, rid))


@router.get('/runs/{rid}/telemetry')
def run_telemetry(rid: str, request: Request, user=Depends(principal)):
    from .telemetry import run_telemetry as project
    return project(request.app.state.resources['runs'], user, rid)


@router.get('/run-telemetry')
def telemetry_page(kb_id: str, request: Request, cursor: str | None = Query(None, max_length=128),
                   limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    from app.identity.api import require_kb
    require_kb(user, kb_id)
    from .telemetry import page
    return page(request.app.state.resources['runs'], user, kb_id, cursor=cursor, limit=limit)


@router.post('/runs/{rid}/confirm-product')
def confirm(rid: str, data: ConfirmInput, request: Request, user=Depends(principal)):
    return request.app.state.resources['commands'].confirm(user, rid, data)


@router.post('/runs/{rid}/cancel')
def cancel(rid: str, data: VersionInput, request: Request, user=Depends(principal)):
    return request.app.state.resources['commands'].cancel(user, rid, data)


@router.get('/runs/{rid}/events')
def events(rid: str, request: Request, after_seq: int = Query(0, ge=0), user=Depends(principal)):
    last = request.headers.get('last-event-id')
    if last is not None:
        if not last.isascii() or not last.isdecimal():
            raise APIError(422, 'invalid_cursor', 'Last-Event-ID必须是非负整数。')
        after_seq = max(after_seq, int(last))
    resources = request.app.state.resources
    ledger, repo = resources['events'], resources['runs']
    first = ledger.read(user, rid, after_seq)
    def stream():
        cursor, batch, heartbeat = after_seq, first, time.monotonic()
        while True:
            # 订阅期间仍检查账号和范围，避免已撤权的长连接继续读取。
            current = resources['identity'].authenticate(request.cookies.get('support_session'))
            row = repo.get(current, rid)
            for event in batch:
                yield frame(event)
                cursor = event['seq']
            if row['state'] in TERMINAL and cursor >= row['seq']:
                return
            if time.monotonic() - heartbeat >= 15:
                yield ': 心跳\n\n'
                heartbeat = time.monotonic()
            time.sleep(.2)
            batch = ledger.read(current, rid, cursor)
    return StreamingResponse(stream(), media_type='text/event-stream',
        headers={'Cache-Control': 'no-cache, no-transform', 'X-Accel-Buffering': 'no'})
