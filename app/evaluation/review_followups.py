"""未知项追加复核；原审阅不可变，每条原审阅只允许一个并发胜出的结论。"""
from copy import deepcopy
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.knowledge.repository import fingerprint
from app.answering.image_selection import has_review_images

Dimension = Literal['factuality', 'citation_support', 'actionability', 'image_relevance']


class Resolution(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    score: Literal[0, 1, 2, 'not_applicable']
    evidence: str = Field(min_length=1, max_length=4000)

    @field_validator('score', mode='before')
    @classmethod
    def exact_score(cls, value):
        if (type(value) is int and value in (0, 1, 2)) or (type(value) is str and value == 'not_applicable'):
            return value
        raise ValueError('追加结论只接受整数0/1/2或not_applicable；未核实请保留旧未知')

    @field_validator('evidence')
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError('每个追加维度必须单独说明原件依据或不适用原因')
        return value


class FollowupInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)
    subject_sha256: str = Field(pattern=r'^[0-9a-f]{64}$')
    client_request_id: str = Field(min_length=1, max_length=128)
    human_attested: bool
    source_checked: bool
    resolutions: dict[Dimension, Resolution] = Field(min_length=1, max_length=4)
    critical_errors: list[Literal['unauthorized', 'wrong_model']] = Field(default_factory=list, max_length=2)

    @model_validator(mode='after')
    def actual_human(self):
        if not (self.human_attested and self.source_checked):
            raise ValueError('追加复核须由原审核者本人重新核对原件并声明')
        if self.resolutions.get('factuality') and self.resolutions['factuality'].score == 'not_applicable':
            raise ValueError('事实维度不能不适用')
        return self


class FollowupLedger:
    def __init__(self, db):
        self.rows = db.evaluation_review_followups
        self.rows.create_index([('experiment_id', 1), ('review_id', 1)], unique=True)
        self.rows.create_index([('owner_id', 1), ('client_request_id', 1)], unique=True)

    def append(self, user, eid, original, data, result):
        if original['reviewer_kind'] != 'human' or not (original['human_attested'] and original['source_checked']):
            raise APIError(409, 'human_review_required', '只能追加本人已核对原件的人工审阅。')
        unknown = {key for key, value in original['scores'].items() if value == 'unknown'}
        if not unknown:
            raise APIError(409, 'review_has_no_unknown', '原审阅没有未知项，不能借追加改变确定结论。')
        if set(data.resolutions) != unknown:
            raise APIError(422, 'review_resolution_dimensions', '须逐项解决该轮全部未知项；确定维度不能修改。')
        image = data.resolutions.get('image_relevance')
        action = data.resolutions.get('actionability')
        if (action and original.get('rubric_version') == 'question-purpose-v1' and
                ((action.score == 'not_applicable') == original['actionability_applicable'])):
            raise APIError(422, 'review_applicability_changed', '追加未知结论不能改变原审阅按题意确定的步骤适用性；须保留原规则。')
        if image and image.score == 'not_applicable' and has_review_images(result):
            raise APIError(422, 'image_review_required', '含配图来源须核对用途与相关性，不能直接跳过图片。')
        identity = fingerprint(dict(experiment_id=eid, review_id=original['review_id'], **data.model_dump()))
        row = dict(experiment_id=eid, review_id=original['review_id'],
                   question_id=original['question_id'], round=original['round'], reviewer_kind='human',
                   owner_id=user.user_id, reviewer_id=user.user_id, followup_id=str(uuid4()),
                   original_sha256=fingerprint(original), request_sha256=identity,
                   created_at=datetime.now(timezone.utc).isoformat(), **data.model_dump())
        try:
            self.rows.insert_one(row)
        except DuplicateKeyError:
            prior = self.rows.find_one({'owner_id': user.user_id, 'client_request_id': data.client_request_id})
            if not prior or prior['request_sha256'] != identity:
                raise APIError(409, 'review_followup_conflict', '该轮已有追加结论或请求标识冲突，请刷新查看；历史不可覆盖。') from None
            return prior
        return row

    def effective(self, originals, followups):
        """只覆盖有完整合法溯源的未知项，保留原记录及全部关键错误。"""
        by_id = {r['review_id']: r for r in followups}
        effective, bound = [], []
        for original in originals:
            row = deepcopy(original)
            followup = by_id.get(row['review_id'])
            if (followup and row['reviewer_kind'] == 'human' and
                    followup['reviewer_id'] == row['reviewer_id'] and
                    followup.get('owner_id') == row.get('owner_id') and
                    followup.get('reviewer_kind') == 'human' and
                    followup.get('human_attested') is True and followup.get('source_checked') is True and
                    followup['subject_sha256'] == row['subject_sha256'] and
                    followup['original_sha256'] == fingerprint(original) and
                    {key for key, value in row['scores'].items() if value == 'unknown'} == set(followup['resolutions']) and
                    all(value.get('score') in (0, 1, 2, 'not_applicable') and
                        isinstance(value.get('evidence'), str) and value['evidence'].strip()
                        for value in followup['resolutions'].values())):
                for key, value in followup['resolutions'].items():
                    row['scores'][key] = value['score']
                row['critical_errors'] = sorted(set(row['critical_errors'] + followup['critical_errors']))
                bound.append(followup['followup_id'])
            effective.append(row)
        return effective, sorted(bound)
