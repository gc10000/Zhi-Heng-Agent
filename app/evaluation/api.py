"""维护者评测工作台；浏览器只提交服务端登记身份。"""
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from app.api.errors import APIError
from app.identity.api import principal, require_writer, require_kb
from .reviews import ReviewInput, CalibrationInput, ReviewService

router = APIRouter(prefix='/api/v1', tags=['评测'])


class RegisterSetInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kb_id: str = Field(min_length=1, max_length=128)
    eval_set_id: str = Field(min_length=1, max_length=128)
    version: str = Field(min_length=1, max_length=128)


class ExperimentInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    kb_id: str = Field(min_length=1, max_length=128)
    eval_set_id: str = Field(min_length=1, max_length=128)
    eval_set_version: str = Field(min_length=1, max_length=128)
    config_id: str = Field(min_length=1, max_length=128)
    config_version: str = Field(default='v1', min_length=1, max_length=128)
    baseline_experiment_id: str | None = Field(default=None, max_length=128)
    client_request_id: str = Field(min_length=1, max_length=128)


class VersionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0, strict=True)


def service(request):
    value = request.app.state.resources.get('evaluations')
    if value is None:
        raise APIError(503, 'evaluation_unconfigured', '请配置M6_EVALUATION_CATALOG和M6_EVALUATION_WORK_DIR以启用评测。')
    return value


@router.get('/eval-catalog')
def catalog(request: Request, kb_id: str, user=Depends(principal)):
    require_writer(user)
    require_kb(user, kb_id)
    return service(request).catalog_options(kb_id)


@router.get('/eval-sets')
def list_sets(request: Request, kb_id: str, user=Depends(principal)):
    require_writer(user)
    require_kb(user, kb_id)
    return service(request).list_sets(user, kb_id)


@router.post('/eval-sets', status_code=201)
def register(data: RegisterSetInput, request: Request, user=Depends(principal)):
    require_writer(user)
    require_kb(user, data.kb_id)
    return service(request).register_set(user, data.model_dump())


@router.get('/experiments')
def list_experiments(request: Request, kb_id: str, user=Depends(principal)):
    require_writer(user)
    require_kb(user, kb_id)
    return service(request).list_experiments(user, kb_id)


@router.post('/experiments', status_code=202)
def create(data: ExperimentInput, request: Request, user=Depends(principal)):
    require_writer(user)
    require_kb(user, data.kb_id)
    return service(request).create_experiment(user, data.model_dump())


@router.get('/experiments/{eid}')
def get(eid: str, request: Request, user=Depends(principal)):
    require_writer(user)
    return service(request).get_experiment(user, eid)


@router.get('/experiments/{eid}/results')
def results(eid: str, request: Request, cursor: str | None = Query(None, max_length=128),
            limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    require_writer(user)
    return service(request).results_page(user, eid, cursor=cursor, limit=limit)


@router.post('/experiments/{eid}/cancel')
def cancel(eid: str, data: VersionInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return service(request).cancel(user, eid, data.expected_version)


@router.post('/experiments/{eid}/retry', status_code=202)
def retry(eid: str, data: VersionInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return service(request).retry(user, eid, data.expected_version)


@router.get('/experiments/{eid}/reviews')
def reviews(eid: str, request: Request, user=Depends(principal)):
    require_writer(user)
    return ReviewService(service(request).repo).list(user, eid)


@router.post('/experiments/{eid}/reviews', status_code=201)
def review(eid: str, data: ReviewInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return ReviewService(service(request).repo).submit(user, eid, data)


@router.post('/experiments/{eid}/calibrations', status_code=201)
def calibrate(eid: str, data: CalibrationInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return ReviewService(service(request).repo).calibrate(user, eid, data)


@router.get('/experiments/{eid}/release-gate')
def release_gate(eid: str, calibration_id: str, request: Request, user=Depends(principal)):
    require_writer(user)
    return ReviewService(service(request).repo).gate(user, eid, calibration_id)
