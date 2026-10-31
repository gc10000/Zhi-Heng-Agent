"""仅用于显式诊断的输出能力与计账合同；未知不放行，不推断网关语义。"""
import json
from datetime import datetime, timezone
from importlib.metadata import version
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.knowledge.repository import fingerprint
from app.answering.reviewed_subjects import GitEvidence, evidence_bytes
from .diagnostic_usage import ABSENT


class OutputContract(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    enabled: bool = Field(default=False, strict=True)
    function_version: Literal['diagnostic_total_output_v2'] = 'diagnostic_total_output_v2'
    n: int = Field(default=1,ge=1,le=1,strict=True)
    status: Literal['unknown', 'verified'] = 'unknown'
    endpoint_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    model: str = Field(min_length=1, max_length=200)
    client_versions: dict[str, str] = Field(min_length=1, max_length=10)
    limit_field: Literal['max_tokens', 'max_completion_tokens'] = 'max_tokens'
    semantics: Literal['unknown', 'visible', 'total_including_reasoning'] = 'unknown'
    thinking: bool | None = Field(default=None, strict=True)
    reasoning_budget: int | None = Field(default=None, ge=0, strict=True)
    evidence: GitEvidence | None = None
    per_request_total_output_tokens: int = Field(default=4096, ge=1, le=4096, strict=True)
    ledger_id: str = Field(min_length=1, max_length=128)
    max_total_output_tokens: int = Field(ge=1, strict=True)
    prior_input_tokens: int = Field(default=0, ge=0, strict=True)
    prior_output_tokens: int = Field(default=0, ge=0, strict=True)
    prior_source_sha256: str | None = Field(default=None, pattern=r'^[a-f0-9]{64}$')
    max_total_input_tokens: int = Field(default=1477632, ge=1, strict=True)

    @model_validator(mode='after')
    def complete(self):
        if ((self.prior_input_tokens or self.prior_output_tokens) and not self.prior_source_sha256 or
                self.max_total_output_tokens < self.prior_output_tokens + self.per_request_total_output_tokens or
                self.max_total_input_tokens < self.prior_input_tokens):
            raise ValueError('诊断累计预算或历史来源不完整')
        if self.status == 'verified' and (self.evidence is None or self.semantics != 'total_including_reasoning'):
            raise ValueError('诊断仅接受有适用证据的含reasoning总输出硬限')
        return self


def payload(value):
    if value is None:return None
    policy=OutputContract.model_validate(value)
    return policy.model_dump(mode='json') if policy.enabled else None


def from_config(config):
    return config.get('parameters', {}).get('answer_budget', {}).get('output_contract')


def identity(value):
    value = payload(value)
    if not value or not value['enabled']:return {}
    body={value['limit_field']:value['per_request_total_output_tokens']}
    if value['thinking'] is not None:body['enable_thinking']=value['thinking']
    if value['reasoning_budget'] is not None:body['thinking_budget']=value['reasoning_budget']
    return {'output_contract': value, 'output_contract_sha256': fingerprint(value),
            'output_parameters_sha256':fingerprint({'extra_body':body,'n':value['n'],'sdk_max_retries':0,
                'usage_validation':'raw_usage_v2'})}


def validate_run(row, value):
    current = payload(value)
    saved = payload(row.get('output_contract'))
    expected=identity(value)
    if (not expected and any(k in row for k in ('output_contract','output_contract_sha256','output_parameters_sha256'))) or current != saved or any(row.get(k)!=v for k,v in expected.items()) or (
            'output_contract' in row and row.get('output_contract_sha256') != fingerprint(saved)):
        raise APIError(409, 'execution_config_conflict', '诊断输出合同或能力身份变化，拒绝复用旧Run。')


def require_capability(value):
    policy = OutputContract.model_validate(value)
    if not policy.enabled:return policy
    if policy.status != 'verified' or policy.semantics != 'total_including_reasoning' or policy.evidence is None:
        raise APIError(422, 'output_capability_unknown', '网关总输出限制能力未知，诊断调用暂停。')
    proof = json.loads(evidence_bytes(policy.evidence))
    expected = {k: getattr(policy, k) for k in ('endpoint_sha256', 'model', 'client_versions',
        'limit_field', 'semantics', 'thinking', 'reasoning_budget','n')}
    if (proof.get('kind') != 'gateway_output_capability_evidence_v1' or
            proof.get('identity') != expected or proof.get('status') != 'verified' or
            proof.get('server_hard_limit') is not True or proof.get('evidence_type') not in
                {'applicable_gateway_contract', 'authorized_gateway_probe'} or
            type(proof.get('max_verified_total_tokens')) is not int or
            proof['max_verified_total_tokens'] < policy.per_request_total_output_tokens):
        raise APIError(422, 'output_capability_evidence_invalid', '网关能力证据不适用当前身份或总输出预算。')
    return policy


def unwrap_client(client):
    seen = set()
    while hasattr(client, 'client') and id(client) not in seen:
        seen.add(id(client));child = client.client
        # ChatOpenAI.client是SDK资源，不是策略包装；在模型端点层停止。
        if getattr(client, 'model_name', None) and getattr(client, 'openai_api_base', None):break
        client = child
    return client


def strict_options(client, limit, field, contract):
    policy = require_capability(contract)
    underlying = unwrap_client(client)
    if not policy.enabled:raise ValueError('关闭合同不使用严格发参入口')
    if field != policy.limit_field or limit != policy.per_request_total_output_tokens:
        raise ValueError('输出字段或总预算与能力合同冲突')
    if (fingerprint(str(getattr(underlying, 'openai_api_base', ''))) != policy.endpoint_sha256 or
            getattr(underlying, 'model_name', None) != policy.model or
            {k: version(k) for k in policy.client_versions} != policy.client_versions):
        raise ValueError('实际客户端、模型或端点hash与能力证据不符')
    # 同一逻辑调用不能让SDK静默重试造成未结算付费窗口。
    if getattr(underlying, 'max_retries', None) != 0:
        raise ValueError('诊断能力合同要求SDK不自动重试')
    declared_n=getattr(underlying,'n',None)
    if declared_n is not None and (type(declared_n) is not int or declared_n!=policy.n):
        raise ValueError('诊断仅允许已绑定的单份生成n=1')
    body = dict(getattr(underlying, 'extra_body', None) or {})
    if set(body)-{'max_tokens','max_completion_tokens','enable_thinking','thinking_budget'}:
        raise ValueError('诊断存在未绑定的额外wire参数，拒绝静默消费')
    model_kwargs = dict(getattr(underlying, 'model_kwargs', None) or {})
    if (model_kwargs or getattr(underlying,'default_query',None) or
            getattr(underlying, 'max_tokens', None) is not None or
            getattr(underlying, 'max_completion_tokens', None) is not None or
            any(getattr(underlying,k,None) is not None for k in ('reasoning','reasoning_effort')) or
            any(k in body for k in ('thinking','reasoning','reasoning_effort'))):
        raise ValueError('诊断限制与客户端默认参数冲突')
    other = 'max_completion_tokens' if field == 'max_tokens' else 'max_tokens'
    if other in body or field in body and (body[field] != limit or type(body[field]) is not int):
        raise ValueError('诊断限制字段冲突，禁止静默覆盖')
    if (body.get('enable_thinking') != policy.thinking or body.get('thinking_budget') != policy.reasoning_budget or
            ('enable_thinking' in body and type(body['enable_thinking']) is not bool) or
            ('thinking_budget' in body and type(body['thinking_budget']) is not int)):
        raise ValueError('thinking设置与适用能力证据不一致')
    body[field] = limit
    # 安装SDK会合并typed/model_kwargs并改写旧限额名；检查最终构造，绝不覆盖坏值。
    if callable(getattr(underlying,'_get_request_payload',None)):
        effective=underlying._get_request_payload('',n=policy.n,extra_body=body)
        if (type(effective.get('n')) is not int or effective['n']!=policy.n or
                effective.get('model')!=policy.model or
                any(k in effective for k in ('max_tokens','max_completion_tokens','reasoning','reasoning_effort')) or
                effective.get('extra_body')!=body or
                underlying._use_responses_api(effective)):
            raise ValueError('实际SDK请求与单份ChatCompletions合同不一致')
    return {'n':policy.n,'extra_body': body}


def usage_receipt(usage, *, reasoning=ABSENT, observations=None):
    from .diagnostic_usage import observe_usage,summarize
    raw=dict(usage) if isinstance(usage,dict) else usage
    validation=summarize(observations if observations else [observe_usage(raw,source='direct',reasoning=reasoning)])
    counts=validation['reported']
    if observations and isinstance(usage,dict):
        for key in ('input','output'):
            if counts[key] is not None and type(usage.get(key)) is int and counts[key]!=usage[key]:
                validation['errors'].append('telemetry_'+key+'_conflict');validation['valid']=False
    input_tokens,output_tokens=(counts['input'],counts['output']) if validation['valid'] else (None,None)
    reasoning=counts['reasoning'] if validation['valid'] else None
    return dict(input_tokens=input_tokens, output_tokens=output_tokens, reasoning_tokens=reasoning,
        output_minus_reasoning=output_tokens-reasoning if output_tokens is not None and reasoning is not None and reasoning <= output_tokens else None,
        reported_input_tokens=counts['input'],reported_output_tokens=counts['output'],
        usage_validation=validation,visible_tokens=None, http_requests=None, cost=None)


class OutputLedger:
    """在现有Run执行边界串行结算，不调度job。未知窗口持久阻断下一题。"""
    def __init__(self, db, contract):
        self.policy = OutputContract.model_validate(contract)
        self.rows = db.diagnostic_output_accounts
        self.key = fingerprint(['diagnostic_total_output_v1', self.policy.ledger_id])
        self.sha = fingerprint(payload(self.policy))

    def _read(self):
        saved = self.rows.find_one({'_id': self.key})
        if not saved or saved.get('contract_sha256') != self.sha:
            raise APIError(409, 'output_account_identity_conflict', '诊断累计账本身份变化。')
        return saved

    def _cas(self, prior, values):
        result = self.rows.update_one({'_id': self.key, 'version': prior['version']},
            {'$set': values, '$inc': {'version': 1}})
        if not result.matched_count:raise APIError(409, 'output_account_busy', '诊断结算并发冲突，停止派发。')

    def begin(self, run_id, run_identity, *, input_reservation=0):
        require_capability(self.policy)
        row = dict(contract_sha256=self.sha, version=0, state='open', pending=None,
            settled={}, new_input_tokens=0, new_output_tokens=0, known_new_input_tokens=0,known_new_output_tokens=0,
            logical_reservations=0, unknown_windows=[],
            prior_input_tokens=self.policy.prior_input_tokens, prior_output_tokens=self.policy.prior_output_tokens,
            exact_http_requests=None, exact_cost=None)
        try:self.rows.update_one({'_id': self.key}, {'$setOnInsert': row}, upsert=True)
        except DuplicateKeyError:pass
        saved = self._read()
        if type(input_reservation) is not int or input_reservation<0:raise ValueError('输入预留须为非负整数')
        if (saved['state'] != 'open' or saved['pending'] is not None or
                fingerprint(run_id) in saved['settled'] or
                saved['prior_output_tokens'] + saved['new_output_tokens'] + self.policy.per_request_total_output_tokens > self.policy.max_total_output_tokens or
                saved['prior_input_tokens'] + saved['new_input_tokens'] + input_reservation > self.policy.max_total_input_tokens):
            raise APIError(409, 'output_account_blocked', '诊断存在未结算、重复调用或剩余预算不足，停止派发。')
        self._cas(saved, dict(state='pending', pending=dict(run_id=run_id, run_identity=run_identity,
            input_reservation=input_reservation,started_at=datetime.now(timezone.utc).isoformat()),
            new_input_tokens=None,new_output_tokens=None,logical_reservations=saved['logical_reservations']+1))

    def settle(self, run_id, run_identity, usage, *, completed, reasoning=ABSENT, logical_calls=None,observations=None):
        receipt = usage_receipt(usage, reasoning=reasoning,observations=observations) | dict(run_id=run_id, run_identity=run_identity, completed=bool(completed))
        keys=('invoke_started','stream_started')
        receipt['logical_provider_calls']={k:logical_calls[k] for k in keys} if isinstance(logical_calls,dict) and all(
            type(logical_calls.get(k)) is int and logical_calls[k]>=0 for k in keys) else None
        saved = self._read();key = fingerprint(run_id)
        if key in saved['settled']:
            if saved['settled'][key] != receipt:raise APIError(409, 'output_settlement_conflict', '相同调用的结算内容改变。')
            return saved  # 崩溃重放只复用同一结算；不重置或再次增加usage。
        if not saved['pending'] or any(saved['pending'].get(k) != v for k,v in dict(run_id=run_id, run_identity=run_identity).items()):
            raise APIError(409, 'output_settlement_conflict', '没有匹配的调用前持久关联。')
        known = receipt['input_tokens'] is not None and receipt['output_tokens'] is not None
        output = saved['known_new_output_tokens'] + (receipt['output_tokens'] or 0)
        input_tokens = saved['known_new_input_tokens'] + (receipt['input_tokens'] or 0)
        good = (known and receipt['usage_validation']['valid'] and completed and receipt['output_tokens'] <= self.policy.per_request_total_output_tokens and
            saved['prior_output_tokens'] + output <= self.policy.max_total_output_tokens and
            saved['prior_input_tokens'] + input_tokens <= self.policy.max_total_input_tokens)
        windows = list(saved['unknown_windows'])
        if not receipt['usage_validation']['valid']:
            windows.append(dict(run_id=run_id,reason='invalid_usage',errors=receipt['usage_validation']['errors']))
        elif not known or not completed:windows.append(dict(run_id=run_id,reason='missing_usage_or_incomplete'))
        self._cas(saved, dict(state='open' if good else 'blocked',pending=None,settled=saved['settled'] | {key:receipt},
            known_new_input_tokens=input_tokens,known_new_output_tokens=output,
            new_input_tokens=input_tokens if known and completed else None,new_output_tokens=output if known and completed else None,
            unknown_windows=windows))
        return self._read()

    def require_open(self):
        saved = self._read()
        if saved['state'] != 'open' or saved['unknown_windows']:
            raise APIError(409, 'output_account_blocked', '诊断usage缺失、未完成或总输出越界，后续调用保持暂停。')
        return saved
