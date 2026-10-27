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


def test_answer_image_usage_survives_formal_adapter_and_result_storage(evaluation_context):
    from app.evaluation.repository import EvaluationRepository
    cfg,factory,resources,prompts,question,scoped=evaluation_context
    g=resources['knowledge']()
    entity=g.index_factory().search()[0]['entity']
    entity['metadata']['asset_ids']=['diagram']
    g.db.knowledge_assets.insert_one(dict(asset_id='diagram',document_id=entity['document_id'],
        revision_id=entity['revision_id'],sha256='b'*64,source_refs=[dict(kind='pdf',page=2)]))
    with RealQueryExecutor(cfg,resource_factory=factory) as execute:
        result=execute(question)
    images=[c for c in result['citations'] if c.get('asset_sha256')]
    assert images and images[0]['image_usage']=='context'
    assert result['image_selection_version']==1
    repo=EvaluationRepository(g.db)
    repo.save_results('adapter-new',1,[question|{'category':'parameter'}],[dict(id='q1',status='completed',result=result)])
    stored=repo.results.find_one({'experiment_id':'adapter-new'})['result']
    assert stored['image_selection_version']==1 and stored['citations']==result['citations']


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


def test_validated_candidate_can_be_evaluated_without_changing_active_pointer(evaluation_context):
    cfg, factory, resources, prompts, question, scoped = evaluation_context
    from copy import deepcopy
    original = cfg['corpus']['documents'][0]
    candidate = scoped.create_revision(original['document_id'], 'candidate', original_sha256='a'*64, object_key='m4-test/adapter/candidate')
    validation = {'fixture': 'validated-candidate'}
    scoped.revisions.update_one({'revision_id':candidate.revision_id},{'$set':{'status':'validated','validation':validation}})
    cfg['metric_schema_version'] = 1
    cfg['corpus']['documents'][0] = dict(original, revision_id=candidate.revision_id)
    cfg['corpus']['candidate_revisions'] = [dict(document_id=original['document_id'], revision_id=candidate.revision_id, expected_active_revision_id=original['revision_id'], validation=validation)]
    gateway=resources['knowledge']()
    from types import SimpleNamespace
    gateway.publisher=lambda kb:SimpleNamespace(inspect=lambda r:validation)
    old_factory=gateway.index_factory
    class CandidateIndex:
        def search(self,*args,**kw):
            rows=deepcopy(old_factory().search(*args,**kw))
            for row in rows:
                row['entity']['revision_id']=candidate.revision_id
                for ref in row['entity']['metadata']['source_refs']:ref['revision_id']=candidate.revision_id
            return rows
    gateway.index_factory=CandidateIndex
    with RealQueryExecutor(cfg,resource_factory=factory) as execute:
        result=execute(question)
    assert result['state']=='completed' and result['citations'][0]['revision_id']==candidate.revision_id
    assert scoped.get_document(original['document_id'])['active_revision_id']==original['revision_id']
    assert scoped.get_revision(candidate.revision_id)['status']=='validated'


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


def test_m6_full_query_preserves_ranked_source_identity_without_candidate_text(evaluation_context):
    cfg, factory, resources, prompts, question, _ = evaluation_context
    cfg['metric_schema_version'] = 1
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        result = execute(question)
    assert set(result.get('retrieval_candidates', {})) == {'candidates', 'reranked', 'context'}
    for stage in result['retrieval_candidates'].values():
        assert len(stage) == 1 and stage[0]['sources'][0]['document_sha256'] == 'a'*64
        assert stage[0]['sources'][0]['page'] == 2
        assert set(stage[0]) == {'candidate_id', 'sources'}


def test_actual_query_records_usage_and_resumes_without_extra_calls(evaluation_context):
    from types import SimpleNamespace
    cfg,factory,resources,prompts,question,_=evaluation_context
    cfg['metric_schema_version']=1
    class Measured:
        model_name='synthetic-model'
        def stream(self,*args,**kwargs):
            prompts.append('合成测试调用')
            yield SimpleNamespace(content='24 V。',usage_metadata={'input_tokens':9,'output_tokens':3})
    resources['query_runner'].llm_factory=Measured
    with RealQueryExecutor(cfg,resource_factory=factory) as execute:
        result=execute(question)
        again=execute(question)
    assert result['token_usage']=={'input':9,'output':3}
    assert result==again and len(prompts)==1
    row=resources['runs'].runs.find_one({'run_id':result['run_id']})
    assert row['telemetry']['logical_provider_calls']=={'invoke_started':0,'stream_started':1}
    assert row['telemetry']['models']==['synthetic-model']


def test_explicit_m6_failed_question_retry_creates_one_new_run_then_reuses_it(evaluation_context):
    from app.infrastructure.providers.policy import ProviderFailure
    cfg, factory, resources, prompts, question, _ = evaluation_context
    cfg['metric_schema_version'] = 1
    original = resources['query_runner'].llm_factory
    class Failing:
        def stream(self, *args, **kwargs): raise ProviderFailure('upstream_timeout', True)
    resources['query_runner'].llm_factory = Failing
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        with pytest.raises(ProviderFailure): execute(question)
    resources['query_runner'].llm_factory = original
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        execute.retry_key = 'explicit-retry-one'
        result = execute(question)
        again = execute(question)
    assert result == again and result['state'] == 'completed'
    assert len(prompts) == 1 and resources['runs'].runs.count_documents({}) == 2


def test_explicit_m6_followup_after_interrupted_run_creates_one_new_run_then_reuses_it(evaluation_context):
    from datetime import datetime, timedelta, timezone
    cfg, factory, resources, prompts, question, _ = evaluation_context
    cfg['metric_schema_version'] = 1
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        original = execute(question)
    resources['runs'].runs.update_one({'run_id': original['run_id']}, {'$set': {
        'state': 'running', 'execution_token': 'expired-worker-token',
        'execution_lease': datetime.now(timezone.utc) - timedelta(seconds=1)}, '$inc': {'version': 1}})
    recovered = resources['commands'].recover()
    interrupted = resources['runs'].runs.find_one({'run_id': original['run_id']})
    assert original['run_id'] in recovered and interrupted['state'] == 'interrupted'

    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        with pytest.raises(ValueError):
            execute(question)
    assert len(prompts) == 1 and resources['runs'].runs.count_documents({}) == 1

    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        execute.retry_key = 'followup-from-source-experiment'
        followup = execute(question)
        repeated = execute(question)
    assert followup['run_id'] != original['run_id']
    assert followup == repeated and followup['state'] == 'completed'
    assert len(prompts) == 2 and resources['runs'].runs.count_documents({}) == 2
    assert resources['runs'].runs.find_one({'run_id': original['run_id']})['state'] == 'interrupted'


def test_explicit_m6_followup_does_not_retry_nonretryable_failed_run(evaluation_context):
    from app.infrastructure.providers.policy import ProviderFailure
    cfg, factory, resources, prompts, question, _ = evaluation_context
    cfg['metric_schema_version'] = 1
    class InvalidResponse:
        def stream(self, *args, **kwargs):
            raise ProviderFailure('provider_invalid_response', False)
    resources['query_runner'].llm_factory = InvalidResponse
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        with pytest.raises(ProviderFailure) as error:
            execute(question)
    assert error.value.retryable is False
    resources['query_runner'].llm_factory = lambda: InvalidResponse()
    with RealQueryExecutor(cfg, resource_factory=factory) as execute:
        execute.retry_key = 'followup-from-source-experiment'
        with pytest.raises(ProviderFailure) as followup_error:
            execute(question)
    assert followup_error.value.retryable is False
    assert prompts == [] and resources['runs'].runs.count_documents({}) == 1
