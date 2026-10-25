"""支持流程命令复用登录、同源防伪、owner及知识范围授权。"""
from fastapi import APIRouter, Depends, Request
from app.identity.api import principal
from .models import SupportInput
from .repository import SupportRepository

router = APIRouter(prefix='/api/v1', tags=['支持流程'])


def support(request):
    resources = request.app.state.resources
    return SupportRepository(resources['conversations'], resources['runs'])


@router.get('/conversations/{cid}/support')
def get_support(cid: str, request: Request, user=Depends(principal)):
    return support(request).get(user, cid)


@router.post('/conversations/{cid}/support')
def update_support(cid: str, data: SupportInput, request: Request, user=Depends(principal)):
    return support(request).update(user, cid, data)

