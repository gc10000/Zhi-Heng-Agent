"""不可变题级审阅与先校准后比较的质量门槛；不执行知识发布。"""
from copy import deepcopy
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.knowledge.repository import fingerprint
from .review_followups import FollowupLedger
from .review_protocol import Applicability, ObservationLedger, review_dump
from app.answering.image_selection import has_review_images
from .development_policy import PolicyReference

Score = Literal[0, 1, 2, 'unknown', 'not_applicable']
DIMENSIONS = ('factuality', 'citation_support', 'actionability', 'image_relevance')


class Scores(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    factuality: Score
    citation_support: Score
    actionability: Score
    image_relevance: Score

    @field_validator('*', mode='before')
    @classmethod
    def explicit_score(cls, value):
        # Literal会按相等关系接受True和1.0，评分必须保留明确输入类型。
        if type(value) is int and value in (0, 1, 2):
            return value
        if type(value) is str and value in ('unknown', 'not_applicable'):
            return value
        raise ValueError('评分只接受整数0/1/2、unknown或not_applicable')

    @model_validator(mode='after')
    def factuality_required(self):
        if self.factuality == 'not_applicable':
            raise ValueError('事实维度不能标为不适用，可标未知')
        return self


class ReviewInput(Applicability):
    model_config = ConfigDict(extra='forbid', strict=True)
    question_id: str = Field(min_length=1, max_length=128)
    subject_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    client_request_id: str = Field(min_length=1, max_length=128)
    round: int = Field(ge=1, le=2)
    reviewer_kind: Literal['human', 'assistant', 'model']
    human_attested: bool = False
    source_checked: bool
    scores: Scores
    critical_errors: list[Literal['unauthorized', 'wrong_model', 'wrong_object', 'fabricated_live_state', 'unsafe_procedure']] = Field(max_length=5)
    rationale: str = Field(min_length=1, max_length=4000)
    observation_id: str | None = Field(default=None, min_length=1, max_length=128)
    quality_policy: dict | None = None
    review_execution_id: str | None = Field(default=None,pattern=r'^[0-9a-f]{64}$')
    dimension_evidence: dict[str,str] = Field(default_factory=dict)

    @model_validator(mode='after')
    def attribution(self):
        if not self.rationale.strip():
            raise ValueError('须填写核对依据或未知原因')
        if self.reviewer_kind == 'human' and not (self.human_attested and self.source_checked):
            raise ValueError('人工评分须明确本人已核对原件；未核对请记录辅助审阅和未知')
        if self.reviewer_kind != 'human' and self.human_attested:
            raise ValueError('辅助审阅不能声称人工核对')
        if self.quality_policy:
            from .development_policy import PolicyReference
            PolicyReference.model_validate(self.quality_policy)
            if self.reviewer_kind!='assistant' or self.human_attested or not self.review_execution_id:
                raise ValueError('助手开发政策须使用真实助手执行身份')
            if set(self.dimension_evidence)!=set(DIMENSIONS) or any(not s.strip() or len(s)>4000 for s in self.dimension_evidence.values()):
                raise ValueError('开发审核须逐维保存原件依据或未知原因')
        elif self.review_execution_id or self.dimension_evidence:
            raise ValueError('审核执行及逐维依据须显式绑定开发政策')
        return self


class CalibrationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    client_request_id: str = Field(min_length=1, max_length=128)
    rationale: str = Field(min_length=1, max_length=4000)
    quality_policy: PolicyReference | None = None


class ObservationInput(Applicability):
    model_config = ConfigDict(extra='forbid', strict=True)
    question_id: str = Field(min_length=1, max_length=128)
    subject_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    source_message_id: str = Field(min_length=1, max_length=128)
    statement: str = Field(min_length=1, max_length=8000)
    scores: Scores

    @model_validator(mode='after')
    def nonblank(self):
        if not self.statement.strip() or not self.source_message_id.strip():
            raise ValueError('须保留原话和稳定的聊天来源标识')
        return self


def public(row):
    return {k: deepcopy(v) for k, v in row.items() if k not in {'_id', 'request_sha256', 'owner_id'}}


class ReviewService:
    def __init__(self, repo):
        self.repo = repo
        self.reviews = repo.db.evaluation_reviews
        self.calibrations = repo.db.evaluation_calibrations
        self.reviews.create_index([('owner_id', 1), ('client_request_id', 1)], unique=True)
        self.reviews.create_index([('experiment_id', 1), ('subject_sha256', 1), ('reviewer_id', 1),
                                   ('reviewer_kind', 1), ('round', 1)], unique=True)
        self.calibrations.create_index('calibration_id', unique=True)
        self.calibrations.create_index([('owner_id', 1), ('client_request_id', 1)], unique=True)
        self.followups = FollowupLedger(repo.db)
        self.observations = ObservationLedger(repo.db)

    def list_observations(self, user, eid):
        experiment,_=self._subjects(user, eid)
        if experiment.get('quality_policy'):
            from .development_policy import DevelopmentPolicy
            if not DevelopmentPolicy(self.repo).visible(eid):
                return {'items':[], 'next_cursor':None}
        return {'items': [public(r) for r in self.observations.rows.find({'experiment_id': eid})], 'next_cursor': None}

    def observe(self, user, eid, data):
        _, subjects = self._subjects(user, eid)
        subject = subjects.get(data.question_id)
        if not subject or subject[0] != data.subject_sha256:
            raise APIError(409, 'review_subject_changed', '聊天反馈须绑定当前已完成结果。')
        return public(self.observations.append(user, eid, data))

    def _subjects(self, user, eid):
        experiment = self.repo.get_experiment(user, eid)
        if experiment['state'] != 'completed':
            raise APIError(409, 'review_results_unavailable', '只审阅已完成实验的已发布结果。')
        rows = list(self.repo.results.find({'experiment_id': eid, 'attempt': experiment.get('result_attempt')}))
        subjects = {}
        for row in rows:
            clean = {k: v for k, v in row.items() if k not in {'_id', 'experiment_id', 'attempt'}}
            subjects[row['question_id']] = (fingerprint(clean), clean)
        return experiment, subjects

    def list(self, user, eid):
        experiment, subjects = self._subjects(user, eid)
        from .development_policy import DevelopmentPolicy
        visible=not experiment.get('quality_policy') or DevelopmentPolicy(self.repo).visible(eid)
        return {'quality_policy':experiment.get('quality_policy'),
                'purpose':'development_acceptance' if experiment.get('quality_policy') else 'human_publication',
                'subjects': [dict(question_id=q, subject_sha256=s[0]) for q, s in sorted(subjects.items())],
                'items': [public(r) for r in self.reviews.find({'experiment_id': eid})] if visible else [],
                'followups': [public(r) for r in self.followups.rows.find({'experiment_id': eid})] if visible else [], 'next_cursor': None}

    def followup(self, user, eid, review_id, data):
        _, subjects = self._subjects(user, eid)
        original = self.reviews.find_one({'experiment_id': eid, 'review_id': review_id, 'reviewer_id': user.user_id})
        if original is None:
            raise APIError(404, 'not_found', '原审阅不存在或不是当前审核者的记录。')
        subject = subjects.get(original['question_id'])
        if not subject or subject[0] != original['subject_sha256'] or subject[0] != data.subject_sha256:
            raise APIError(409, 'review_subject_changed', '答案或来源已变化，不能对旧结果追加结论。')
        clean = {k: deepcopy(v) for k, v in original.items() if k != '_id'}
        return public(self.followups.append(user, eid, clean, data, subject[1].get('result') or {}))

    def submit(self, user, eid, data):
        experiment, subjects = self._subjects(user, eid)
        if data.quality_policy != experiment.get('quality_policy'):
            raise APIError(409,'quality_policy_mismatch','评分与实验政策身份不一致。')
        if data.quality_policy:
            from .development_policy import DevelopmentPolicy
            DevelopmentPolicy(self.repo).sealed_review(user,eid,data)
        subject = subjects.get(data.question_id)
        if not subject or subject[0] != data.subject_sha256:
            raise APIError(409, 'review_subject_changed', '结果内容已改变，请刷新后对新结果审阅。')
        result = subject[1].get('result') or {}
        if data.scores.image_relevance == 'not_applicable' and has_review_images(result):
            raise APIError(422, 'image_review_required', '含配图来源的结果须审核图片，可标未知。')
        self.observations.require_reference(user, eid, data)
        fields = review_dump(data)
        identity = fingerprint({'experiment_id': eid, **fields})
        row = dict(experiment_id=eid, owner_id=user.user_id, reviewer_id=user.user_id,
                   review_id=str(uuid4()), created_at=datetime.now(timezone.utc).isoformat(),
                   request_sha256=identity, **fields)
        try:
            self.reviews.insert_one(row)
        except DuplicateKeyError:
            prior = self.reviews.find_one({'owner_id': user.user_id, 'client_request_id': data.client_request_id})
            if not prior or prior['request_sha256'] != identity:
                raise APIError(409, 'review_conflict', '审阅轮次或请求标识已存在；历史审阅不可覆盖。') from None
            return public(prior)
        return public(row)

    def _quality(self, user, eid, *, human_only=False):
        experiment, subjects = self._subjects(user, eid)
        originals = [{k: v for k, v in r.items() if k != '_id'} for r in self.reviews.find({'experiment_id': eid})]
        reviews, followup_ids = self.followups.effective(originals,
            list(self.followups.rows.find({'experiment_id': eid})))
        policy=experiment.get('quality_policy') if not human_only else None
        known_critical={r['question_id'] for r in originals if policy and r.get('quality_policy')==policy and
            r.get('critical_errors') and r['question_id'] in subjects and r['subject_sha256']==subjects[r['question_id']][0]}
        attestations=[]
        if policy:
            from .development_policy import DevelopmentPolicy
            reviews,attestations=DevelopmentPolicy(self.repo).effective(user,eid,reviews)
        critical, incomplete, values, bound, rubrics = list(known_critical), [], {}, [], {}
        if not subjects or len(subjects) != experiment.get('selected_questions'):
            incomplete.append('incomplete_question_set')
        for qid, (sha, result) in subjects.items():
            current = [r for r in reviews if r['question_id'] == qid and r['subject_sha256'] == sha]
            if any(r['critical_errors'] for r in current):
                critical.append(qid)
            humans = ([r for r in current if r['reviewer_kind']=='assistant' and r.get('quality_policy')==policy and r['source_checked']]
                if policy else [r for r in current if r['reviewer_kind'] == 'human' and r['human_attested'] and r['source_checked']])
            versions = {r.get('rubric_version', 'legacy-v1') for r in humans}
            if versions - {'legacy-v1'}:
                rubrics[qid] = sorted(versions)
            if len(versions) > 1:
                incomplete.append(qid)
            # 两名审核者可各负责一轮；同一人必须分轮提交，不改写旧分。
            if {r['round'] for r in humans} != {1, 2} or result['status'] != 'completed':
                incomplete.append(qid)
                continue
            values[qid] = {}
            for dimension in DIMENSIONS:
                scores = [r['scores'][dimension] for r in humans]
                if dimension == 'image_relevance' and 'not_applicable' in scores and has_review_images(result.get('result') or {}):
                    # 历史误标不改写，但不能将实际可见答案图冻结为null或通过旧门槛。
                    incomplete.append(qid)
                    continue
                if 'unknown' in scores or ('not_applicable' in scores and set(scores) != {'not_applicable'}):
                    incomplete.append(qid)
                elif set(scores) == {'not_applicable'}:
                    values[qid][dimension] = None
                else:
                    values[qid][dimension] = min(scores)
            bound.extend(r['review_id'] for r in humans)
        quality = dict(critical=sorted(set(critical)), incomplete=sorted(set(incomplete)), values=values,
            subjects={q: s[0] for q, s in subjects.items()}, review_ids=sorted(bound))
        # 无追加记录时保留旧校准结构，已冻结的历史证明不因升级无条件失效。
        if followup_ids:
            quality['followup_ids'] = followup_ids
        if rubrics:
            quality['rubrics'] = rubrics
        if policy:
            quality.update(policy=policy,purpose='development_acceptance',independence_attestations=attestations)
            sources={}
            for r in reviews:
                if r.get('dimension_sources'):
                    for dimension,source in r['dimension_sources'].items():
                        sources.setdefault(r['question_id'],{}).setdefault(dimension,[]).append(source)
            if sources:
                quality['dimension_sources']={q:{d:sorted(v,key=lambda s:s['round']) for d,v in dims.items()} for q,dims in sources.items()}
        return experiment, quality

    def calibrate(self, user, eid, data):
        fields=data.model_dump(exclude_none=True)
        experiment=self.repo.get_experiment(user,eid)
        if fields.get('quality_policy')!=experiment.get('quality_policy'):
            raise APIError(409,'quality_policy_mismatch','校准请求须明确匹配实验的政策身份。')
        identity = fingerprint({'experiment_id': eid, **fields})
        prior = self.calibrations.find_one({'owner_id': user.user_id, 'client_request_id': data.client_request_id})
        self.repo.get_experiment(user, eid)
        if prior:
            if prior['request_sha256'] != identity:
                raise APIError(409, 'idempotency_conflict', '校准请求已绑定其他内容。')
            return public(prior)
        experiment, quality = self._quality(user, eid)
        if quality['incomplete'] or quality['critical']:
            raise APIError(409, 'development_review_required' if experiment.get('quality_policy') else 'human_review_required',
                '基线需要本政策有效双轮原件核对，且无关键错误和未知维度。')
        row = dict(calibration_id=str(uuid4()), experiment_id=eid, owner_id=user.user_id,
            kb_id=experiment['kb_id'], dataset_sha256=experiment['dataset_sha256'],
            manifest_sha256=experiment['manifest_sha256'], baseline=quality, tolerance=0,
            created_at=datetime.now(timezone.utc).isoformat(), request_sha256=identity, **fields)
        if experiment.get('quality_policy'): row['quality_policy']=experiment['quality_policy']
        try:
            self.calibrations.insert_one(row)
        except DuplicateKeyError:
            return self.calibrate(user, eid, data)
        return public(row)

    def gate(self, user, eid, calibration_id, *, human_only=False):
        experiment, current = self._quality(user, eid,human_only=human_only)
        calibration = self.calibrations.find_one({'calibration_id': calibration_id, 'owner_id': user.user_id,
                                                  'kb_id': {'$in': list(user.kb_ids)}})
        if calibration is None:
            raise APIError(404, 'not_found', '校准不存在或不在授权范围。')
        baseline, live_baseline = self._quality(user, calibration['experiment_id'],human_only=human_only)
        reasons = []
        if calibration.get('quality_policy')!=experiment.get('quality_policy') or (human_only and calibration.get('quality_policy')):
            reasons.append('quality_policy_mismatch')
        if current.get('rubrics', {}) != calibration['baseline'].get('rubrics', {}):
            reasons.append('rubric_changed')
        if (calibration['baseline'] != live_baseline or current['incomplete']):
            reasons.append('review_pending_or_changed')
        if (experiment['dataset_sha256'] != calibration['dataset_sha256'] or
                experiment.get('manifest_sha256') != calibration['manifest_sha256'] or
                experiment['kb_id'] != calibration['kb_id'] or
                set(current['subjects']) != set(live_baseline['subjects'])):
            reasons.append('incompatible_question_set')
        if experiment['created_at'] <= calibration['created_at']:
            reasons.append('candidate_precedes_calibration')
        if current['critical'] or live_baseline['critical']:
            reasons.append('critical_error')
        regressions = []
        for qid, scores in current['values'].items():
            old = calibration['baseline']['values'].get(qid, {})
            for dimension, value in scores.items():
                if dimension not in old or (value is None) != (old[dimension] is None):
                    reasons.append('applicability_changed')
                elif value is not None and value < old[dimension]:
                    regressions.append(dict(question_id=qid, dimension=dimension))
        if regressions:
            reasons.append('quality_regression')
        status = ('blocked' if {'critical_error', 'quality_regression'} & set(reasons) else
                  'pending' if reasons else 'passed')
        result=dict(status=status, reasons=sorted(set(reasons)), regressions=regressions,
                    calibration_id=calibration_id, candidate_experiment_id=eid,
                    human_review_count=len(current['review_ids']) if not experiment.get('quality_policy') else 0, automatic_publish=False)
        if experiment.get('quality_policy'):
            result.update(quality_policy=experiment['quality_policy'],purpose='development_acceptance',
                assistant_review_count=len(current['review_ids']),human_publication_status='pending')
            if (experiment.get('baseline_experiment_id')!=calibration['experiment_id'] or
                experiment.get('quality_calibration_id')!=calibration_id):
                result['reasons']=sorted(set(result['reasons']+['candidate_calibration_not_bound']))
                if result['status']=='passed':result['status']='pending'
        if human_only:
            result.update(purpose='human_publication',assistant_review_count=0,human_review_count=len(current['review_ids']))
        return result
