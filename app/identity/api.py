"""同源Cookie登录，不接受URL中的长期令牌。"""
import hmac
from fastapi import APIRouter, Depends, Request, Response
from app.api.errors import APIError
from app.identity.models import LoginInput

router = APIRouter(prefix='/api/v1', tags=['身份'])
COOKIE = 'support_session'


def identity(request):
    return request.app.state.resources['identity']


def check_origin(request: Request):
    if request.headers.get('origin', '') not in request.app.state.settings.origins:
        raise APIError(403, 'origin_rejected', '请求来源不被允许。')


def principal(request: Request):
    user = identity(request).authenticate(request.cookies.get(COOKIE))
    if request.method not in {'GET', 'HEAD', 'OPTIONS'}:
        check_origin(request)
        expected = identity(request).csrf(request.cookies.get(COOKIE, ''))
        if not hmac.compare_digest(request.headers.get('x-csrf-token', ''), expected):
            raise APIError(403, 'csrf_rejected', '请求防伪令牌无效，请刷新后重试。')
    return user


def require_writer(user):
    if user.role not in {'maintainer', 'admin'}:
        raise APIError(403, 'permission_denied', '当前角色不能执行维护操作。')


def require_kb(user, kb_id):
    if kb_id not in user.kb_ids:
        raise APIError(404, 'not_found', '资源不存在或不在授权范围。')


@router.post('/auth/login', dependencies=[Depends(check_origin)])
def login(data: LoginInput, request: Request, response: Response):
    service = identity(request)
    token, user = service.login(data.username, data.password, request.client.host if request.client else 'unknown')
    settings = request.app.state.settings
    response.set_cookie(COOKIE, token, httponly=True, secure=settings.cookie_secure, samesite='strict',
                        max_age=settings.session_seconds, path='/api/v1')
    response.headers['Cache-Control'] = 'no-store'
    return {'user': user.model_dump(mode='json'), 'csrf_token': service.csrf(token)}


@router.get('/me')
def me(request: Request, user=Depends(principal)):
    return {'user': user.model_dump(mode='json'), 'csrf_token': identity(request).csrf(request.cookies[COOKIE])}


@router.post('/auth/logout')
def logout(request: Request, response: Response, user=Depends(principal)):
    identity(request).logout(request.cookies[COOKIE])
    response.delete_cookie(COOKIE, path='/api/v1')
    return {'logged_out': True}
