"""支持流程命令复用登录、同源防伪、owner及知识范围授权。"""
from fastapi import APIRouter, Depends, Request
from app.identity.api import principal
from .models import SupportInput, ChecklistInput, OperationReport
from .repository import SupportRepository, now
from app.api.errors import APIError

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


def authorize_citations(request, user, citations):
    if not citations:
        return
    gateway = request.app.state.resources['knowledge']()
    for citation in citations:
        gateway.revision(user, citation['document_id'], citation['revision_id'])


@router.post('/conversations/{cid}/support/checklist')
def checklist(cid: str, data: ChecklistInput, request: Request, user=Depends(principal)):
    from .checklist import build_checklist
    repository = support(request)
    current = repository.editable(user, cid, data.expected_version)
    run = repository.completed_run(user, cid, data.run_id)
    authorize_citations(request, user, run.get('citations', []))
    row = build_checklist(current, run)
    if not row['operations']:
        row.update(state='handoff', reason='no_action_evidence', requested_slot=None, prompt='没有可核对的具体操作证据，请转交人工支持。')
    return repository.save(user, cid, current, row)


@router.post('/conversations/{cid}/support/operations/{oid}')
def operation(cid: str, oid: str, data: OperationReport, request: Request, user=Depends(principal)):
    from .checklist import record_result
    repository = support(request)
    current = repository.editable(user, cid, data.expected_version)
    return repository.save(user, cid, current, record_result(current, oid, data, at=now(), user_id=user.user_id))
