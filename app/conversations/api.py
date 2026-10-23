"""会话端点从服务端身份设置owner，不信任客户端归属字段。"""
from fastapi import APIRouter, Depends, Query, Request
from app.conversations.models import ConversationInput, ConversationPatch
from app.identity.api import principal

router = APIRouter(prefix='/api/v1/conversations', tags=['会话'])


def repository(request):
    return request.app.state.resources['conversations']


@router.get('')
def conversations(request: Request, cursor: str | None = None, limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    return repository(request).list(user, cursor=cursor, limit=limit)


@router.post('', status_code=201)
def create(data: ConversationInput, request: Request, user=Depends(principal)):
    return repository(request).create(user, data)


@router.patch('/{cid}')
def patch(cid: str, data: ConversationPatch, request: Request, user=Depends(principal)):
    return repository(request).patch(user, cid, data)


@router.get('/{cid}/messages')
def messages(cid: str, request: Request, cursor: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    return repository(request).history(user, cid, after=cursor, limit=limit)
