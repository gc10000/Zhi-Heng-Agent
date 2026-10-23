"""运行API只返回持久快照；执行与订阅不持有HTTP会话内存。"""
from fastapi import APIRouter, Depends, Request
from app.identity.api import principal
from app.runs.models import RunInput, snapshot

router = APIRouter(prefix='/api/v1', tags=['运行'])


@router.post('/conversations/{cid}/runs', status_code=202)
def create_run(cid: str, data: RunInput, request: Request, user=Depends(principal)):
    return request.app.state.resources['run_service'].create(user, cid, data)


@router.get('/runs/{rid}')
def get_run(rid: str, request: Request, user=Depends(principal)):
    return snapshot(request.app.state.resources['runs'].get(user, rid))
