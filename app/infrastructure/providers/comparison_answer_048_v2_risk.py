"""仅用于support-v1-048单次完整比较答复的专用风险档案。"""
import sys
import copy
import hashlib
import json
from pathlib import Path

from app.answering.reviewed_subjects import evidence_bytes
from app.knowledge.repository import fingerprint
from . import remaining_risk as base
from . import nonthinking_risk as previous
from . import comparison_answer_048_risk as consumed_profile
from .product_risk import exclusive, code_version

ROOT = Path(__file__).resolve().parents[3]
VERSION = 'diagnostic_comparison_answer_048_v2'
BATCH = 'm6-comparison-answer-048-risk-r8'
SLOT = 'm6-comparison-answer-048-r8-support-v1-048'
QUESTION_ID = 'support-v1-048'
ACCOUNT_COLLECTION = 'diagnostic_comparison_answer_048_v2_accounts'
SUPERSEDED_BATCH = 'm6-comparison-answer-048-risk-r7'
SUPERSEDED_SLOT = 'm6-comparison-answer-048-r7-support-v1-048'

# 只绑定本包单次授权；授权文件位于受审提交中，不复用旧048消费槽。
AUTHORIZED_GIT = dict(
    commit='fc656db374d13a55f6904bebd5936055f5861b1c',
    path='docs/development/reviews/M6-comparison-answer-048-authorization-r8.json',
    sha256='97136e5c0d722a4187b5eee0a7c04cb4002c9b211dae189fca92371ed16dc732',
)

read = base.read
sha = base.sha
now = base.now
config_subject = base.config_subject
entry_for = base.entry_for


def local(path):
    p = (ROOT / path).resolve()
    if not p.is_relative_to(ROOT.resolve()) or 'private-identity' in p.parts:
        raise ValueError('比较答复来源路径越界')
    return p


def batch_dir():
    return local('output/m6-authorized-products/' + BATCH)


def slot_dir(policy):
    return batch_dir() / 'members' / policy.admission.member_slot


def seal_stop(evidence):
    path = batch_dir() / 'halt.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if read(path) != evidence:
            raise ValueError('比较答复首停止证据不可改变')
    else:
        try:
            exclusive(path, evidence)
        except FileExistsError:
            if read(path) != evidence:
                raise ValueError('比较答复并发停止冲突')


def prior_receipt(auth=None):
    """读取新授权随附的历史计量证明；拒绝用预算数字本身冒充证明。"""
    if auth is None:
        if AUTHORIZED_GIT is None:
            raise ValueError('比较答复前值账本尚未绑定新的授权来源')
        auth = json.loads(evidence_bytes(AUTHORIZED_GIT))
    prior = auth.get('prior_usage')
    if (not isinstance(prior, dict) or
            (prior.get('input_tokens'), prior.get('output_tokens')) != (54664, 30449) or
            not isinstance(prior.get('sources'), dict) or not prior['sources']):
        raise ValueError('比较答复历史前值缺少54664/30449计量来源')
    for source in prior['sources'].values():
        if (not isinstance(source, dict) or not isinstance(source.get('path'), str) or
                not isinstance(source.get('sha256'), str) or sha(local(source['path'])) != source['sha256']):
            raise ValueError('比较答复历史计量来源文件或hash不匹配')
    value = dict(input_tokens=prior['input_tokens'], output_tokens=prior['output_tokens'],
        sources=copy.deepcopy(prior['sources']))
    digest = fingerprint(value)
    if prior.get('sha256') != digest:
        raise ValueError('比较答复历史计量证明hash不匹配')
    return value | dict(sha256=digest)


def sources(policy):
    """只接受r3单题授权、冻结题集和完整提示来源。"""
    if AUTHORIZED_GIT is None:
        raise ValueError('比较答复专用Git授权尚未登记，禁止真实执行')
    ref = policy.admission.authorization.model_dump(mode='json')
    if ref != AUTHORIZED_GIT:
        raise ValueError('比较答复必须使用本包固定Git授权')
    auth = json.loads(evidence_bytes(AUTHORIZED_GIT))
    if (auth.get('kind') != 'coordinator_scoped_comparison_answer_048_authorization' or
            auth.get('admission_version') != VERSION or auth.get('fixed_batch_slot') != BATCH or
            auth.get('single_experimental_change') != 'comparison_answer_v2_with_assertion_binding_disabled' or
            auth.get('risk', {}).get('gateway_capability_status') != 'unknown' or
            auth.get('user_authorization', {}).get('max_provider_streams') != 1 or
            auth.get('user_authorization', {}).get('stop_on_first_failure') is not True or
            auth.get('authorization_continuation', {}).get('provider_streams_started_before_continuation') != 0 or
            auth.get('authorization_continuation', {}).get('max_provider_streams_for_this_validation') != 1 or
            auth.get('authorization_continuation', {}).get('reuse_or_retry_superseded_slots') is not False or
            auth.get('risk', {}).get('coordinator_accepts_unknown_paid_upper_bound_only_for_this_one_stream') is not True):
        raise ValueError('比较答复专用授权内容不适用')
    stopped = auth.get('supersedes_failed_attempt', {})
    halt_relative = stopped.get('halt_path') if isinstance(stopped, dict) else None
    if (not isinstance(halt_relative, str) or not halt_relative or
            stopped.get('batch') != SUPERSEDED_BATCH or
            stopped.get('slot') != SUPERSEDED_SLOT or
            stopped.get('authorization_commit') != '1381cb0448be5e9f84060f8d1256c37084a10622' or
            stopped.get('authorization_sha256') != '7567092c6a11d533f04e3edbbbfbd20ede1bf5f0eb64c39835f98aff910468a4' or
            stopped.get('halt_must_remain_unchanged') is not True or
            stopped.get('retry_or_reuse_authorized') is not False):
        raise ValueError('048前次失败批次停止证明缺失或身份变化')
    halt_path = local(halt_relative)
    if sha(halt_path) != stopped.get('halt_sha256'):
        raise ValueError('048前次失败批次停止证明缺失或已变化')
    halt = read(halt_path)
    if (halt.get('no_more_provider_calls') is not True or
            halt.get('source_review', {}).get('accepted') is not False or
            halt.get('source_review', {}).get('run_id') != stopped.get('run_id')):
        raise ValueError('048前次r7质量拒绝停止证据缺失或不一致')
    members = auth.get('members')
    if (not isinstance(members, list) or len(members) != 1 or
            auth.get('dispatch_order') != [SLOT] or policy.admission.member_slot != SLOT):
        raise ValueError('比较答复只允许support-v1-048一个固定成员')
    member = members[0]
    if (member.get('version'), member.get('ordinal'), member.get('question_id'),
            member.get('fixed_slot'), member.get('expected_generation')) != (1, 27, QUESTION_ID, SLOT, True):
        raise ValueError('比较答复成员身份不是版1 support-v1-048')
    if (sha(local(auth['original_master_path'])) != auth['original_master_file_sha256'] or
            sha(local(auth['original_execution_manifest_path'])) != auth['original_execution_manifest_sha256'] or
            sha(local(member['source_input_path'])) != member['source_input_file_sha256']):
        raise ValueError('比较答复题集、执行清单或冻结输入来源漂移')
    anchor = read(local(member['source_input_path']))
    if (fingerprint(anchor['result']) != member['source_result_sha256'] or
            fingerprint(anchor['new_config']) != member['source_config_sha256'] or
            hashlib.sha256(anchor['result']['prompt'].encode()).hexdigest() != member['prompt_utf8_sha256']):
        raise ValueError('比较答复冻结完整输入或配置漂移')
    attribution = anchor['new_config']['parameters']['evidence_attribution']
    if (attribution.get('enabled') is not True or
            not attribution.get('source_relations', {}).get('enabled') or
            attribution.get('comparison_answer', {}).get('enabled') is not True or
            attribution['comparison_answer'].get('function_version') != 'comparison_answer_v2' or
            attribution.get('assertion_binding', {}).get('enabled', False)):
        raise ValueError('比较答复授权配置必须开启比较并关闭原句摘录协议')
    master = read(local(auth['original_master_path']))
    parent = next((p for p in master['version_sources'] if p['version'] == member['version']), None)
    if parent is None:
        raise ValueError('比较答复来源缺少冻结题集版本')
    prior = prior_receipt(auth)
    runtime, budget = auth.get('runtime', {}), auth.get('budget', {})
    expected_runtime = dict(n=1, model=policy.model, endpoint_sha256=policy.endpoint_sha256,
        client_versions={'openai': '2.28.0', 'langchain-openai': '1.1.11'},
        limit_field='max_completion_tokens', requested_total_output_tokens=4096,
        thinking=False, temperature=0.1, timeout_seconds=120, sdk_max_retries=0, stream=True)
    if runtime != expected_runtime:
        raise ValueError('比较答复模型、端点、SDK或请求参数漂移')
    expected_budget = dict(context_window=32768, output_tokens_requested=4096,
        reserve_tokens=256, max_chars=12000, single_input_limit=28416,
        prior_diagnostic_input_tokens=54664, prior_diagnostic_output_tokens=30449,
        max_total_diagnostic_input_tokens=83080, max_total_diagnostic_output_tokens=34545,
        max_new_product_jobs=1, max_new_product_streams=1, max_attempts_per_member=1)
    if any(budget.get(k) != v for k, v in expected_budget.items()):
        raise ValueError('比较答复单槽累计预算漂移')
    expected_contract = dict(enabled=True, status='unknown', semantics='unknown', evidence=None,
        n=1, model=runtime['model'], endpoint_sha256=runtime['endpoint_sha256'],
        client_versions=runtime['client_versions'], limit_field=runtime['limit_field'],
        thinking=False, reasoning_budget=None, per_request_total_output_tokens=4096,
        ledger_id='m6-comparison-answer-048-canary-r8', prior_input_tokens=prior['input_tokens'],
        prior_output_tokens=prior['output_tokens'], prior_source_sha256=prior['sha256'],
        max_total_input_tokens=83080, max_total_output_tokens=34545)
    if any(getattr(policy, key) != value for key, value in expected_contract.items()):
        raise ValueError('比较答复合同与新授权、历史计量或单次预算不一致')
    return auth, member, anchor, parent


def authorized_inputs(auth, member):
    return base.authorized_inputs(auth, member, profile=sys.modules[__name__])


def execution_control_database(auth, parent):
    database = auth.get('evaluation_control_database')
    if not isinstance(database, str) or not database:
        raise ValueError('比较答复授权缺少正式评测控制库')
    return database


def build_member(config, question, control_database):
    from .output_contract import parse_contract
    anchor = sources(parse_contract(config['parameters']['answer_budget']['output_contract']))[2]
    actual, expected = copy.deepcopy(config), copy.deepcopy(anchor['new_config'])
    for value in (actual, expected):
        value.pop('experiment_id', None)
        value['versions'].pop('code', None)
        value.pop('question_ids', None)
        value['parameters']['answer_budget'].pop('output_contract', None)
        value['parameters']['answer_budget'].pop('output_token_field', None)
    if actual != expected:
        raise ValueError('比较答复成员仅允许授权的输出策略变化')
    member = sources(parse_contract(config['parameters']['answer_budget']['output_contract']))[1]
    if (config.get('question_ids') != [QUESTION_ID] or question.get('id') != QUESTION_ID or
            config.get('experiment_id') != SLOT or config['versions'].get('code') != code_version() or
            config.get('dataset_sha256') != member.get('dataset_sha256') or
            config.get('split_manifest_sha256') != member.get('split_manifest_sha256')):
        raise ValueError('比较答复题目、实验、源码或冻结题集身份漂移')
    return base.build_member(config, question, control_database, profile=sys.modules[__name__])


def build_manifest(items, *, artifacts=None):
    if len(items) != 1:
        raise ValueError('比较答复风险清单只允许一个成员')
    entry = build_member(*items[0])
    from .output_contract import parse_contract
    policy = parse_contract(items[0][0]['parameters']['answer_budget']['output_contract'])
    auth = sources(policy)[0]
    if entry['member']['fixed_slot'] != SLOT or auth['dispatch_order'] != [SLOT]:
        raise ValueError('比较答复风险清单成员顺序漂移')
    return dict(version=VERSION, batch_slot=BATCH, authorization=AUTHORIZED_GIT,
        prior_receipt=prior_receipt(auth), shared_control_database=entry['control_database'],
        dispatch_order=[SLOT], entries=[entry], artifacts=artifacts or {})


def require(policy):
    sources(policy)
    return base.require(policy, profile=sys.modules[__name__])


def validate_previous_account(policy, client):
    """旧r7只读复核：状态、结算和halt均须保持已拒绝且不可重试。"""
    auth = sources(policy)[0]
    if auth.get('previous_batch') != consumed_profile.BATCH:
        raise ValueError('新比较授权未指向已消费r7比较账本')
    old_dir = local('output/m6-authorized-products/' + consumed_profile.BATCH)
    planned = read(old_dir / 'planned.json')
    if (planned.get('version') != consumed_profile.VERSION or planned.get('batch_slot') != consumed_profile.BATCH or
            planned.get('dispatch_order') != [consumed_profile.SLOT]):
        raise ValueError('旧r7固定成员计划来源身份漂移')
    halt = read(old_dir / 'halt.json')
    settled_path = old_dir / 'members' / consumed_profile.SLOT / 'settled.json'
    settled = read(settled_path)
    saved = client[planned['shared_control_database']][consumed_profile.ACCOUNT_COLLECTION].find_one(
        {'_id': fingerprint([consumed_profile.VERSION, consumed_profile.BATCH])})
    slot = (saved or {}).get('settled', {}).get(consumed_profile.SLOT)
    if (not saved or saved.get('state') != 'blocked' or saved.get('pending') is not None or
            saved.get('unknown_windows') or len(saved.get('settled', {})) != 1 or
            slot is None or saved.get('halt') != halt or settled.get('receipt') != slot or
            halt.get('no_more_provider_calls') is not True or
            halt.get('source_review', {}).get('accepted') is not False or
            halt.get('source_review', {}).get('run_id') != slot.get('run_id')):
        raise ValueError('旧r7账户未保持单次结算后的质量拒绝停止状态')


def prepare_manifest(manifest):
    if AUTHORIZED_GIT is None or manifest.get('authorization') != AUTHORIZED_GIT:
        raise ValueError('比较答复专用Git授权尚未登记，不能冻结或派发清单')
    return base.prepare_manifest(manifest, profile=sys.modules[__name__])


def validate_config(config, control_database, *, question=None):
    return base.validate_config(config, control_database, question=question, profile=sys.modules[__name__])


def validate_prompt(policy, prompt, state):
    return base.validate_prompt(policy, prompt, state, profile=sys.modules[__name__])


def validate_client(policy, client):
    return base.validate_client(policy, client, profile=sys.modules[__name__])


def validate_runtime(policy, run, context, db):
    base.validate_runtime(policy, run, context, db, profile=sys.modules[__name__])
    validate_previous_account(policy, db.client)


def open_client(policy):
    # 先确认新授权，避免尚未批准的配置读取模型凭据或构造网络客户端。
    sources(policy)
    return previous.open_client(policy)


class ComparisonAnswer048V2Ledger(previous.NonthinkingLedger):
    """新身份专用账本类型；构造时即要求新档案的独立授权。"""

    def __init__(self, db, contract):
        base.RemainingLedger.__init__(self, db, contract, profile=sys.modules[__name__])

