"""冻结实验参数必须真实接入已实现策略，禁止静默忽略或越界。"""
from pydantic import BaseModel,ConfigDict,Field
from app.retrieval.search import RetrievalPolicy
from app.retrieval.expansion import ExpansionPolicy
from app.retrieval.routing import EnhancementPolicy
from app.answering.service import AnswerBudget
from app.lm.runtime import ModelRuntimePolicy
from app.retrieval.prerequisites import SourcePrerequisitePolicy


class EvaluationStrategy(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    retrieval:RetrievalPolicy=Field(default_factory=RetrievalPolicy)
    expansion:ExpansionPolicy=Field(default_factory=ExpansionPolicy)
    enhancement:EnhancementPolicy=Field(default_factory=EnhancementPolicy)
    answer_budget:AnswerBudget=Field(default_factory=AnswerBudget)
    runtime:ModelRuntimePolicy=Field(default_factory=ModelRuntimePolicy)
    source_prerequisites:SourcePrerequisitePolicy=Field(default_factory=SourcePrerequisitePolicy)


def strategy_policies(config):
    if config['strategy']=='m3-baseline':
        if config.get('parameters'):raise ValueError('原链路基线不接受策略覆盖')
        return EvaluationStrategy()
    if config['strategy']!='m4-configured':raise ValueError('未知评测策略，不能忽略参数')
    return EvaluationStrategy.model_validate(config.get('parameters',{}))
