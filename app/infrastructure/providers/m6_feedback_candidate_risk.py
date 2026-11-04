"""两版完整反馈候选的独立170成员准入与共享调用账本。"""
from collections import Counter
import copy
import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from functools import lru_cache

from pymongo.errors import DuplicateKeyError

from app.api.errors import APIError
from app.answering.reviewed_subjects import evidence_bytes
from app.knowledge.repository import fingerprint
from .product_risk import SingleProductAdmission, exclusive


VERSION = 'diagnostic_feedback_candidate_manifest_r1'
BATCH = 'm6-feedback-candidate-full-r1'
ACCOUNT_COLLECTION = 'diagnostic_feedback_candidate_accounts'
CANDIDATE_SLOTS = {
    'm6-feedback-stage-r1-v1': 1,
    'm6-feedback-stage-r1-v2': 2,
}
MEMBERS_PER_CANDIDATE = 85
EXPECTED_MEMBERS = 170
EXPECTED_GENERATED_MEMBERS = 168
EXPECTED_CLARIFICATIONS = 2
CLARIFICATION_QUESTION = 'support-v1-047'
COMPARISON_QUESTION = 'support-v1-048'
SERIES_QUESTION = 'm6-g540-20-a'
ROOT = Path(__file__).resolve().parents[3]
AUTHORIZATION_PATH = 'docs/development/reviews/M6-feedback-stage-authorization-r1.json'
AUTHORIZATION_REFERENCE_PATH = 'docs/development/reviews/M6-feedback-stage-authorization-reference-r1.json'
DEFAULT_AUTHORIZATION = None


class CandidateBatchStop(ValueError):
    """有限候选失败后由正式runner持久化当前错误并停止整个批次。"""
    stop_batch = True


def local(relative):
    if not isinstance(relative, str) or Path(relative).is_absolute() or '\\' in relative:
        raise ValueError('反馈候选来源必须使用仓库内相对路径')
    path = (ROOT / relative).resolve()
    if not path.is_relative_to(ROOT.resolve()) or any(part in {'private-identity', '.env'} for part in path.parts):
        raise ValueError('反馈候选来源路径越界')
    return path


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def load_authorization_reference(root=ROOT):
    from app.answering.reviewed_subjects import GitEvidence
    path = root / AUTHORIZATION_REFERENCE_PATH
    if not path.exists():
        return None
    payload = path.read_bytes()
    ref = GitEvidence.model_validate_json(payload).model_dump(mode='json')
    if ref['path'] != AUTHORIZATION_PATH:
        raise ValueError('完整反馈候选只能绑定本批次专属授权')
    saved = subprocess.run(['git', 'show', 'HEAD:' + AUTHORIZATION_REFERENCE_PATH], cwd=root,
        capture_output=True, timeout=10)
    if saved.returncode or saved.stdout != payload:
        raise ValueError('完整反馈候选授权引用尚未提交或发生漂移')
    return ref


AUTHORIZED_GIT = load_authorization_reference()


def batch_dir():
    return local('output/m6-authorized-products/' + BATCH)


def member_slot(candidate_slot, question_id):
    if candidate_slot not in CANDIDATE_SLOTS or not isinstance(question_id, str):
        raise ValueError('候选版本或题目身份不属于固定反馈范围')
    return f"m6-feedback-stage-r1-v{CANDIDATE_SLOTS[candidate_slot]}-{question_id}"


def validate_full_dispatch(manifest):
    """校验完整范围与执行顺序；总量、澄清和路由都由冻结包固定。"""
    if not isinstance(manifest, dict):
        raise ValueError('反馈候选清单类型无效')
    entries = manifest.get('entries')
    order = manifest.get('dispatch_order')
    if not isinstance(entries, list) or len(entries) != EXPECTED_MEMBERS:
        raise ValueError('反馈候选必须包含完整170成员')
    if not isinstance(order, list) or len(order) != EXPECTED_MEMBERS or len(set(order)) != EXPECTED_MEMBERS:
        raise ValueError('反馈候选必须有170个唯一且有序的固定槽')
    if (manifest.get('expected_members') != EXPECTED_MEMBERS or
            manifest.get('expected_generated_members') != EXPECTED_GENERATED_MEMBERS or
            manifest.get('expected_clarifications') != EXPECTED_CLARIFICATIONS):
        raise ValueError('反馈候选总成员或provider stream预算漂移')

    seen = set()
    versions = Counter()
    routes_by_version = {1: Counter(), 2: Counter()}
    generations = 0
    clarifications = 0
    for position, entry in enumerate(entries):
        member = entry.get('member') if isinstance(entry, dict) else None
        if not isinstance(member, dict):
            raise ValueError('反馈候选成员缺少固定身份')
        candidate_slot = member.get('candidate_slot')
        version = CANDIDATE_SLOTS.get(candidate_slot)
        question_id = member.get('question_id')
        ordinal = member.get('ordinal')
        slot = member_slot(candidate_slot, question_id)
        generated = question_id != CLARIFICATION_QUESTION
        expected_route = ('clarify' if question_id == CLARIFICATION_QUESTION else
                          'compare' if question_id == COMPARISON_QUESTION else
                          'series' if question_id == SERIES_QUESTION else 'answer')
        if (version is None or member.get('version') != version or member.get('split') != 'dev' or
                type(ordinal) is not int or ordinal < 1 or ordinal > MEMBERS_PER_CANDIDATE or
                member.get('fixed_slot') != slot or order[position] != slot or slot in seen or
                type(member.get('expected_generation')) is not bool or member['expected_generation'] != generated or
                member.get('max_provider_streams') != int(generated)):
            raise ValueError('反馈候选成员越界、重排、重复或生成预算不符')
        if member.get('route') != expected_route:
            raise ValueError('反馈候选固定题目路由身份漂移')
        if position // MEMBERS_PER_CANDIDATE != version - 1 or ordinal != position % MEMBERS_PER_CANDIDATE + 1:
            raise ValueError('两版候选必须按冻结顺序连续派发')
        seen.add(slot)
        versions[version] += 1
        routes_by_version[version][member['route']] += 1
        generations += int(generated)
        clarifications += int(not generated)

    if versions != {1: MEMBERS_PER_CANDIDATE, 2: MEMBERS_PER_CANDIDATE}:
        raise ValueError('每版候选必须恰好85道dev题')
    if generations != EXPECTED_GENERATED_MEMBERS or clarifications != EXPECTED_CLARIFICATIONS:
        raise ValueError('反馈候选须保持168个生成和2个零调用澄清')
    if any(routes_by_version[version] != Counter(answer=82, series=1, compare=1, clarify=1)
            for version in CANDIDATE_SLOTS.values()):
        raise ValueError('两版反馈候选题目路由分布漂移')
    return manifest


def validate_contract_profile(policy, auth):
    runtime = auth.get('runtime') or {}
    expected = dict(status='unknown', semantics='unknown', evidence=None, n=1,
        model='qwen3.8-flash', endpoint_sha256=runtime.get('endpoint_sha256'),
        client_versions={'openai': '2.28.0', 'langchain-openai': '1.1.11'},
        limit_field='max_completion_tokens', thinking=False, reasoning_budget=None,
        per_request_total_output_tokens=4096, ledger_id=BATCH, prior_input_tokens=0,
        prior_output_tokens=0, prior_source_sha256=None,
        max_total_input_tokens=4773888, max_total_output_tokens=688128)
    if (any(getattr(policy, key, None) != value for key, value in expected.items()) or
            not isinstance(expected['endpoint_sha256'], str) or len(expected['endpoint_sha256']) != 64 or
            any(ch not in '0123456789abcdef' for ch in expected['endpoint_sha256'])):
        raise ValueError('反馈候选合同与供应商、SDK、思考或预算profile不一致')
    budget = auth.get('budget') or {}
    expected_budget = dict(context_window=32768, output_tokens_requested=4096, reserve_tokens=256,
        max_chars=12000, single_input_limit=28416, max_new_product_streams=168,
        max_members=170, max_attempts_per_member=1)
    if budget != expected_budget:
        raise ValueError('反馈候选授权预算维度或最大尝试数漂移')
    if (runtime.get('n') != 1 or runtime.get('model') != expected['model'] or
            runtime.get('client_versions') != expected['client_versions'] or
            runtime.get('limit_field') != expected['limit_field'] or
            runtime.get('requested_total_output_tokens') != expected['per_request_total_output_tokens'] or
            runtime.get('thinking') is not False or runtime.get('temperature') != 0.1 or
            runtime.get('timeout_seconds') != 120 or runtime.get('sdk_max_retries') != 0 or
            runtime.get('stream') is not True):
        raise ValueError('反馈候选授权runtime profile漂移')
    return True


def entry_for_execution(manifest, candidate_slot, question_id, *, version=None):
    validate_full_dispatch(manifest)
    candidate_version = CANDIDATE_SLOTS.get(candidate_slot)
    if candidate_version is None or (version is not None and version != candidate_version):
        raise ValueError('正式Run不能借用另一候选版本的准入')
    slot = member_slot(candidate_slot, question_id)
    matches = [entry for entry in manifest['entries'] if entry['member']['fixed_slot'] == slot]
    if len(matches) != 1 or matches[0]['member']['version'] != candidate_version:
        raise ValueError('正式Run题目不属于候选版本的固定成员')
    return matches[0]


def sources(policy):
    if AUTHORIZED_GIT is None or policy.admission is None:
        raise ValueError('完整反馈候选尚无新范围Git授权')
    if policy.admission.authorization.model_dump(mode='json') != AUTHORIZED_GIT:
        raise ValueError('完整反馈候选不能借用其他调用授权')
    auth = json.loads(evidence_bytes(AUTHORIZED_GIT))
    if (auth.get('kind') != 'coordinator_scoped_m6_feedback_candidates_authorization' or
            auth.get('status') != 'authorized_for_two_complete_dev_candidates' or
            auth.get('admission_version') != VERSION or auth.get('fixed_batch_slot') != BATCH or
            auth.get('candidate_slots') != list(CANDIDATE_SLOTS) or
            auth.get('max_provider_streams') != EXPECTED_GENERATED_MEMBERS or
            auth.get('new_input_budget') != 4773888 or auth.get('new_output_budget') != 688128 or
            auth.get('stop_on_first_failure') is not True or
            auth.get('sdk_max_retries') != 0 or auth.get('heldout_selected') != 0 or
            auth.get('old_43_question_batch_started') is not False or auth.get('m7_started') is not False):
        raise ValueError('完整反馈候选授权范围、停止规则或预算漂移')
    validate_contract_profile(policy, auth)
    validate_technical_review(auth)
    ref = auth.get('production_manifest')
    if not isinstance(ref, dict):
        raise ValueError('缺少完整生产输入清单引用')
    path = local(ref.get('path'))
    if sha(path) != ref.get('sha256'):
        raise ValueError('完整生产输入清单hash不匹配')
    manifest = loaded_manifest(str(path), ref['sha256'])
    if fingerprint(manifest) != auth.get('production_manifest_sha256'):
        raise ValueError('完整生产输入清单身份不匹配')
    validate_full_dispatch(manifest)
    if (manifest.get('authorization_path') != AUTHORIZATION_PATH or
            manifest.get('batch_slot') != BATCH or
            manifest.get('expected_members') != EXPECTED_MEMBERS or
            manifest.get('expected_generated_members') != EXPECTED_GENERATED_MEMBERS):
        raise ValueError('生产输入清单与完整反馈授权不一致')
    if (policy.max_total_input_tokens != auth['new_input_budget'] or
            policy.max_total_output_tokens != auth['new_output_budget']):
        raise ValueError('反馈候选合同预算超出已授权上限')
    return auth, manifest


def validate_technical_review(auth):
    """消费本包不同实现身份的已提交结论，拒绝借用旧包或源码漂移。"""
    from .product_risk import code_version
    ref = auth.get('independent_technical_review')
    if not isinstance(ref, dict):
        raise ValueError('完整反馈候选缺少独立技术复核来源')
    review = json.loads(evidence_bytes(ref))
    if (review.get('kind') != 'm6_feedback_candidate_independent_technical_review' or
            review.get('final_technical_review') != 'passed_with_specific_boundaries' or
            review.get('implementation_participation') is not False or
            review.get('open_findings') != [] or
            review.get('source_code_sha256') != code_version()):
        raise ValueError('完整反馈候选独立技术结论未关闭或不覆盖当前源码')
    return review


@lru_cache(maxsize=4)
def loaded_manifest(path, digest):
    """固定授权进程只消费已重算的内存快照；调用方仍核文件原字节hash。"""
    if sha(path) != digest:
        raise ValueError('生产输入清单hash漂移')
    value = read(path)
    from app.evaluation.m6_feedback_inputs import validate_production_manifest
    return validate_production_manifest(value)


def prepare_manifest(manifest):
    from app.infrastructure.providers.output_contract import FEEDBACK_CANDIDATE_VERSION
    if AUTHORIZED_GIT is None or manifest.get('authorization_path') != AUTHORIZATION_PATH:
        raise ValueError('缺少已提交的完整反馈候选授权')
    auth = json.loads(evidence_bytes(AUTHORIZED_GIT))
    ref = auth.get('production_manifest')
    if not isinstance(ref, dict):
        raise ValueError('授权缺少完整生产清单身份')
    approved_path = local(ref.get('path'))
    approved = read(approved_path)
    if (sha(approved_path) != ref.get('sha256') or
            fingerprint(approved) != auth.get('production_manifest_sha256') or
            manifest != approved):
        raise ValueError('派发清单与批准的完整生产输入不一致')
    validate_full_dispatch(manifest)
    if manifest.get('batch_slot') != BATCH or manifest.get('version') != FEEDBACK_CANDIDATE_VERSION:
        raise ValueError('反馈候选清单版本或批次不匹配')
    path = batch_dir() / 'planned.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if read(path) != manifest:
            raise ValueError('完整反馈候选计划不可覆盖或换目录重领')
    else:
        try:
            exclusive(path, manifest)
        except FileExistsError:
            if read(path) != manifest:
                raise ValueError('并发创建的完整反馈候选计划不一致')
    digest = fingerprint(manifest)
    for entry in manifest['entries']:
        directory = batch_dir() / 'members' / entry['member']['fixed_slot']
        directory.mkdir(parents=True, exist_ok=True)
        member_plan = directory / 'planned.json'
        value = dict(manifest_sha256=digest, entry=entry)
        if member_plan.exists():
            if read(member_plan) != value:
                raise ValueError('反馈候选成员计划不可覆盖')
        else:
            try:
                exclusive(member_plan, value)
            except FileExistsError:
                if read(member_plan) != value:
                    raise ValueError('并发成员计划身份冲突')
    return manifest


def require(policy):
    auth, authorized_manifest = sources(policy)
    path = batch_dir() / 'planned.json'
    if not path.exists():
        raise ValueError('缺少完整170成员正式派发清单')
    manifest = read(path)
    if (manifest != authorized_manifest or fingerprint(manifest) != policy.admission.manifest_sha256 or
            manifest.get('authorization_path') != AUTHORIZATION_PATH):
        raise ValueError('正式派发清单与批准的完整输入身份不一致')
    return manifest


def current_entry(policy, question_id, *, manifest=None):
    selected = manifest or require(policy)
    return entry_for_execution(selected, policy.admission.member_slot, question_id)


def expected_generation(policy, question):
    return current_entry(policy, question['id'])['member']['expected_generation']


def candidate(config, slot):
    candidates = config.get('candidate_versions')
    if not isinstance(candidates, list):
        raise ValueError('完整反馈候选缺少两个冻结配置版本')
    matches = [row for row in candidates if row.get('candidate_slot') == slot]
    if len(matches) != 1:
        raise ValueError('反馈候选配置不属于唯一授权版本')
    return matches[0]


def validate_question_scope(config, version_config):
    expected = version_config.get('question_ids')
    if (not isinstance(expected, list) or len(expected) != MEMBERS_PER_CANDIDATE or
            len(set(expected)) != MEMBERS_PER_CANDIDATE):
        raise ValueError('反馈候选清单必须绑定完整85题dev身份')
    selected = config.get('question_ids')
    if selected is not None and selected != expected:
        raise ValueError('反馈候选不能缩小或重排已授权dev范围')
    return expected


def validate_request(config, data):
    from .output_contract import parse_contract
    policy = parse_contract(config['parameters']['answer_budget']['output_contract'])
    approved = candidate(require(policy), policy.admission.member_slot)['request']
    if data != approved:
        raise ValueError('完整候选正式请求、反馈来源、校准或幂等身份漂移')


def config_subject(config):
    value = copy.deepcopy(config)
    for key in ('quality_execution_key', 'regression_execution_key', 'regression_source'):
        value.pop(key, None)
    contract = value.get('parameters', {}).get('answer_budget', {}).get('output_contract')
    if not isinstance(contract, dict):
        raise ValueError('反馈候选缺少专属输出合同')
    contract.update(enabled=False, admission=None)
    return value


def validate_config(config, control_database, *, question=None):
    from .output_contract import parse_contract
    policy = parse_contract(config['parameters']['answer_budget']['output_contract'])
    manifest = require(policy)
    version_config = candidate(manifest, policy.admission.member_slot)
    if (config_subject(config) != version_config.get('config_subject') or
            control_database != version_config.get('control_database') or
            config.get('experiment_id') != version_config.get('experiment_id') or
            config.get('dataset_sha256') != version_config.get('dataset_sha256') or
            config.get('split_manifest_sha256') != version_config.get('split_manifest_sha256') or
            config.get('versions') != version_config.get('versions')):
        raise ValueError('反馈候选配置、控制库、题集或源码身份漂移')
    ids = validate_question_scope(config, version_config)
    if question is not None:
        entry = current_entry(policy, question['id'], manifest=manifest)
        expected = entry['question']
        if ({k: question[k] for k in ('id', 'question', 'product_names', 'history')} != expected or
                question.get('split') != 'dev' or question['id'] not in ids):
            raise ValueError('正式Run问题不匹配其固定dev输入')
    return manifest


def validate_prompt(policy, prompt, state):
    question_id = state.get('evaluation_question_id')
    if not isinstance(question_id, str):
        raise ValueError('反馈候选实际prompt缺少持久题号身份')
    entry = current_entry(policy, question_id)
    member = entry['member']
    if not member['expected_generation']:
        raise ValueError('零调用澄清成员不能进入生成器')
    expected = entry['production_input']['result']
    if (prompt != expected['prompt'] or state.get('prompt_used_docs') != expected['context'] or
            state.get('prompt_reference_map', []) != expected['prompt_reference_map'] or
            state.get('evidence_groups', []) != expected['groups'] or
            {k: v for k, v in state['prompt_budget'].items() if k != 'policy'} !=
                {k: v for k, v in expected['budget'].items() if k != 'policy'} or
            state['prompt_budget'].get('input_limit') != 28416 or
            state.get('comparison_context_assembly') != expected.get('comparison_context_assembly')):
        raise ValueError('反馈候选实际输入与逐题完整生产输入冻结身份不一致')


def input_identity(policy, run, entry):
    result = copy.deepcopy(entry['production_input']['result'])
    result['budget'].pop('policy', None)
    return dict(function_version=VERSION, run_id=run['run_id'], run_identity=run['identity'],
        member_slot=entry['member']['fixed_slot'], manifest_sha256=policy.admission.manifest_sha256,
        input_sha256=fingerprint(result), contract_sha256=fingerprint(policy.model_dump(mode='json')))


def validate_persisted_input(policy, db, run, question_id):
    entry = current_entry(policy, question_id)
    if not entry['member']['expected_generation']:
        raise ValueError('澄清成员不能有模型输入持久记录')
    expected = input_identity(policy, run, entry)
    actual = db.feedback_candidate_generation_inputs.find_one({'_id': run['run_id']})
    if actual != dict(expected, _id=run['run_id']):
        raise ValueError('完整候选独立调用前输入记录缺失或漂移')
    return expected


def persist_input(policy, db, run, prompt, state):
    validate_prompt(policy, prompt, state)
    entry = current_entry(policy, state['evaluation_question_id'])
    expected = input_identity(policy, run, entry)
    try:
        db.feedback_candidate_generation_inputs.update_one({'_id': run['run_id']},
            {'$setOnInsert': expected}, upsert=True)
    except DuplicateKeyError:
        pass
    return validate_persisted_input(policy, db, run, state['evaluation_question_id'])


def validate_runtime(policy, run, context, db):
    if not context:
        raise ValueError('反馈候选准入只能沿正式评测job消费')
    validate_config(context['config'], context['control_database'], question=context['question'])
    entry = current_entry(policy, context['question']['id'])
    if entry['member']['candidate_slot'] != policy.admission.member_slot:
        raise ValueError('反馈候选Run版本与题级清单不匹配')
    from app.evaluation.execution_links import validate_execution
    from app.evaluation.execution_identity import run_input
    validate_execution(context['control_db'], context['execution'], context['config'])
    link = db.evaluation_execution_links.find_one(dict(
        experiment_id=context['execution']['experiment_id'],
        attempt=context['execution']['attempt'], run_id=run['run_id'], mode='execution'))
    if (not link or link.get('control_database') != context['control_database'] or
            link.get('target_database') != db.name or
            link.get('question_id') != context['question']['id'] or
            link.get('output_contract') != policy.model_dump(mode='json') or
            link.get('run_input_sha256') != fingerprint(run_input(run, db))):
        raise ValueError('反馈候选正式Run执行链接缺失或身份漂移')
    validate_previous_accounts(policy, db.client)


def validate_previous_accounts(policy, client):
    auth, _ = sources(policy)
    refs = auth.get('previous_accounts')
    if not isinstance(refs, list) or len(refs) != 2:
        raise ValueError('完整反馈候选必须保护旧r8与048r2两个停止账户')
    for ref in refs:
        path = local(ref['snapshot']['path'])
        if sha(path) != ref['snapshot']['sha256']:
            raise ValueError('旧停止账户保存证据漂移')
        saved = read(path)
        actual = client[ref['database']][ref['collection']].find_one({'_id': saved['_id']})
        if (actual != saved or saved.get('state') != 'blocked' or saved.get('pending') is not None or
                saved.get('unknown_windows') or not saved.get('settled') or not saved.get('halt')):
            raise ValueError('旧停止账户状态或已消费结算发生变化，不放行新调用')


def validate_client(policy, client):
    from . import remaining_risk
    return remaining_risk.validate_client(policy, client, profile=sys.modules[__name__])


def open_client(policy):
    sources(policy)
    from .nonthinking_risk import open_client as open_nonthinking_client
    return open_nonthinking_client(policy)


def slot_dir(slot):
    return batch_dir() / 'members' / slot


def seal_stop(evidence):
    if not isinstance(evidence, dict) or not evidence:
        raise ValueError('反馈候选停止必须保留具体验证证据')
    path = batch_dir() / 'halt.json'
    if path.exists():
        if read(path) != evidence:
            raise ValueError('完整反馈批次的首次停止证据不可改变')
    else:
        try:
            exclusive(path, evidence)
        except FileExistsError:
            if read(path) != evidence:
                raise ValueError('并发反馈候选停止证据冲突')


class FeedbackCandidateLedger:
    """两版共享单一CAS账本；每次成功结算推进一个题级槽，失败后永久阻断。"""
    def __init__(self, db, contract):
        from .output_contract import parse_contract
        self.policy = parse_contract(contract)
        self.manifest = require(self.policy)
        self.db = db
        self.db_name = db.name
        self.rows = db.client[self.manifest['shared_control_database']][ACCOUNT_COLLECTION]
        self.key = fingerprint([VERSION, BATCH])
        self.sha = fingerprint(self.manifest)
        self.handler = sys.modules[__name__]

    def _read(self):
        row = self.rows.find_one({'_id': self.key})
        if not row or row.get('manifest_sha256') != self.sha:
            raise APIError(409, 'output_account_identity_conflict', '完整反馈候选共享账本身份不一致。')
        return row

    def _cas(self, prior, values):
        if not self.rows.update_one({'_id': self.key, 'version': prior['version']},
                {'$set': values, '$inc': {'version': 1}}).matched_count:
            raise APIError(409, 'output_account_busy', '完整反馈候选账本并发冲突，暂停派发。')

    def _member(self, context):
        entry = current_entry(self.policy, context['question']['id'], manifest=self.manifest)
        if entry['member']['candidate_slot'] != self.policy.admission.member_slot:
            raise ValueError('Run不属于合同授权的候选版本')
        return entry

    def initialize(self):
        seed = dict(manifest_sha256=self.sha, version=0, state='open', pending=None, settled={}, cursor=0,
            prior_input_tokens=0, prior_output_tokens=0, known_new_input_tokens=0, known_new_output_tokens=0,
            new_input_tokens=0, new_output_tokens=0, provider_stream_reservations=0,
            job_reservations=0, unknown_windows=[], exact_http_requests=None, exact_cost=None)
        try:
            self.rows.update_one({'_id': self.key}, {'$setOnInsert': seed}, upsert=True)
        except DuplicateKeyError:
            pass
        return self._read()

    def require_run_settled(self, run_id, run_identity):
        saved = self.initialize()
        receipt = next((item for item in saved['settled'].values()
            if item['run_id'] == run_id and item['run_identity'] == run_identity), None)
        if (receipt is None or not receipt['completed'] or saved['state'] == 'blocked' or
                saved['unknown_windows'] or (batch_dir() / 'halt.json').exists()):
            self.recover_unknown(dict(status='unsettled_or_failed_run', run_id=run_id))
            raise CandidateBatchStop('完整反馈候选Run未成功结算，整批停止。')
        entry = next(e for e in self.manifest['entries'] if e['member']['fixed_slot'] == receipt['slot'])
        run = self.db.runs.find_one({'run_id': run_id, 'identity': run_identity})
        if run is None:
            raise ValueError('候选结算找不到原持久Run')
        if entry['member']['expected_generation']:
            self.handler.validate_persisted_input(self.policy, self.db, run, entry['member']['question_id'])
        elif self.db.feedback_candidate_generation_inputs.find_one({'_id': run_id}) is not None:
            raise ValueError('零调用澄清不能出现生成输入记录')
        self._seal(receipt)
        return saved

    def recover_unknown(self, evidence):
        """观察恢复不调用模型；无法证明已结算的窗口永久封存。"""
        saved = self.initialize()
        if saved['state'] == 'dispatching':
            # 即使租约已过期也不能证明旧进程不会使用已取得的派发权。
            # 只记录未知在途并挡住后续；不落halt、不宣称网络已经停止。
            marker = dict(reason='dispatch_in_flight_unknown', pending=copy.deepcopy(saved['pending']))
            if marker not in saved['unknown_windows']:
                self._cas(saved, dict(unknown_windows=saved['unknown_windows'] + [marker],
                    new_input_tokens=None, new_output_tokens=None))
            path = batch_dir() / 'in-flight-unknown.json'
            if not path.exists():
                try:
                    self.handler.exclusive(path, marker)
                except FileExistsError:
                    pass
            raise APIError(409, 'output_dispatch_in_flight', '无法证明既有派发已经结束；保留未知窗口，不宣称停止成功。')
        if saved['state'] != 'blocked':
            windows = list(saved['unknown_windows'])
            windows.append(dict(reason='unsettled_execution', evidence=evidence,
                pending=copy.deepcopy(saved.get('pending'))))
            self._cas(saved, dict(state='blocked', unknown_windows=windows,
                new_input_tokens=None, new_output_tokens=None, halt=evidence))
        if not (batch_dir() / 'halt.json').exists():
            self.handler.seal_stop(evidence)
        return self._read()

    def begin(self, run_id, run_identity, *, input_reservation=0, risk_context=None, zero_generation=False):
        context = risk_context
        if not context:
            raise ValueError('缺少完整反馈候选正式Run上下文')
        self.handler = sys.modules[__name__]
        self.handler.validate_config(context['config'], context['control_database'], question=context['question'])
        run = self.db.runs.find_one({'run_id': run_id})
        if not run or run.get('identity') != run_identity:
            raise ValueError('反馈候选预留Run身份不一致')
        self.handler.validate_runtime(self.policy, run, context, self.db)
        entry = self._member(context)
        member = entry['member']
        generated = member['expected_generation']
        if generated:
            self.handler.validate_persisted_input(self.policy, self.db, run, context['question']['id'])
        if zero_generation == generated or type(input_reservation) is not int or input_reservation < 0:
            raise ValueError('反馈候选调用类型与题级预算不一致')
        expected_input = entry['production_input']['result']['budget']['input_tokens'] if generated else 0
        output_reservation = 4096 if generated else 0
        if input_reservation != expected_input:
            raise ValueError('反馈候选实际输入预留不等于逐题冻结输入')
        saved = self.initialize()
        slot = member['fixed_slot']
        order = self.manifest['dispatch_order']
        if (saved['state'] != 'open' or saved.get('pending') is not None or slot in saved['settled'] or
                saved['cursor'] >= len(order) or order[saved['cursor']] != slot or
                saved['known_new_input_tokens'] + input_reservation > self.policy.max_total_input_tokens or
                saved['known_new_output_tokens'] + output_reservation > self.policy.max_total_output_tokens or
                (batch_dir() / 'halt.json').exists() or
                (slot_dir(slot) / 'started.json').exists() or (slot_dir(slot) / 'settled.json').exists()):
            raise APIError(409, 'output_account_blocked', '反馈候选顺序、停止状态、重复槽或预算不符，禁止派发。')
        pending = dict(slot=slot, candidate_slot=member['candidate_slot'], run_id=run_id,
            run_identity=run_identity, input_reservation=input_reservation, output_reservation=output_reservation,
            expected_generation=generated, at=now(), contract_sha256=fingerprint(self.policy.model_dump(mode='json')),
            control_database=context['control_database'], target_database=self.db.name,
            config_sha256=fingerprint(context['config']),
            execution={k: context['execution'][k] for k in ('experiment_id', 'attempt', 'config_sha256')})
        self._cas(saved, dict(state='pending', pending=pending,
            new_input_tokens=None, new_output_tokens=None,
            provider_stream_reservations=saved['provider_stream_reservations'] + int(generated),
            job_reservations=saved['job_reservations'] + 1))
        if (batch_dir() / 'halt.json').exists():
            current = self._read()
            self._cas(current, dict(state='blocked'))
            raise APIError(409, 'output_account_blocked', '批次停止已封存，保留本次预留且不联网。')
        path = slot_dir(slot) / 'started.json'
        self.handler.exclusive(path, dict(manifest_sha256=self.sha, **pending))
        # 派发权与halt争用同一版本。halt先赢则不能返回给provider；
        # dispatching先赢则该次调用已在途，halt明确拒绝，待结算后再停。
        current = self._read()
        if current['state'] != 'pending' or current.get('pending') != pending:
            raise APIError(409, 'output_account_blocked', '反馈候选派发前已停止。')
        self._cas(current, dict(state='dispatching'))

    def _seal(self, receipt):
        slot = receipt['slot']
        started = read(slot_dir(slot) / 'started.json')
        if any(started.get(k) != receipt.get(k) for k in ('run_id', 'run_identity')):
            raise ValueError('反馈候选结算Run与原预留不一致')
        value = dict(manifest_sha256=self.sha, receipt=receipt)
        path = slot_dir(slot) / 'settled.json'
        if path.exists():
            if read(path) != value:
                raise ValueError('反馈候选首次结算证据不可覆盖')
        else:
            try:
                self.handler.exclusive(path, value)
            except FileExistsError:
                if read(path) != value:
                    raise ValueError('并发反馈候选结算证据冲突')

    def settle(self, run_id, run_identity, usage, *, completed, reasoning=None,
               logical_calls=None, observations=None, product_state=None):
        from .output_contract import usage_receipt
        receipt = usage_receipt(usage, reasoning=reasoning, observations=observations) | dict(
            run_id=run_id, run_identity=run_identity, completed=bool(completed), product_state=product_state,
            logical_provider_calls={k: logical_calls.get(k) for k in ('invoke_started', 'stream_started')}
                if isinstance(logical_calls, dict) else None)
        saved = self._read()
        pending = saved.get('pending') or {}
        if pending.get('run_id') != run_id or pending.get('run_identity') != run_identity:
            prior = next((row for row in saved['settled'].values()
                if row.get('run_id') == run_id and row.get('run_identity') == run_identity), None)
            if prior is not None:
                receipt['slot'] = prior['slot']
                self._finish(receipt)
                return self._read()
            raise APIError(409, 'output_settlement_conflict', '反馈候选没有匹配的生成预留。')
        if not pending.get('expected_generation'):
            raise APIError(409, 'output_settlement_conflict', '澄清槽不得结算模型usage。')
        receipt['slot'] = pending['slot']
        self._finish(receipt)
        return self._read()

    def _finish(self, receipt):
        saved = self._read()
        slot = receipt['slot']
        if slot in saved['settled']:
            if saved['settled'][slot] != receipt:
                raise APIError(409, 'output_settlement_conflict', '相同反馈成员的结算不能改变。')
            self._seal(receipt)
            return saved
        pending = saved.get('pending')
        if not pending or pending.get('slot') != slot:
            raise APIError(409, 'output_settlement_conflict', '反馈候选无匹配的调用前持久关联。')
        known = receipt['input_tokens'] is not None and receipt['output_tokens'] is not None
        input_total = saved['known_new_input_tokens'] + (receipt['input_tokens'] or 0)
        output_total = saved['known_new_output_tokens'] + (receipt['output_tokens'] or 0)
        product = receipt.get('product_state') or {}
        zero = not pending['expected_generation']
        observations = receipt['usage_validation'].get('observations', [])
        positive_reasoning = any(type(o.get('counts', {}).get('reasoning')) is int and
            o['counts']['reasoning'] > 0 for o in observations)
        logical_calls = receipt.get('logical_provider_calls')
        one_stream = (isinstance(logical_calls, dict) and
            type(logical_calls.get('invoke_started')) is int and
            type(logical_calls.get('stream_started')) is int and
            logical_calls == dict(invoke_started=0, stream_started=1))
        valid_product = ((product.get('clarification_valid') is True and
            receipt['logical_provider_calls'] == dict(invoke_started=0, stream_started=0) and
            receipt['input_tokens'] == 0 and receipt['output_tokens'] == 0) if zero else
            product.get('visible_body') is True and product.get('truncated') is False and
            product.get('finish_reason') == 'stop' and product.get('observed_reasoning') is False and
            receipt['reasoning_tokens'] in (None, 0) and not positive_reasoning and one_stream)
        good = (not saved['unknown_windows'] and saved['state'] in {'pending', 'dispatching'} and
            not (batch_dir() / 'halt.json').exists() and known and receipt['completed'] and receipt['usage_validation']['valid'] and
            receipt['input_tokens'] <= pending['input_reservation'] and
            receipt['output_tokens'] <= pending['output_reservation'] and
            input_total <= self.policy.max_total_input_tokens and
            output_total <= self.policy.max_total_output_tokens and valid_product)
        windows = list(saved['unknown_windows'])
        if not good:
            reason = 'invalid_usage' if not receipt['usage_validation']['valid'] or not known else 'incomplete_or_output_rejected'
            windows.append(dict(slot=slot, run_id=receipt['run_id'], reason=reason,
                usage=receipt['usage_validation'].get('reported')))
        next_cursor = saved['cursor'] + int(good)
        next_state = ('awaiting_quality_review' if good and next_cursor == EXPECTED_MEMBERS else
            'open' if good else 'blocked')
        self._cas(saved, dict(state=next_state, pending=None,
            settled=saved['settled'] | {slot: receipt}, cursor=saved['cursor'] + int(good),
            known_new_input_tokens=input_total, known_new_output_tokens=output_total,
            new_input_tokens=input_total if good else None, new_output_tokens=output_total if good else None,
            unknown_windows=windows,
            completed_at=now() if good and next_cursor == EXPECTED_MEMBERS else None))
        self._seal(receipt)
        if not good:
            self.handler.seal_stop(dict(slot=slot, run_id=receipt['run_id'], status='blocked',
                completed=receipt['completed'], usage_validation=receipt['usage_validation'], product_state=product))
        return self._read()

    def settle_clarification(self, run, result):
        entry = current_entry(self.policy, self._pending_question(), manifest=self.manifest)
        if entry['member']['expected_generation']:
            raise ValueError('只有冻结澄清成员允许零provider结算')
        valid = (run.get('state') == 'awaiting_input' and not result.get('answer') and
            result.get('behavior') == 'clarify' and
            result.get('run_id') == run.get('run_id'))
        receipt = dict(slot=entry['member']['fixed_slot'], run_id=run['run_id'], run_identity=run['identity'],
            completed=valid, input_tokens=0, output_tokens=0, reasoning_tokens=0,
            visible_tokens=None, http_requests=None, cost=None,
            logical_provider_calls=dict(invoke_started=0, stream_started=0),
            usage_validation=dict(valid=True, reported=dict(input=0, output=0, reasoning=0)),
            product_state=dict(clarification_valid=valid))
        saved = self._read()
        pending = saved.get('pending') or {}
        if pending.get('slot') != receipt['slot'] or pending.get('run_id') != run['run_id'] or pending.get('expected_generation'):
            raise APIError(409, 'output_settlement_conflict', '澄清成员缺少零调用预留。')
        return self._finish(receipt)

    def _pending_question(self):
        row = self._read()
        if not row.get('pending'):
            raise APIError(409, 'output_settlement_conflict', '没有待结算的澄清成员。')
        slot = row['pending']['slot']
        return next(e['member']['question_id'] for e in self.manifest['entries']
            if e['member']['fixed_slot'] == slot)

    def require_open(self):
        saved = self._read()
        if (saved['state'] not in {'open', 'awaiting_quality_review'} or saved['pending'] is not None or
                saved['unknown_windows'] or saved['cursor'] < EXPECTED_MEMBERS and
                (batch_dir() / 'halt.json').exists()):
            raise APIError(409, 'output_account_blocked', '反馈候选存在未知窗口、停止证据或未结算成员。')
        return saved

    def halt(self, evidence):
        saved = self._read()
        if saved['state'] == 'dispatching':
            raise APIError(409, 'output_dispatch_in_flight', '调用已取得派发权；须观察结算，不能宣称已经停止。')
        if saved.get('halt'):
            if saved['halt'] != evidence:
                raise ValueError('反馈候选首次停止证据不可改变')
            return saved
        self._cas(saved, dict(state='blocked', halt=evidence))
        self.handler.seal_stop(evidence)
        return self._read()


def exclusive(path, value):
    from .product_risk import exclusive as write_exclusive
    return write_exclusive(path, value)
