"""冻结实验参数必须真实接入已实现策略，禁止静默忽略或越界。"""
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.retrieval.search import RetrievalPolicy
from app.retrieval.expansion import ExpansionPolicy
from app.retrieval.routing import EnhancementPolicy
from app.answering.service import AnswerBudget
from app.lm.runtime import ModelRuntimePolicy
from app.retrieval.prerequisites import SourcePrerequisitePolicy
from app.retrieval.combination import CombinationPolicy,validate_policies


class EvaluationStrategy(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    retrieval:RetrievalPolicy=Field(default_factory=RetrievalPolicy)
    expansion:ExpansionPolicy=Field(default_factory=ExpansionPolicy)
    enhancement:EnhancementPolicy=Field(default_factory=EnhancementPolicy)
    answer_budget:AnswerBudget=Field(default_factory=AnswerBudget)
    runtime:ModelRuntimePolicy=Field(default_factory=ModelRuntimePolicy)
    source_prerequisites:SourcePrerequisitePolicy=Field(default_factory=SourcePrerequisitePolicy)
    retrieval_combination:CombinationPolicy=Field(default_factory=CombinationPolicy)

    @model_validator(mode="after")
    def combination_bounds(self):
        validate_policies(self.retrieval_combination,self.retrieval,self.source_prerequisites,self.expansion,self.enhancement)
        return self


def strategy_policies(config):
    if config['strategy']=='m3-baseline':
        if config.get('parameters'):raise ValueError('原链路基线不接受策略覆盖')
        return EvaluationStrategy()
    if config['strategy']!='m4-configured':raise ValueError('未知评测策略，不能忽略参数')
    return EvaluationStrategy.model_validate(config.get('parameters',{}))


def validate_combination_config(config,policies=None):
    """目标/语料快照身份必须与内部策略一致，先于任何持久写入。"""
    from app.knowledge.repository import fingerprint
    combo=(policies or strategy_policies(config)).retrieval_combination
    if not combo.enabled:return
    t=config['target'];corpus=config.get('corpus',{})
    if (any(t.get(k)!=getattr(combo.scope,k) for k in ('owner_id','kb_id','database','collection')) or
            {d['document_id']:d['revision_id'] for d in corpus.get('documents',[])}!=combo.scope.revisions or
            not corpus.get('snapshot') or fingerprint(corpus['snapshot'])!=combo.corpus_snapshot_sha256):
        raise ValueError('内部组合与实验目标/冻结语料快照不同')
