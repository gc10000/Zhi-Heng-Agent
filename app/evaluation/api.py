"""维护者评测工作台；浏览器只提交服务端登记身份。"""
from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel, ConfigDict, Field
from app.api.errors import APIError
from app.identity.api import principal, require_writer, require_kb
from .reviews import ReviewInput, CalibrationInput, ReviewService
from .review_followups import FollowupInput
from .feedback_triage import TriageInput, authorized_feedback, public_feedback, review_feedback
from .feedback_triage import BindRevisionInput, bind_revision
from .feedback_triage import QualityProofInput, save_quality_proof

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


@router.post('/experiments/{eid}/reviews/{review_id}/followups', status_code=201)
def review_followup(eid: str, review_id: str, data: FollowupInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return ReviewService(service(request).repo).followup(user, eid, review_id, data)


@router.post('/experiments/{eid}/calibrations', status_code=201)
def calibrate(eid: str, data: CalibrationInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return ReviewService(service(request).repo).calibrate(user, eid, data)


@router.get('/experiments/{eid}/release-gate')
def release_gate(eid: str, calibration_id: str, request: Request, user=Depends(principal)):
    require_writer(user)
    return ReviewService(service(request).repo).gate(user, eid, calibration_id)


@router.get('/feedback')
def feedback_queue(request: Request, kb_id: str, cursor: str | None = Query(None, max_length=128),
                   limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    require_writer(user)
    require_kb(user, kb_id)
    query = {'kb_id': kb_id}
    if cursor:
        query['feedback_id'] = {'$gt': cursor}
    rows = list(request.app.state.resources['db'].support_feedback.find(query).sort('feedback_id', 1).limit(limit + 1))
    # 任一来源撤权则整页拒绝，不能回显反馈笔记或旧答案快照。
    items = [public_feedback(authorized_feedback(request, user, r['feedback_id'])) for r in rows[:limit]]
    return {'items': items, 'next_cursor': rows[limit - 1]['feedback_id'] if len(rows) > limit else None}


@router.post('/feedback/{feedback_id}/review')
def triage_feedback(feedback_id: str, data: TriageInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return review_feedback(request, user, feedback_id, data)


@router.post('/feedback/{feedback_id}/bind-revision')
def bind_feedback_revision(feedback_id: str, data: BindRevisionInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return bind_revision(request, user, feedback_id, data)


@router.post('/feedback/{feedback_id}/quality-proof')
def feedback_quality_proof(feedback_id: str, data: QualityProofInput, request: Request, user=Depends(principal)):
    require_writer(user)
    return save_quality_proof(request, user, feedback_id, data)
