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


class ReviewInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    question_id: str = Field(min_length=1, max_length=128)
    subject_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    client_request_id: str = Field(min_length=1, max_length=128)
    round: int = Field(ge=1, le=2)
    reviewer_kind: Literal['human', 'assistant', 'model']
    human_attested: bool = False
    source_checked: bool
    scores: Scores
    critical_errors: list[Literal['unauthorized', 'wrong_model']] = Field(max_length=2)
    rationale: str = Field(min_length=1, max_length=4000)

    @model_validator(mode='after')
    def attribution(self):
        if not self.rationale.strip():
            raise ValueError('须填写核对依据或未知原因')
        if self.reviewer_kind == 'human' and not (self.human_attested and self.source_checked):
            raise ValueError('人工评分须明确本人已核对原件；未核对请记录辅助审阅和未知')
        if self.reviewer_kind != 'human' and self.human_attested:
            raise ValueError('辅助审阅不能声称人工核对')
        return self


class CalibrationInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    client_request_id: str = Field(min_length=1, max_length=128)
    rationale: str = Field(min_length=1, max_length=4000)


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
        _, subjects = self._subjects(user, eid)
        return {'subjects': [dict(question_id=q, subject_sha256=s[0]) for q, s in sorted(subjects.items())],
                'items': [public(r) for r in self.reviews.find({'experiment_id': eid})],
                'followups': [public(r) for r in self.followups.rows.find({'experiment_id': eid})], 'next_cursor': None}

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
        _, subjects = self._subjects(user, eid)
        subject = subjects.get(data.question_id)
        if not subject or subject[0] != data.subject_sha256:
            raise APIError(409, 'review_subject_changed', '结果内容已改变，请刷新后对新结果审阅。')
        result = subject[1].get('result') or {}
        if data.scores.image_relevance == 'not_applicable' and any(
                c.get('asset_sha256') or c.get('asset_ids') for c in result.get('citations', [])):
            raise APIError(422, 'image_review_required', '含配图来源的结果须审核图片，可标未知。')
        identity = fingerprint({'experiment_id': eid, **data.model_dump()})
        row = dict(experiment_id=eid, owner_id=user.user_id, reviewer_id=user.user_id,
                   review_id=str(uuid4()), created_at=datetime.now(timezone.utc).isoformat(),
                   request_sha256=identity, **data.model_dump())
        try:
            self.reviews.insert_one(row)
        except DuplicateKeyError:
            prior = self.reviews.find_one({'owner_id': user.user_id, 'client_request_id': data.client_request_id})
            if not prior or prior['request_sha256'] != identity:
                raise APIError(409, 'review_conflict', '审阅轮次或请求标识已存在；历史审阅不可覆盖。') from None
            return public(prior)
        return public(row)

    def _quality(self, user, eid):
        experiment, subjects = self._subjects(user, eid)
        originals = [{k: v for k, v in r.items() if k != '_id'} for r in self.reviews.find({'experiment_id': eid})]
        reviews, followup_ids = self.followups.effective(originals,
            list(self.followups.rows.find({'experiment_id': eid})))
        critical, incomplete, values, bound = [], [], {}, []
        if not subjects or len(subjects) != experiment.get('selected_questions'):
            incomplete.append('incomplete_question_set')
        for qid, (sha, result) in subjects.items():
            current = [r for r in reviews if r['question_id'] == qid and r['subject_sha256'] == sha]
            if any(r['critical_errors'] for r in current):
                critical.append(qid)
            humans = [r for r in current if r['reviewer_kind'] == 'human' and r['human_attested'] and r['source_checked']]
            # 两名审核者可各负责一轮；同一人必须分轮提交，不改写旧分。
            if {r['round'] for r in humans} != {1, 2} or result['status'] != 'completed':
                incomplete.append(qid)
                continue
            values[qid] = {}
            for dimension in DIMENSIONS:
                scores = [r['scores'][dimension] for r in humans]
                if 'unknown' in scores or ('not_applicable' in scores and set(scores) != {'not_applicable'}):
                    incomplete.append(qid)
                elif set(scores) == {'not_applicable'}:
                    values[qid][dimension] = None
                else:
                    values[qid][dimension] = min(scores)
            bound.extend(r['review_id'] for r in humans)
        quality = dict(critical=critical, incomplete=sorted(set(incomplete)), values=values,
            subjects={q: s[0] for q, s in subjects.items()}, review_ids=sorted(bound))
        # 无追加记录时保留旧校准结构，已冻结的历史证明不因升级无条件失效。
        if followup_ids:
            quality['followup_ids'] = followup_ids
        return experiment, quality

    def calibrate(self, user, eid, data):
        identity = fingerprint({'experiment_id': eid, **data.model_dump()})
        prior = self.calibrations.find_one({'owner_id': user.user_id, 'client_request_id': data.client_request_id})
        self.repo.get_experiment(user, eid)
        if prior:
            if prior['request_sha256'] != identity:
                raise APIError(409, 'idempotency_conflict', '校准请求已绑定其他内容。')
            return public(prior)
        experiment, quality = self._quality(user, eid)
        if quality['incomplete'] or quality['critical']:
            raise APIError(409, 'human_review_required', '基线需要完整两轮人工原件核对，且无关键错误和未知维度。')
        row = dict(calibration_id=str(uuid4()), experiment_id=eid, owner_id=user.user_id,
            kb_id=experiment['kb_id'], dataset_sha256=experiment['dataset_sha256'],
            manifest_sha256=experiment['manifest_sha256'], baseline=quality, tolerance=0,
            created_at=datetime.now(timezone.utc).isoformat(), request_sha256=identity, **data.model_dump())
        try:
            self.calibrations.insert_one(row)
        except DuplicateKeyError:
            return self.calibrate(user, eid, data)
        return public(row)

    def gate(self, user, eid, calibration_id):
        experiment, current = self._quality(user, eid)
        calibration = self.calibrations.find_one({'calibration_id': calibration_id, 'owner_id': user.user_id,
                                                  'kb_id': {'$in': list(user.kb_ids)}})
        if calibration is None:
            raise APIError(404, 'not_found', '校准不存在或不在授权范围。')
        baseline, live_baseline = self._quality(user, calibration['experiment_id'])
        reasons = []
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
        return dict(status=status, reasons=sorted(set(reasons)), regressions=regressions,
                    calibration_id=calibration_id, candidate_experiment_id=eid,
                    human_review_count=len(current['review_ids']), automatic_publish=False)
