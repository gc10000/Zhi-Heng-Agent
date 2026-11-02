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
from . import source_relation_048_risk as consumed_profile
from .product_risk import exclusive, code_version

ROOT = Path(__file__).resolve().parents[3]
VERSION = 'diagnostic_comparison_answer_048_v1'
BATCH = 'm6-comparison-answer-048-risk-r7'
SLOT = 'm6-comparison-answer-048-r7-support-v1-048'
QUESTION_ID = 'support-v1-048'
ACCOUNT_COLLECTION = 'diagnostic_comparison_answer_048_accounts'
SUPERSEDED_BATCH = 'm6-comparison-answer-048-risk-r6'
SUPERSEDED_SLOT = 'm6-comparison-answer-048-r6-support-v1-048'

# 只绑定本包单次授权；授权文件位于受审提交中，不复用旧048消费槽。
AUTHORIZED_GIT = dict(
    commit='1381cb0448be5e9f84060f8d1256c37084a10622',
    path='docs/development/reviews/M6-comparison-answer-048-authorization-r7.json',
    sha256='7567092c6a11d533f04e3edbbbfbd20ede1bf5f0eb64c39835f98aff910468a4',
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
            (prior.get('input_tokens'), prior.get('output_tokens')) != (53089, 30412) or
            not isinstance(prior.get('sources'), dict) or not prior['sources']):
        raise ValueError('比较答复历史前值缺少53089/30412计量来源')
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
            auth.get('single_experimental_change') != 'comparison_answer_v1_with_assertion_binding_disabled' or
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
            stopped.get('authorization_commit') != 'ced704033b6be6704c16485dc4637b71046f5179' or
            stopped.get('authorization_sha256') != 'd2871685f00753c9429ca0c8b1ec0bf85857d9e9bf30a48a7c2d0d8311437a51' or
            stopped.get('halt_must_remain_unchanged') is not True or
            stopped.get('retry_or_reuse_authorized') is not False):
        raise ValueError('048前次失败批次停止证明缺失或身份变化')
    halt_path = local(halt_relative)
    if sha(halt_path) != stopped.get('halt_sha256'):
        raise ValueError('048前次失败批次停止证明缺失或已变化')
    halt = read(halt_path)
    if (halt.get('kind') != 'm6_comparison_answer_048_prompt_order_stop' or
            halt.get('batch') != SUPERSEDED_BATCH or halt.get('slot') != SUPERSEDED_SLOT or
            halt.get('question_id') != QUESTION_ID or
            halt.get('failure_code') != 'comparison_prompt_product_order_drift' or
            halt.get('authorization_commit') != stopped.get('authorization_commit') or
            halt.get('authorization_sha256') != stopped.get('authorization_sha256') or
            halt.get('provider_requests') != 0 or halt.get('provider_streams') != 0 or
            halt.get('formal_experiment_created') is not True or halt.get('formal_result_rows') != 1 or
            halt.get('run_created') is not True or halt.get('risk_account_created') is not False or
            halt.get('retry_authorized') is not False):
        raise ValueError('048前次失败槽未保持资源初始化停止状态')
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
            attribution['comparison_answer'].get('function_version') != 'comparison_answer_v1' or
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
        prior_diagnostic_input_tokens=53089, prior_diagnostic_output_tokens=30412,
        max_total_diagnostic_input_tokens=81505, max_total_diagnostic_output_tokens=34508,
        max_new_product_jobs=1, max_new_product_streams=1, max_attempts_per_member=1)
    if any(budget.get(k) != v for k, v in expected_budget.items()):
        raise ValueError('比较答复单槽累计预算漂移')
    expected_contract = dict(enabled=True, status='unknown', semantics='unknown', evidence=None,
        n=1, model=runtime['model'], endpoint_sha256=runtime['endpoint_sha256'],
        client_versions=runtime['client_versions'], limit_field=runtime['limit_field'],
        thinking=False, reasoning_budget=None, per_request_total_output_tokens=4096,
        ledger_id='m6-comparison-answer-048-canary-r7', prior_input_tokens=prior['input_tokens'],
        prior_output_tokens=prior['output_tokens'], prior_source_sha256=prior['sha256'],
        max_total_input_tokens=81505, max_total_output_tokens=34508)
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
    """不接管旧账户；未来授权必须证明源账保持原值，不取消blocked状态。"""
    auth = sources(policy)[0]
    previous_batch = auth.get('previous_batch')
    previous_snapshot = auth.get('previous_account_snapshot_path')
    previous_settlement = auth.get('previous_settlement_source_path')
    if not all(isinstance(v, str) and v for v in (previous_batch, previous_snapshot, previous_settlement)):
        raise ValueError('新比较授权缺少旧消费账本的只读来源')
    if previous_batch != consumed_profile.BATCH:
        raise ValueError('新比较授权指向的旧批次不是已消费source-relation 048账本')
    old_dir = local('output/m6-authorized-products/' + previous_batch)
    snapshot_path, settlement_path = local(previous_snapshot), local(previous_settlement)
    saved = read(snapshot_path)
    settlement = read(settlement_path)
    expected_snapshot_sha = auth.get('previous_account_snapshot_sha256')
    expected_manifest_sha = auth.get('previous_manifest_sha256')
    if (saved.get('state') != 'blocked' or saved.get('pending') is not None or
            saved.get('unknown_windows') or sha(old_dir / 'halt.json') != auth.get('previous_halt_sha256') or
            not isinstance(expected_snapshot_sha, str) or sha(snapshot_path) != expected_snapshot_sha or
            not isinstance(expected_manifest_sha, str) or
            fingerprint(read(old_dir / 'planned.json')) != expected_manifest_sha or
            sha(settlement_path) != auth.get('previous_settlement_source_sha256') or
            settlement.get('account') != saved or
            saved.get('halt') != read(old_dir / 'halt.json') or
            len(saved.get('settled', {})) != 1 or consumed_profile.SLOT not in saved.get('settled', {})):
        raise ValueError('旧048消费账本不再处于封存blocked状态')
    planned = read(old_dir / 'planned.json')
    if (planned.get('version') != consumed_profile.VERSION or planned.get('batch_slot') != consumed_profile.BATCH or
            planned.get('dispatch_order') != [consumed_profile.SLOT]):
        raise ValueError('旧048固定成员计划来源身份漂移')
    actual = client[planned['shared_control_database']][consumed_profile.ACCOUNT_COLLECTION].find_one({'_id': saved['_id']})
    if actual != saved:
        raise ValueError('旧048消费账本现场变化，禁止新单次预算执行')


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


class ComparisonAnswer048Ledger(previous.NonthinkingLedger):
    """新身份专用账本类型；构造时即要求新档案的独立授权。"""

    def __init__(self, db, contract):
        base.RemainingLedger.__init__(self, db, contract, profile=sys.modules[__name__])
