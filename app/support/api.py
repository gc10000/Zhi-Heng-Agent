"""支持流程命令复用登录、同源防伪、owner及知识范围授权。"""
from fastapi import APIRouter, Depends, Request, Query
from app.identity.api import principal
from .models import SupportInput, ChecklistInput, OperationReport, CaseInput, CasePatch
from app.runs.commands import VersionInput
from .repository import SupportRepository, now
from app.api.errors import APIError

router = APIRouter(prefix='/api/v1', tags=['支持流程'])


def support(request):
    resources = request.app.state.resources
    return SupportRepository(resources['conversations'], resources['runs'])


@router.get('/conversations/{cid}/support')
def get_support(cid: str, request: Request, user=Depends(principal)):
    row = support(request).get(user, cid)
    authorize_payload(request, user, row)
    return row


@router.post('/conversations/{cid}/support')
def update_support(cid: str, data: SupportInput, request: Request, user=Depends(principal)):
    repository = support(request)
    authorize_payload(request, user, repository.get(user, cid))
    if data.run_id:
        authorize_payload(request, user, request.app.state.resources['runs'].get(user, data.run_id).get('citations', []))
    return repository.update(user, cid, data)


def authorize_payload(request, user, payload):
    """连同历史/工具输出中的精确资料身份重新授权，撤权后不回显嵌套快照。"""
    identities = set()
    def collect(value):
        if isinstance(value, dict):
            if value.get('document_id') and value.get('revision_id'):
                identities.add((value['document_id'], value['revision_id']))
            for nested in value.values():
                collect(nested)
        elif isinstance(value, list):
            for nested in value:
                collect(nested)
    collect(payload)
    if identities:
        gateway = request.app.state.resources['knowledge']()
        for document_id, revision_id in identities:
            gateway.revision(user, document_id, revision_id)


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
    from .commands import check_run_context
    check_run_context(current, run, allow_bound=True)
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
    authorize_payload(request, user, current)
    return repository.save(user, cid, current, record_result(current, oid, data, at=now(), user_id=user.user_id))


def cases(request):
    from .cases import CaseRepository
    return CaseRepository(support(request))


def authorized_case(request, user, case):
    authorize_payload(request, user, case)
    return case


@router.post('/cases', status_code=201)
def create_case(data: CaseInput, request: Request, user=Depends(principal)):
    run = request.app.state.resources['runs'].get(user, data.run_id)
    authorize_citations(request, user, run.get('citations', []))
    return authorized_case(request, user, cases(request).create(user, data))


@router.get('/cases')
def list_cases(request: Request, cursor: str | None = None, limit: int = Query(50, ge=1, le=100), user=Depends(principal)):
    rows = cases(request).list(user, cursor=cursor, limit=limit)
    for row in rows['items']:
        authorized_case(request, user, row)
    return rows


@router.get('/cases/{case_id}')
def get_case(case_id: str, request: Request, user=Depends(principal)):
    return authorized_case(request, user, cases(request).get(user, case_id))


@router.patch('/cases/{case_id}')
def patch_case(case_id: str, data: CasePatch, request: Request, user=Depends(principal)):
    repository = cases(request)
    authorized_case(request, user, repository.get(user, case_id))
    return repository.patch(user, case_id, data)


@router.post('/cases/{case_id}/confirm')
def confirm_case(case_id: str, data: VersionInput, request: Request, user=Depends(principal)):
    repository = cases(request)
    authorized_case(request, user, repository.get(user, case_id))
    return repository.confirm(user, case_id, data.expected_version)


from .tools import ToolInput
from .feedback import FeedbackInput


@router.post('/conversations/{cid}/support/tools')
def call_tool(cid: str, data: ToolInput, request: Request, user=Depends(principal)):
    from .tools import execute_tool, scoped_handlers
    repository = support(request)
    context = repository.get(user, cid)
    authorize_payload(request, user, context)
    result = execute_tool(repository, user, cid, data, scoped_handlers(request, user, cid, context))
    authorize_payload(request, principal(request), result)
    return result


@router.get('/cases/{case_id}/export')
def export_case(case_id: str, request: Request, user=Depends(principal)):
    from .export import export_markdown
    return export_markdown(authorized_case(request, user, cases(request).get(user, case_id)))


@router.post('/feedback', status_code=201)
def feedback(data: FeedbackInput, request: Request, user=Depends(principal)):
    from .feedback import save_feedback
    resources = request.app.state.resources
    run = resources['runs'].get(user, data.run_id)
    selected = [c for c in run.get('citations',[]) if c['citation_id'] in data.citation_ids]
    authorize_citations(request, user, selected)
    return save_feedback(resources['db'],user,run,data)
