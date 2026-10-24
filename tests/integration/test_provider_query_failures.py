"""供应商异常经正式运行入口向外传播；真实Mongo，异常注入，付费零。"""
from types import SimpleNamespace
import httpx
import openai
import pytest
from tests.integration.test_run_claim import run_context, request
from tests.integration.test_query_runs import query_context
from app.infrastructure.providers.clients import PolicyChatClient
from app.infrastructure.providers.policy import ProviderPolicy

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('mode,code,retryable', [('timeout', 'upstream_timeout', True),
    ('connection', 'upstream_connection_failed', True), (429, 'provider_rate_limited', True),
    (503, 'provider_unavailable', True), (401, 'provider_authentication_failed', False),
    (403, 'provider_authentication_failed', False), (404, 'provider_model_not_found', False)])
@pytest.mark.parametrize('wrapped', [False, True])
def test_sdk_error_after_partial_answer_never_completes_and_saves_safe_code(query_context, mode, code, retryable, wrapped):
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    class Failure:
        def stream(self, prompt, **options):
            yield SimpleNamespace(content='已生成部分')
            req = httpx.Request('POST', 'https://private.invalid')
            if mode == 'timeout': raise openai.APITimeoutError(request=req)
            if mode == 'connection': raise openai.APIConnectionError(request=req)
            raise openai.APIStatusError('SYNTHETIC-PRIVATE-RESPONSE', response=httpx.Response(mode, request=req), body={})
    runner.llm_factory = lambda: PolicyChatClient(Failure(), ProviderPolicy('text')) if wrapped else Failure()
    rid = service.create(user, cid, request())['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'failed' and row['answer'] == '已生成部分'
    assert row['error'] == {'code': code, 'stage': 'answer', 'retryable': retryable}
    assert conv.messages.count_documents({'run_id': rid, 'role': 'assistant'}) == 0
    events = runner.events.read(user, rid)
    assert sum(e['type'] == 'run.failed' for e in events) == 1
    assert not any(e['type'] == 'run.completed' for e in events)
    assert 'SYNTHETIC-PRIVATE-RESPONSE' not in str(row['error']) and 'private.invalid' not in str(row['error'])
