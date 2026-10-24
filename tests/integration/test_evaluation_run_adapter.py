"""真实独立Mongo + 正式QueryRunner；检索/模型端口注入，不计供应商验证。"""
from contextlib import contextmanager
from types import SimpleNamespace
import pytest
from app.evaluation.query_adapter import RealQueryExecutor
from app.identity.models import Principal
from app.knowledge.gateway import KnowledgeGateway
from app.knowledge.api import ProductInput
from app.conversations.repository import ConversationRepository
from app.runs.repository import RunRepository
from app.runs.service import RunService
from app.runs.events import EventLedger
from app.runs.commands import RunCommands
from app.runs.query_runner import QueryRunner

pytestmark = pytest.mark.integration


@pytest.fixture
def evaluation_context(mongo_db):
    owner, kb = 'm4-test-owner', 'm4-test-kb'
    user = Principal(user_id=owner, username='隔离验证', role='maintainer', kb_ids=(kb,))
    conv = ConversationRepository(mongo_db); repo = RunRepository(mongo_db, conv)
    g = KnowledgeGateway(mongo_db, None, owner_id=owner)
    product = g.add_product(user, kb, ProductInput(kb_id=kb, model='AX'))
    scoped = g.repo(kb)
    doc = scoped.register_document('one', name='合成参数手册', product_ids=[product['product_id']])
    revision = scoped.create_revision(doc.document_id, 'one', original_sha256='a'*64, object_key='m4-test/adapter/source')
    scoped.revisions.update_one({'revision_id': revision.revision_id}, {'$set': {'status': 'published'}})
    scoped.documents.update_one({'document_id': doc.document_id}, {'$set': {'active_revision_id': revision.revision_id}})
    entity = {'chunk_uid': 'source', 'document_id': doc.document_id, 'revision_id': revision.revision_id,
              'text': '额定电压为24 V', 'metadata': {'heading_path': [], 'asset_ids': [],
              'source_refs': [{'kind': 'pdf', 'page': 2, 'document_id': doc.document_id, 'revision_id': revision.revision_id}]}}
    class Index:
        def search(self, *args, **kwargs): return [{'entity': entity}]
    g.index_factory = Index
    prompts = []
    class Model:
        def stream(self, prompt, **options):
            prompts.append(prompt)
            yield SimpleNamespace(content='额定电压为24 V。')
    commands = RunCommands(repo, EventLedger(repo))
    runner = QueryRunner(repo, commands, lambda: g, ranker=lambda q, d: d, llm_factory=Model)
    resources = {'db': mongo_db, 'conversations': conv, 'runs': repo, 'run_service': RunService(repo),
                 'commands': commands, 'query_runner': runner, 'knowledge': lambda: g}
    @contextmanager
    def factory(config): yield resources
    cfg = {'experiment_id': 'baseline', 'strategy': 'm3-baseline', 'dataset_sha256': 'a'*64,
           'target': {'database': mongo_db.name, 'collection': 'm1_test_m4_adapter_v2', 'owner_id': owner, 'kb_id': kb,
                      'object_prefix': 'm4-test/adapter/', 'bucket': 'existing'},
           'corpus': {'documents': [{'document_id': doc.document_id, 'revision_id': revision.revision_id, 'original_sha256': 'a'*64}]}}
    question = {'id': 'q1', 'question': '它的额定电压是多少？', 'product_names': ['AX'],
                'history': [{'role': 'user', 'text': '我使用AX'}, {'role': 'assistant', 'text': '已明确型号AX'}],
                'expected': {'key_points': ['绝不能传入模型的判分标签']}}
    yield cfg, factory, resources, prompts, question, scoped
    runner.close()


def test_formal_run_persists_history_sources_and_never_injects_labels(evaluation_context):
    cfg, factory, resources, prompts, question, scoped = evaluation_context
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        result = execute(question)
    assert result['state'] == 'completed' and result['answer'] == '额定电压为24 V。'
    assert result['citations'][0]['document_sha256'] == 'a'*64 and result['citations'][0]['page'] == 2
    assert '已明确型号AX' in prompts[0] and '绝不能传入模型的判分标签' not in prompts[0]
    rows = list(resources['conversations'].messages.find().sort('ordinal', 1))
    assert [r['role'] for r in rows] == ['user', 'assistant', 'user', 'assistant']


def test_reconstructed_executor_reuses_completed_run_without_model_call(evaluation_context):
    cfg, factory, resources, prompts, question, scoped = evaluation_context
    with RealQueryExecutor(cfg, resource_factory=factory) as execute: first = execute(question)
    with RealQueryExecutor(cfg, resource_factory=factory) as execute: second = execute(question)
    assert first == second and len(prompts) == 1 and resources['runs'].runs.count_documents({}) == 1


def test_changed_active_corpus_rejected_before_generation(evaluation_context):
    cfg, factory, resources, prompts, question, scoped = evaluation_context
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        scoped.documents.update_one(scoped.scope, {'$set': {'active_revision_id': None}})
        with pytest.raises(ValueError): execute(question)
    assert prompts == [] and resources['runs'].runs.count_documents({}) == 0


def test_configured_strategy_controls_real_execution_ports_and_budget(evaluation_context):
    cfg,factory,resources,prompts,question,_=evaluation_context
    cfg.update(strategy='m4-configured',parameters=dict(retrieval=dict(fusion='rrf'),answer_budget=dict(output_tokens=128)))
    gateway=resources['knowledge']();original=gateway.index_factory;seen=[]
    class CapturedIndex:
        def search(self,*args,**kwargs):
            seen.append(kwargs)
            return original().search(*args,**kwargs)
    gateway.index_factory=CapturedIndex
    with RealQueryExecutor(cfg,resource_factory=factory) as execute:
        result=execute(question)
    assert result['state']=='completed' and result['answer']=='额定电压为24 V。'
    assert seen and all(row['policy']['fusion']=='rrf' for row in seen)
    assert result['prompt_budget']['policy']['output_tokens']==128
    assert len(prompts)==1 and result['citations']
