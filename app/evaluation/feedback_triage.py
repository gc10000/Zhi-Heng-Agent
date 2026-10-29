"""反馈审核以单文档CAS保存结论和草稿，不自动修改知识或真值。"""
from copy import deepcopy
from datetime import datetime, timezone
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.api.errors import APIError
from app.knowledge.repository import fingerprint


class TriageInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0, strict=True)
    decision: Literal['confirm', 'reject']
    destination: Literal['regression', 'revision'] | None = None
    rationale: str = Field(min_length=1, max_length=4000)
    proposed_question: str | None = Field(default=None, max_length=4000)
    proposed_expectation: str | None = Field(default=None, max_length=4000)
    client_request_id: str = Field(min_length=1, max_length=128)

    @model_validator(mode='after')
    def complete_decision(self):
        if not self.rationale.strip():
            raise ValueError('审核须填写理由')
        if self.decision == 'confirm':
            if not self.destination or not (self.proposed_question or '').strip() or not (self.proposed_expectation or '').strip():
                raise ValueError('确认反馈须填写草稿问题与预期，不自动作为标准答案')
        elif self.destination is not None or self.proposed_question is not None or self.proposed_expectation is not None:
            raise ValueError('驳回反馈不能同时创建草稿')
        return self


class BindRevisionInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0, strict=True)
    document_id: str = Field(min_length=1, max_length=128)
    revision_id: str = Field(min_length=1, max_length=128)
    affected_question_ids: list[str] = Field(min_length=1, max_length=200)

    @model_validator(mode='after')
    def unique_questions(self):
        if len(set(self.affected_question_ids)) != len(self.affected_question_ids) or any(
                not q.strip() or len(q) > 128 for q in self.affected_question_ids):
            raise ValueError('受影响题必须是明确且不重复的身份')
        return self


def bind_revision(request, user, feedback_id, data):
    row = authorized_feedback(request, user, feedback_id)
    if row['state'] != 'confirmed' or row.get('draft', {}).get('kind') != 'revision':
        raise APIError(409, 'revision_draft_required', '仅确认的资料修订建议可绑定待发布修订。')
    gateway = request.app.state.resources['knowledge']()
    revision = gateway.revision(user, data.document_id, data.revision_id)
    if revision['kb_id'] != row['kb_id'] or revision['status'] not in {'staged', 'validated'}:
        raise APIError(409, 'revision_not_staged', '修订必须属于反馈知识库且尚未发布。')
    target = dict(target_document_id=data.document_id, target_revision_id=data.revision_id,
                  affected_question_ids=sorted(data.affected_question_ids))
    same = all(row['draft'].get(k) == v for k, v in target.items())
    if not same and (row.get('version', 0) != data.expected_version or row['draft'].get('target_revision_id')):
        raise APIError(409, 'version_conflict', '草稿版本改变或已绑定修订。')
    # 先在修订本身保留强制门禁，进程退出也不能留下无门禁的关联修订。
    repo = gateway.repo(row['kb_id'])
    binding = dict(feedback_id=feedback_id, affected_question_ids=sorted(data.affected_question_ids))
    reserved = repo.revisions.update_one(repo.scope | {'revision_id': data.revision_id,
        'status': {'$in': ['staged', 'validated']}, '$or': [
            {'feedback_gate': {'$exists': False}}, {'feedback_gate': binding}]}, {'$set': {'feedback_gate': binding}})
    if not reserved.matched_count:
        raise APIError(409, 'feedback_binding_conflict', '修订已绑定其他审核或状态已变化。')
    if same:
        return public_feedback(row)
    result = request.app.state.resources['db'].support_feedback.update_one(
        {'feedback_id': feedback_id, 'version': data.expected_version, 'state': 'confirmed',
         'draft.target_revision_id': {'$exists': False}},
        {'$set': {'draft.'+k: v for k, v in target.items()}, '$inc': {'version': 1}})
    if not result.matched_count:
        raise APIError(409, 'version_conflict', '草稿已被其他维护者绑定。')
    return public_feedback(authorized_feedback(request, user, feedback_id))


class QualityProofInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    expected_version: int = Field(ge=0, strict=True)
    stage: Literal['affected', 'full']
    experiment_id: str = Field(min_length=1, max_length=128)
    calibration_id: str = Field(min_length=1, max_length=128)


def save_quality_proof(request, user, feedback_id, data):
    from .repository import EvaluationRepository
    from .reviews import ReviewService
    row = authorized_feedback(request, user, feedback_id)
    draft = row.get('draft', {})
    if row['state'] != 'confirmed' or not draft.get('target_revision_id'):
        raise APIError(409, 'feedback_revision_unbound', '须先绑定反馈的新修订。')
    existing = draft.get('quality_proofs', {})
    if data.stage == 'full' and 'affected' not in existing:
        raise APIError(409, 'affected_regression_required', '须先保存受影响题通过证明，再创建完整发布回归。')
    gateway = request.app.state.resources['knowledge']()
    revision = gateway.revision(user, draft['target_document_id'], draft['target_revision_id'])
    if (revision['status'] != 'validated' or revision.get('validation') !=
            gateway.publisher(row['kb_id']).inspect(revision)):
        raise APIError(409, 'revision_validation_changed', '待发布修订尚未验证或内容改变。')
    reviews = ReviewService(EvaluationRepository(request.app.state.resources['db']))
    experiment = reviews.repo.get_experiment(user, data.experiment_id)
    gate = reviews.gate(user, data.experiment_id, data.calibration_id)
    binding = experiment.get('corpus_binding') or {}
    expected = {'document_id': revision['document_id'], 'revision_id': revision['revision_id'],
                'validation_sha256': fingerprint(revision['validation'])}
    if (gate['status'] != 'passed' or experiment['kb_id'] != row['kb_id'] or
            binding.get('database') != request.app.state.resources['db'].name or
            expected not in binding.get('candidate_revisions', [])):
        raise APIError(409, 'quality_proof_invalid', '实验未通过人工质量门槛，或未评测当前隔离目标的新修订。')
    _, quality = reviews._quality(user, data.experiment_id)
    questions = sorted(quality['subjects'])
    if not set(draft['affected_question_ids']) <= set(questions):
        raise APIError(409, 'affected_questions_missing', '实验未覆盖全部受影响题。')
    if data.stage == 'full':
        if (binding.get('is_full_dev') is not True or
                experiment['created_at'] <= existing['affected']['completed_at']):
            raise APIError(409, 'full_regression_required', '完整发布回归须在受影响题证明保存后创建，且覆盖冻结开发集全题。')
    proof = dict(experiment_id=data.experiment_id, calibration_id=data.calibration_id,
        result_attempt=experiment['result_attempt'], reviewer_id=user.user_id,
        validation_sha256=expected['validation_sha256'], question_ids=questions,
        created_at=experiment['created_at'], completed_at=datetime.now(timezone.utc).isoformat())
    prior = existing.get(data.stage)
    if prior:
        if all(prior[k] == proof[k] for k in proof if k != 'completed_at'):
            return public_feedback(row)
        raise APIError(409, 'quality_proof_conflict', '原回归证明不可覆盖，变更内容须创建新修订。')
    result = request.app.state.resources['db'].support_feedback.update_one(
        {'feedback_id': feedback_id, 'version': data.expected_version,
         'draft.target_revision_id': revision['revision_id'], 'draft.quality_proofs.'+data.stage: {'$exists': False}},
        {'$set': {'draft.quality_proofs.'+data.stage: proof}, '$inc': {'version': 1}})
    if not result.matched_count:
        raise APIError(409, 'version_conflict', '反馈版本改变，请刷新后核对证明。')
    return public_feedback(authorized_feedback(request, user, feedback_id))


def public_feedback(row):
    return {k: deepcopy(v) for k, v in row.items() if k not in {'_id', 'identity', 'review_identity'}}


def authorized_feedback(request, user, feedback_id):
    resources = request.app.state.resources
    row = resources['db'].support_feedback.find_one({'feedback_id': feedback_id, 'kb_id': {'$in': list(user.kb_ids)}})
    if row is None:
        raise APIError(404, 'not_found', '反馈不存在或不在授权范围。')
    source_db = feedback_source_db(resources['db'],row)
    run = source_db.runs.find_one({'run_id': row['run_id'], 'kb_id': row['kb_id'], 'owner_id': row['owner_id']})
    if run is None:
        raise APIError(404, 'not_found', '反馈来源运行不可核对。')
    from app.support.api import authorize_payload
    # 反馈选中引用不能掩盖原回答中其他已撤权资料。
    authorize_payload(request, user, [row, run.get('citations', []), run.get('revision_snapshot', [])])
    return row


def feedback_source_db(control_db, feedback):
    """默认使用原控制库；显式映射仅取自服务端反馈账本，不接受HTTP路径/库名。"""
    name = feedback.get('source_database',control_db.name)
    if not isinstance(name,str) or not name or any(c in name for c in '/\\ ."$\x00'):
        raise APIError(409,'feedback_source_database_invalid','反馈来源库映射无效。')
    return control_db.client[name]


def review_feedback(request, user, feedback_id, data):
    row = authorized_feedback(request, user, feedback_id)
    collection = request.app.state.resources['db'].support_feedback
    identity = fingerprint({'reviewer_id': user.user_id, **data.model_dump()})
    if row.get('review_identity') == identity:
        return public_feedback(row)
    if row['state'] != 'pending_review' or row.get('version', 0) != data.expected_version:
        raise APIError(409, 'version_conflict', '反馈已经审核或版本改变，请刷新。')
    now = datetime.now(timezone.utc).isoformat()
    changes = dict(state='confirmed' if data.decision == 'confirm' else 'rejected',
        version=data.expected_version + 1, reviewer_id=user.user_id, reviewed_at=now,
        review_identity=identity, review_request_id=data.client_request_id, rationale=data.rationale.strip())
    if data.decision == 'confirm':
        revisions = sorted({(c['document_id'], c['revision_id']) for c in row.get('citations', [])
                            if c.get('document_id') and c.get('revision_id')})
        changes['draft'] = dict(draft_id=row['feedback_id'] + ':' + data.destination,
            kind=data.destination, annotation_status='draft', source='reviewed_feedback',
            feedback_id=row['feedback_id'], run_id=row['run_id'], kb_id=row['kb_id'],
            question=data.proposed_question.strip(), proposed_expectation=data.proposed_expectation.strip(),
            source_revisions=[dict(document_id=d, revision_id=r) for d, r in revisions],
            publication_state=('requires_affected_then_full_regression'
                               if data.destination == 'revision' else 'not_applicable'), created_at=now)
    query = {'feedback_id': feedback_id, 'state': 'pending_review', 'kb_id': row['kb_id'],
             '$or': [{'version': data.expected_version}, {'version': {'$exists': False}}] if data.expected_version == 0 else [{'version': data.expected_version}]}
    result = collection.update_one(query, {'$set': changes})
    if not result.matched_count:
        latest = authorized_feedback(request, user, feedback_id)
        if latest.get('review_identity') == identity:
            return public_feedback(latest)
        raise APIError(409, 'version_conflict', '其他审核者已提交，本次没有覆盖历史结论。')
    return public_feedback(authorized_feedback(request, user, feedback_id))
