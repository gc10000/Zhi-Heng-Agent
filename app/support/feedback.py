"""反馈只入待审账本，不自动发布知识或发送给外部人员。"""
from copy import deepcopy
from typing import Literal
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.knowledge.models import stable_id
from app.knowledge.repository import fingerprint
from app.conversations.repository import public
from .repository import now


class FeedbackInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    run_id: str = Field(min_length=1,max_length=128)
    citation_ids: list[str] = Field(default_factory=list,max_length=20)
    category: Literal['model','evidence','missing_material','operation','image']
    note: str = Field(min_length=1,max_length=4000)
    client_request_id: str = Field(min_length=1,max_length=128)


def save_feedback(db, user, run, data):
    if not data.note.strip() or len(set(data.citation_ids)) != len(data.citation_ids):
        raise APIError(422,'invalid_feedback','请填写反馈，引用不能重复。')
    selected = {c['citation_id']:c for c in run.get('citations',[])}
    if not set(data.citation_ids) <= selected.keys():
        raise APIError(422,'invalid_citation','反馈引用必须属于当前运行。')
    collection = db.support_feedback
    collection.create_index('feedback_id',unique=True)
    identity = fingerprint(data.model_dump())
    feedback_id = stable_id('feedback',user.user_id,[data.client_request_id])
    row = {'feedback_id':feedback_id,'identity':identity,'owner_id':user.user_id,'kb_id':run['kb_id'],
           'run_id':run['run_id'],'conversation_id':run['conversation_id'],'category':data.category,
           'note':data.note.strip(),'citations':[deepcopy(selected[c]) for c in data.citation_ids],
           'state':'pending_review','recorded_at':now(),'source':'user_feedback'}
    try:
        collection.insert_one(row)
    except DuplicateKeyError:
        pass
    saved = collection.find_one({'feedback_id':feedback_id,'owner_id':user.user_id})
    if saved['identity'] != identity:
        raise APIError(409,'idempotency_conflict','相同反馈标识的内容不同。')
    return public(saved)
