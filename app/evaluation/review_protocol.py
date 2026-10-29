"""步骤适用性规则与聊天来源账本；转录记录不构成人工评分。"""
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.knowledge.repository import fingerprint


class Applicability(BaseModel):
    rubric_version: Literal['legacy-v1', 'question-purpose-v1'] = 'legacy-v1'
    actionability_applicable: bool | None = None
    applicability_rationale: str | None = Field(default=None, min_length=1, max_length=4000)

    @model_validator(mode='after')
    def purpose_rule(self):
        if self.rubric_version == 'legacy-v1':
            if self.actionability_applicable is not None or self.applicability_rationale is not None:
                raise ValueError('旧规则不能隐式补写新版适用性')
        else:
            if self.actionability_applicable is None or not (self.applicability_rationale or '').strip():
                raise ValueError('新版须按题意明确步骤是否适用并填写理由，未确定请保留旧规则和未知')
            score = self.scores.actionability
            if (not self.actionability_applicable and score != 'not_applicable') or (
                    self.actionability_applicable and score == 'not_applicable'):
                raise ValueError('步骤适用性与评分不一致')
        return self


def review_dump(data):
    values = data.model_dump()
    # 保持旧请求的精确指纹和旧校准结构，历史重试仍幂等。
    if data.rubric_version == 'legacy-v1':
        for key in ('rubric_version', 'actionability_applicable', 'applicability_rationale'):
            values.pop(key, None)
    if values.get('observation_id') is None:
        values.pop('observation_id', None)
    if values.get('quality_policy') is None:
        for key in ('quality_policy','review_execution_id','dimension_evidence'): values.pop(key,None)
    return values


class ObservationLedger:
    def __init__(self, db):
        self.rows = db.evaluation_observations
        self.rows.create_index('observation_id', unique=True)
        # 一条消息不能借不同轮次、题目或实验复制为独立意见。
        self.rows.create_index([('owner_id', 1), ('source_message_id', 1)], unique=True)

    def append(self, user, eid, data):
        fields = data.model_dump()
        identity = fingerprint(dict(experiment_id=eid, **fields))
        row = dict(observation_id=str(uuid4()), experiment_id=eid, owner_id=user.user_id,
            transcriber_id=user.user_id, transcriber_kind='assistant', source_channel='chat',
            statement_sha256=fingerprint(data.statement), request_sha256=identity,
            created_at=datetime.now(timezone.utc).isoformat(), **fields)
        try:
            self.rows.insert_one(row)
        except DuplicateKeyError:
            old = self.rows.find_one({'owner_id': user.user_id, 'source_message_id': data.source_message_id})
            if not old or old['request_sha256'] != identity:
                raise APIError(409, 'observation_conflict', '聊天来源已绑定其他内容；历史反馈不可覆盖或复制。') from None
            return old
        return row

    def require_reference(self, user, eid, data):
        if not data.observation_id:
            return
        if self.rows.find_one(dict(observation_id=data.observation_id, owner_id=user.user_id,
                experiment_id=eid, question_id=data.question_id, subject_sha256=data.subject_sha256)) is None:
            raise APIError(409, 'observation_subject_mismatch', '聊天依据必须属于当前结果与当前维护者。')
