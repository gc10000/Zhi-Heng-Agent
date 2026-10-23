"""公开错误信封，不回显异常正文、配置或请求密码。"""
from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException


class APIError(Exception):
    def __init__(self, status, code, message, details=None):
        self.status, self.code, self.message = status, code, message
        self.details = details or {}


def response(request, status, code, message, details=None):
    return JSONResponse(status_code=status, content={'error': {'code': code, 'message': message, 'details': details or {}},
                                                     'request_id': request.state.request_id})


def install(app):
    from app.knowledge.repository import ConflictError, ScopeError

    @app.exception_handler(ConflictError)
    async def conflict_error(request: Request, exc):
        return response(request, 409, 'version_conflict', '资料版本或幂等请求内容冲突，请刷新后重试。')

    @app.exception_handler(ScopeError)
    async def scope_error(request: Request, exc):
        return response(request, 404, 'not_found', '资源不存在或不在授权范围。')

    @app.exception_handler(APIError)
    async def api_error(request: Request, exc: APIError):
        return response(request, exc.status, exc.code, exc.message, exc.details)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        return response(request, exc.status_code, 'http_error', '请求无法完成。')

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        return response(request, 422, 'validation_error', '请求字段格式不正确。',
                        {'fields': [list(e['loc']) for e in exc.errors()]})

    @app.exception_handler(Exception)
    async def unexpected(request: Request, exc: Exception):
        return response(request, 500, 'internal_error', '服务暂时无法完成请求。')
