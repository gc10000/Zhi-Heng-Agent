"""有限白名单，只允许后端作用域下读取；文档正文从不作为指令执行。"""
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from copy import deepcopy
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from app.api.errors import APIError
from app.knowledge.repository import fingerprint
from .budget import ToolBudget, stop_reason, result_cost, repeated
from .repository import now


class ToolInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0)
    tool: Literal['lookup_product', 'read_evidence', 'search_manual']
    arguments: dict = Field(default_factory=dict, max_length=2)


class EvidenceArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    citation_id: str = Field(min_length=1, max_length=128)


class ProductArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    product_id: str = Field(min_length=1, max_length=128)


class SearchArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=1, max_length=1000)


class ToolOutput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    items: list[dict] = Field(max_length=10)
    notice: str = Field(max_length=1000)


SCHEMAS = {'lookup_product': ProductArgs, 'read_evidence': EvidenceArgs, 'search_manual': SearchArgs}
_POOL = ThreadPoolExecutor(max_workers=2, thread_name_prefix='支持只读工具')
_SLOTS = threading.BoundedSemaphore(2)


def invoke_bounded(handler, arguments, seconds):
    if not _SLOTS.acquire(blocking=False):
        raise APIError(409, 'tool_busy', '只读工具正忙，请转交或稍后处理。')
    def work():
        try:
            return handler(arguments)
        finally:
            _SLOTS.release()
    future = _POOL.submit(work)
    try:
        return future.result(timeout=seconds)
    except FutureTimeout:
        # 同步模型/数据库不保证硬中断；晚到结果不写任何账本，槽位结束后才释放。
        raise APIError(408, 'tool_timeout', '只读工具超时，已停止接纳结果。') from None


def execute_tool(repository, user, cid, data, handlers, *, policy=None, invoke=invoke_bounded, clock=time.monotonic):
    policy = policy or ToolBudget()
    current = repository.editable(user, cid, data.expected_version)
    if current['state'] == 'handoff':
        raise APIError(409, 'support_terminal', '已转交支持，不能继续调用工具。')
    if data.tool not in SCHEMAS or data.tool not in handlers:
        raise APIError(422, 'unknown_tool', '工具不在只读白名单中。')
    try:
        arguments = SCHEMAS[data.tool].model_validate(data.arguments).model_dump()
    except ValidationError:
        raise APIError(422, 'invalid_tool_arguments', '工具参数不符合固定格式。') from None
    row = deepcopy(current)
    calls = row['tool_calls']
    reason = stop_reason(calls, policy)
    if not reason and data.tool == 'search_manual' and sum(c['tool'] == data.tool for c in calls) >= policy.max_searches:
        reason = 'tool_search_budget'
    if reason == 'tool_inflight':
        raise APIError(409, reason, '已有工具调用待核对；超时后结束支持，不重复执行。')
    if reason:
        row.update(state='handoff', reason=reason, requested_slot=None, prompt='工具预算已达上限，请转交人工支持。')
        return repository.save(user, cid, current, row)
    ticket = uuid4().hex
    calls.append({'call_id': ticket, 'tool': data.tool, 'status': 'running', 'started_at': now(), 'arguments': arguments})
    reserved = repository.save(user, cid, current, row)
    began = clock()
    remaining = policy.max_seconds - sum(c.get('elapsed', 0) for c in calls)
    reason, output = None, None
    try:
        output = ToolOutput.model_validate(invoke(handlers[data.tool], arguments, remaining)).model_dump()
        if result_cost(output) + sum(c.get('tokens',0) for c in calls) > policy.max_tokens:
            reason, output = 'tool_token_budget', None
        elif repeated(calls[:-1], output):
            reason = 'tool_repeat'
    except Exception as exc:
        # 不保存上游原文错误、路径、凭据或私有prompt。
        reason = 'tool_timeout' if isinstance(exc, APIError) and exc.code == 'tool_timeout' else 'tool_failed'
    elapsed = max(0, clock() - began)
    if elapsed >= remaining:
        reason, output = 'tool_time_budget', None
    completed = deepcopy(reserved)
    completed['tool_calls'][-1].update(status='failed' if reason and output is None else 'completed',
        elapsed=elapsed, tokens=result_cost(output) if output else 0, output=output,
        output_hash=fingerprint(output) if output else None, finished_at=now(), reason=reason)
    if reason:
        completed.update(state='handoff', reason=reason, requested_slot=None, prompt='工具未获得新可用证据或达到预算，请转交人工支持。')
    # 预留版本和token属于当前聚合；取消/纠正/并发命令后，迟到结果CAS失败。
    return repository.save(user, cid, reserved, completed)


def scoped_handlers(request, user, cid, context):
    resources = request.app.state.resources
    gateway = resources['knowledge']()
    kb = resources['conversations'].get(user, cid)['kb_id']
    def read(arguments):
        selected = next((c for c in context['citations'] if c['citation_id'] == arguments['citation_id']), None)
        if selected is None:
            raise APIError(404, 'not_found', '引用不在本支持流程中。')
        gateway.revision(user, selected['document_id'], selected['revision_id'])
        return {'items': [deepcopy(selected)], 'notice': '内部资料原文，仅供人工核对。'}
    def product(arguments):
        row = gateway.product(user, arguments['product_id'], kb)
        return {'items': [{k: row[k] for k in ('product_id','model','brand','series','aliases') if k in row}], 'notice': '当前授权产品目录。'}
    def search(arguments):
        run = resources['runs'].get(user, context['run_id']) if context['run_id'] else None
        ids = run.get('product_snapshot', {}).get('product_ids', []) if run else []
        if not ids:
            raise APIError(409, 'product_required', '请先在问答中确认设备范围。')
        for pid in ids:
            gateway.product(user, pid, kb)
        from app.retrieval.models import QueryPlan
        from app.retrieval.search import retrieve, RetrievalPolicy
        from app.retrieval.adapters import from_index_hits
        from app.runs.query_runner import encode
        repo = gateway.repo(kb)
        revisions = repo.get_active_revisions()
        plan = QueryPlan(original_query=arguments['query'], product_ids=tuple(ids), search_queries=(arguments['query'],), scope_groups=(tuple(ids),))
        runner = resources.get('query_runner')
        hits = retrieve(gateway.index(), repo, plan, embedder=runner.embedder if runner else encode,
                        revision_snapshot=revisions, policy=RetrievalPolicy())
        items = []
        for hit in from_index_hits(hits)[:10]:
            gateway.revision(user, hit.document_id, hit.revision_id)
            items.append({'document_id':hit.document_id, 'revision_id':hit.revision_id, 'chunk_uid':hit.chunk_uid,
                          'text':hit.text, 'source_refs':hit.metadata.get('source_refs', [])})
        return {'items': items, 'notice': '内部扩展检索结果，尚未作为答案或操作事实。'}
    return {'read_evidence': read, 'lookup_product': product, 'search_manual': search}
