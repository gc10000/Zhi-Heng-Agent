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
from .product_risk import SingleProductAdmission
from .remaining_risk import RemainingAdmission


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


class SingleProductRiskContract(OutputContract):
    function_version: Literal['diagnostic_single_product_risk_v1'] = 'diagnostic_single_product_risk_v1'
    admission: SingleProductAdmission


class RemainingManifestContract(OutputContract):
    function_version: Literal['diagnostic_remaining_manifest_r1'] = 'diagnostic_remaining_manifest_r1'
    admission: RemainingAdmission


class NonthinkingManifestContract(OutputContract):
    function_version: Literal['diagnostic_nonthinking_manifest_r1'] = 'diagnostic_nonthinking_manifest_r1'
    thinking: bool = Field(strict=True)
    admission: RemainingAdmission

    @model_validator(mode='after')
    def explicit_false(self):
        if self.thinking is not False:raise ValueError('非思考清单仅允许显式false')
        return self


class SourceRelation048Contract(NonthinkingManifestContract):
    function_version: Literal['diagnostic_source_relation_048_v1'] = 'diagnostic_source_relation_048_v1'


COMPARISON_ANSWER_048_SLOT = 'm6-comparison-answer-048-r7-support-v1-048'
COMPARISON_ANSWER_048_AUTHORIZATION_PATH = 'docs/development/reviews/M6-comparison-answer-048-authorization-r7.json'
COMPARISON_ANSWER_048_V2_SLOT = 'm6-comparison-answer-048-r8-support-v1-048'
COMPARISON_ANSWER_048_V2_AUTHORIZATION_PATH = 'docs/development/reviews/M6-comparison-answer-048-authorization-r8.json'


class ComparisonAnswer048Admission(SingleProductAdmission):
    member_slot: Literal[COMPARISON_ANSWER_048_SLOT]


class ComparisonAnswer048Contract(NonthinkingManifestContract):
    function_version: Literal['diagnostic_comparison_answer_048_v1'] = 'diagnostic_comparison_answer_048_v1'
    admission: ComparisonAnswer048Admission

    @model_validator(mode='after')
    def fixed_single_comparison_profile(self):
        admission = self.admission
        if admission.authorization.path != COMPARISON_ANSWER_048_AUTHORIZATION_PATH:
            raise ValueError('比较048风险合同必须引用专用Git授权路径')
        if (self.status != 'unknown' or self.semantics != 'unknown' or self.evidence is not None or
                self.n != 1 or self.model != 'qwen3.8-flash' or
                self.client_versions != {'openai': '2.28.0', 'langchain-openai': '1.1.11'} or
                self.limit_field != 'max_completion_tokens' or self.thinking is not False or
                self.reasoning_budget is not None or self.per_request_total_output_tokens != 4096 or
                self.ledger_id != 'm6-comparison-answer-048-canary-r7' or
                self.prior_input_tokens != 53089 or self.prior_output_tokens != 30412 or
                self.prior_source_sha256 is None or self.max_total_input_tokens != 81505 or
                self.max_total_output_tokens != 34508):
            raise ValueError('比较048风险合同超出固定单题profile或预算')
        return self


class ComparisonAnswer048V2Admission(SingleProductAdmission):
    member_slot: Literal[COMPARISON_ANSWER_048_V2_SLOT]


class ComparisonAnswer048V2Contract(NonthinkingManifestContract):
    function_version: Literal['diagnostic_comparison_answer_048_v2'] = 'diagnostic_comparison_answer_048_v2'
    admission: ComparisonAnswer048V2Admission

    @model_validator(mode='after')
    def fixed_single_comparison_profile(self):
        admission = self.admission
        if admission.authorization.path != COMPARISON_ANSWER_048_V2_AUTHORIZATION_PATH:
            raise ValueError('比较048 v2风险合同必须引用专用Git授权路径')
        if (self.status != 'unknown' or self.semantics != 'unknown' or self.evidence is not None or
                self.n != 1 or self.model != 'qwen3.8-flash' or
                self.client_versions != {'openai': '2.28.0', 'langchain-openai': '1.1.11'} or
                self.limit_field != 'max_completion_tokens' or self.thinking is not False or
                self.reasoning_budget is not None or self.per_request_total_output_tokens != 4096 or
                self.ledger_id != 'm6-comparison-answer-048-canary-r8' or
                self.prior_input_tokens != 54664 or self.prior_output_tokens != 30449 or
                self.prior_source_sha256 is None or self.max_total_input_tokens != 83080 or
                self.max_total_output_tokens != 34545):
            raise ValueError('比较048 v2风险合同超出固定单题profile或预算')
        return self


CONNECTION_048_VERSION = 'diagnostic_connection_comparison_048_v1'
CONNECTION_048_SLOT = 'm6-connection-comparison-048-r2-support-v1-048'
CONNECTION_048_AUTHORIZATION_PATH = 'docs/development/reviews/M6-connection-comparison-048-authorization-r2.json'


class ConnectionComparison048Admission(SingleProductAdmission):
    member_slot: Literal[CONNECTION_048_SLOT]


class ConnectionComparison048Contract(NonthinkingManifestContract):
    function_version: Literal['diagnostic_connection_comparison_048_v1'] = CONNECTION_048_VERSION
    admission: ConnectionComparison048Admission | None = None

    @model_validator(mode='after')
    def fixed_connection_profile(self):
        if self.enabled and self.admission is None:
            raise ValueError('连接048开启合同必须有专属授权，不以预检代替')
        if self.admission is not None and self.admission.authorization.path != CONNECTION_048_AUTHORIZATION_PATH:
            raise ValueError('连接048不能借用旧Git授权')
        expected = dict(status='unknown', semantics='unknown', evidence=None, n=1,
            model='qwen3.8-flash', client_versions={'openai':'2.28.0','langchain-openai':'1.1.11'},
            limit_field='max_completion_tokens', thinking=False, reasoning_budget=None,
            per_request_total_output_tokens=4096, ledger_id='m6-connection-comparison-048-r2',
            prior_input_tokens=56239, prior_output_tokens=30516,
            max_total_input_tokens=84655, max_total_output_tokens=34612)
        if any(getattr(self,k) != v for k,v in expected.items()) or self.prior_source_sha256 is None:
            raise ValueError('连接048合同超出固定单题身份或预算')
        return self


FEEDBACK_CANDIDATE_VERSION = 'diagnostic_feedback_candidate_manifest_r1'
FEEDBACK_CANDIDATE_BATCH = 'm6-feedback-candidate-full-r1'
FEEDBACK_CANDIDATE_AUTHORIZATION_PATH = 'docs/development/reviews/M6-feedback-stage-authorization-r1.json'
FEEDBACK_CANDIDATE_MEMBER_SLOTS = ('m6-feedback-stage-r1-v1', 'm6-feedback-stage-r1-v2')


class FeedbackCandidateAdmission(SingleProductAdmission):
    member_slot: Literal[FEEDBACK_CANDIDATE_MEMBER_SLOTS[0], FEEDBACK_CANDIDATE_MEMBER_SLOTS[1]]


class FeedbackCandidateContract(NonthinkingManifestContract):
    function_version: Literal[FEEDBACK_CANDIDATE_VERSION] = FEEDBACK_CANDIDATE_VERSION
    admission: FeedbackCandidateAdmission | None = None

    @model_validator(mode='after')
    def fixed_full_candidate_profile(self):
        if self.enabled and self.admission is None:
            raise ValueError('完整反馈候选必须通过170成员专属范围准入')
        if self.admission is not None and self.admission.authorization.path != FEEDBACK_CANDIDATE_AUTHORIZATION_PATH:
            raise ValueError('完整反馈候选不能借用单题或其他Git授权')
        expected = dict(status='unknown', semantics='unknown', evidence=None, n=1,
            model='qwen3.8-flash', client_versions={'openai':'2.28.0','langchain-openai':'1.1.11'},
            limit_field='max_completion_tokens', thinking=False, reasoning_budget=None,
            per_request_total_output_tokens=4096, ledger_id=FEEDBACK_CANDIDATE_BATCH,
            prior_input_tokens=0, prior_output_tokens=0, prior_source_sha256=None,
            max_total_input_tokens=168*28416, max_total_output_tokens=168*4096)
        if any(getattr(self,k) != v for k,v in expected.items()):
            raise ValueError('完整反馈候选超出固定全范围profile或预算')
        return self


class OperationalDemoContract(OutputContract):
    """仅本轮用户明确采用的八槽内部演示；不沿用M6授权或账本。"""
    function_version: Literal['m7_operational_demo_v1','m7_operational_demo_v2'] = 'm7_operational_demo_v1'
    manifest_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    authorization_sha256: str = Field(pattern=r'^[a-f0-9]{64}$')
    control_database: str = Field(pattern=r'^m1_test_m4_[a-z0-9_]{1,48}$')

    @model_validator(mode='after')
    def fixed_demo_profile(self):
        expected = dict(status='unknown', semantics='unknown', evidence=None, n=1,
            model='qwen3.8-flash', client_versions={'openai':'2.28.0','langchain-openai':'1.1.11'},
            limit_field='max_completion_tokens', thinking=False, reasoning_budget=None,
            per_request_total_output_tokens=4096, ledger_id=('m7-operational-closure-r2' if self.function_version=='m7_operational_demo_v2' else 'm7-operational-closure-r1'),
            prior_input_tokens=0, prior_output_tokens=0, prior_source_sha256=None,
            max_total_input_tokens=227328, max_total_output_tokens=32768)
        if any(getattr(self,k) != v for k,v in expected.items()):
            raise ValueError('内部演示超出固定profile或八槽预算')
        return self


def parse_contract(value):
    kind=value.get('function_version') if isinstance(value,dict) else getattr(value,'function_version',None)
    return {'diagnostic_single_product_risk_v1':SingleProductRiskContract,
            'diagnostic_remaining_manifest_r1':RemainingManifestContract,
            'diagnostic_nonthinking_manifest_r1':NonthinkingManifestContract,
            'diagnostic_source_relation_048_v1':SourceRelation048Contract,
            'diagnostic_comparison_answer_048_v1':ComparisonAnswer048Contract,
            'diagnostic_comparison_answer_048_v2':ComparisonAnswer048V2Contract,
            CONNECTION_048_VERSION:ConnectionComparison048Contract,
            FEEDBACK_CANDIDATE_VERSION:FeedbackCandidateContract,
            'm7_operational_demo_v1':OperationalDemoContract,
            'm7_operational_demo_v2':OperationalDemoContract}.get(kind,OutputContract).model_validate(value)


def is_product_risk(value):
    if value is None:return False
    policy=parse_contract(value)
    return policy.enabled and policy.function_version in ('diagnostic_single_product_risk_v1','diagnostic_remaining_manifest_r1','diagnostic_nonthinking_manifest_r1','diagnostic_source_relation_048_v1','diagnostic_comparison_answer_048_v1','diagnostic_comparison_answer_048_v2',CONNECTION_048_VERSION,FEEDBACK_CANDIDATE_VERSION,'m7_operational_demo_v1','m7_operational_demo_v2')


def risk_handler(value):
    """保持旧单题含义；新清单只进入其自己的封存授权及共享账本。"""
    policy=parse_contract(value)
    if not is_product_risk(policy):raise ValueError('关闭或普通合同不使用风险准入')
    if policy.function_version in ('m7_operational_demo_v1','m7_operational_demo_v2'):
        from . import m7_demo
        return m7_demo
    if policy.function_version == CONNECTION_048_VERSION:
        from . import connection_comparison_048_risk
        return connection_comparison_048_risk
    if policy.function_version == FEEDBACK_CANDIDATE_VERSION:
        from . import m6_feedback_candidate_risk
        return m6_feedback_candidate_risk
    if policy.function_version=='diagnostic_source_relation_048_v1':
        from . import source_relation_048_risk
        return source_relation_048_risk
    if policy.function_version=='diagnostic_comparison_answer_048_v1':
        from . import comparison_answer_048_risk
        return comparison_answer_048_risk
    if policy.function_version=='diagnostic_comparison_answer_048_v2':
        from . import comparison_answer_048_v2_risk
        return comparison_answer_048_v2_risk
    if policy.function_version=='diagnostic_nonthinking_manifest_r1':
        from . import nonthinking_risk
        return nonthinking_risk
    if policy.function_version=='diagnostic_remaining_manifest_r1':
        from . import remaining_risk
        return remaining_risk
    from . import product_risk
    return product_risk


def payload(value):
    if value is None:return None
    policy=parse_contract(value)
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
    policy = parse_contract(value)
    if not policy.enabled:return policy
    if is_product_risk(policy):
        # 准入依据是受控的单次风险授权，能力事实仍为unknown；普通v2分支不变。
        risk_handler(policy).require(policy)
        return policy
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
    if is_product_risk(policy):
        risk_handler(policy).validate_client(policy,underlying)
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
    def __new__(cls,db,contract):
        policy=parse_contract(contract)
        if policy.enabled and policy.function_version in ('m7_operational_demo_v1','m7_operational_demo_v2'):
            from .m7_demo import DemoLedger
            return DemoLedger(db,contract)
        if policy.enabled and policy.function_version == CONNECTION_048_VERSION:
            from .connection_comparison_048_risk import ConnectionComparison048Ledger
            return ConnectionComparison048Ledger(db,contract)
        if policy.enabled and policy.function_version == FEEDBACK_CANDIDATE_VERSION:
            from .m6_feedback_candidate_risk import FeedbackCandidateLedger
            return FeedbackCandidateLedger(db,contract)
        if policy.enabled and policy.function_version=='diagnostic_source_relation_048_v1':
            from .source_relation_048_risk import SourceRelation048Ledger
            return SourceRelation048Ledger(db,contract)
        if policy.enabled and policy.function_version=='diagnostic_comparison_answer_048_v1':
            from .comparison_answer_048_risk import ComparisonAnswer048Ledger
            return ComparisonAnswer048Ledger(db,contract)
        if policy.enabled and policy.function_version=='diagnostic_comparison_answer_048_v2':
            from .comparison_answer_048_v2_risk import ComparisonAnswer048V2Ledger
            return ComparisonAnswer048V2Ledger(db,contract)
        if policy.enabled and policy.function_version=='diagnostic_nonthinking_manifest_r1':
            from .nonthinking_risk import NonthinkingLedger
            return NonthinkingLedger(db,contract)
        if policy.enabled and policy.function_version=='diagnostic_remaining_manifest_r1':
            from .remaining_risk import RemainingLedger
            return RemainingLedger(db,contract)
        return super().__new__(cls)

    def __init__(self, db, contract):
        self.policy = parse_contract(contract)
        self.db_name=db.name
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

    def begin(self, run_id, run_identity, *, input_reservation=0,risk_context=None):
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
        if is_product_risk(self.policy):
            from .product_risk import start
            start(self.policy,db_name=self.db_name,run_id=run_id,run_identity=run_identity,context=risk_context)

    def settle(self, run_id, run_identity, usage, *, completed, reasoning=ABSENT, logical_calls=None,observations=None):
        receipt = usage_receipt(usage, reasoning=reasoning,observations=observations) | dict(run_id=run_id, run_identity=run_identity, completed=bool(completed))
        keys=('invoke_started','stream_started')
        receipt['logical_provider_calls']={k:logical_calls[k] for k in keys} if isinstance(logical_calls,dict) and all(
            type(logical_calls.get(k)) is int and logical_calls[k]>=0 for k in keys) else None
        saved = self._read();key = fingerprint(run_id)
        if key in saved['settled']:
            if saved['settled'][key] != receipt:raise APIError(409, 'output_settlement_conflict', '相同调用的结算内容改变。')
            if is_product_risk(self.policy):
                from .product_risk import settle
                settle(self.policy,receipt)
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
        if is_product_risk(self.policy):
            from .product_risk import settle
            settle(self.policy,receipt)
        return self._read()

    def require_open(self):
        saved = self._read()
        if saved['state'] != 'open' or saved['unknown_windows']:
            raise APIError(409, 'output_account_blocked', '诊断usage缺失、未完成或总输出越界，后续调用保持暂停。')
        return saved
