"""运行请求标识与持久状态；幂等键不复用消息或会话ID。"""
from pydantic import BaseModel, ConfigDict, Field
from app.retrieval.prerequisites import SourcePrerequisitePolicy
from app.retrieval.combination import CombinationPolicy
from app.answering.evidence_attribution import EvidenceAttributionPolicy

TERMINAL = frozenset({'completed', 'failed', 'cancelled', 'interrupted'})
ACTIVE = frozenset({'pending', 'running', 'awaiting_input', 'cancel_requested'})


class RunInput(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=32000)
    client_request_id: str = Field(min_length=1, max_length=128)
    kb_id: str = Field(min_length=1, max_length=128)
    product_ids: list[str] = Field(default_factory=list, max_length=50)


class InternalRunInput(RunInput):
    """只供受信执行器构造，不作为HTTP请求模型；配置参与幂等身份。"""
    source_prerequisites: SourcePrerequisitePolicy | None = None
    retrieval_combination: CombinationPolicy | None = None
    evidence_attribution: EvidenceAttributionPolicy | None = None


def snapshot(row):
    """仅公开运行快照，内部领取、事件outbox不传给浏览器。"""
    keys = ('run_id', 'conversation_id', 'message_id', 'assistant_message_id', 'client_request_id',
            'kb_id', 'state', 'version', 'question', 'product_snapshot', 'created_at', 'answer',
            'citations', 'error', 'stage', 'candidates', 'resume_point', 'seq')
    return {k: row[k] for k in keys if k in row}
