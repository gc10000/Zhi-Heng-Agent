"""M4-R1正式回归（源自总控满池反例）：正式入口，真实隔离Mongo，模型和索引端口注入，付费0。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.integration.conftest import mongo_db
from tests.integration.test_run_claim import run_context, request
from tests.integration.test_query_runs import query_context
from tests.integration.test_query_planning import planning_context

pytestmark = pytest.mark.integration


def quality_inputs(g, question, runner, tmp_path, rank):
    """使用同一真实隔离知识注册表，标准标签仅在末端计分。"""
    from app.evaluation.quality_grid import QualityExecutor, StageCache
    from app.evaluation.strategy import EvaluationStrategy
    from tests.unit.test_evaluation_dataset import case
    documents=[dict(document_id=d['document_id'],revision_id=d['active_revision_id'],original_sha256='a'*64)
        for d in g.repo('k').documents.find({})]
    config=dict(target=dict(kb_id='k'),corpus=dict(documents=documents,snapshot=dict(documents=[])))
    executor=QualityExecutor(config,g,embedder=runner.embedder,ranker=rank,
        cache=StageCache(tmp_path/'stage-cache','synthetic-scope'),hyde=lambda *a:'合成检索假设')
    q=case();q.update(question=question,product_names=[],history=[])
    return executor.execute(q,EvaluationStrategy(enhancement=runner.enhancement_policy).model_dump())


@pytest.mark.parametrize('question',['比较AX-24和AX-48的供电要求。','比较AX-48和AX-24的供电要求。'])
def test_full_first_product_must_not_exclude_second_product_from_rerank(planning_context,tmp_path,question):
    ctx, a, b, _ = planning_context
    user, cid, conv, repo, service, g, runner, first, _ = ctx
    documents = list(g.repo('k').documents.find({}))
    by_product = {d['product_ids'][0]: d for d in documents}
    seen = []
    class Index:
        def search(self, scoped, text, **kw):
            pid = kw['product_ids'][0]
            doc = by_product[pid]
            result = []
            for i in range(kw['limit']):
                row = deepcopy(first)
                row.update(chunk_uid=pid + '-' + str(i), document_id=doc['document_id'],
                    revision_id=doc['active_revision_id'], text=('甲型24V' if pid == a['product_id'] else '乙型48V'))
                row['metadata']['product_ids'] = [pid]
                for ref in row['metadata']['source_refs']:
                    ref.update(document_id=row['document_id'], revision_id=row['revision_id'])
                result.append(dict(entity=row))
            return result
    g.index_factory = Index
    def rank(q, docs):
        seen.extend(docs)
        return [d|dict(score=.8) for d in sorted(docs, key=lambda d: d['text'] != '乙型48V')]
    runner.ranker = rank
    rid = service.create(user, cid, request(question=question))['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    observed = {p for d in seen for p in d['metadata']['product_ids']}
    assert row['state'] == 'completed'
    assert observed == {a['product_id'], b['product_id']}, '两个型号各召回20条，但重排输入只含先拼接型号'
    formal=deepcopy(seen);seen.clear()
    result=quality_inputs(g,question,runner,tmp_path,rank)
    assert result['stage_counts']['reranked']==len(seen)==20
    assert result['rerank_inputs']==[[d['document_id'],d['revision_id'],d['chunk_uid']] for d in seen]
    assert [(d['document_id'],d['chunk_uid']) for d in seen]==[(d['document_id'],d['chunk_uid']) for d in formal]


@pytest.mark.parametrize('branch', ['hyde', 'decomposition'])
def test_completed_enhancement_unique_evidence_reaches_rerank(query_context, branch,tmp_path):
    user, cid, conv, repo, service, g, runner, first, product = query_context
    seen = []
    runner.enhancement_policy = {branch + '_enabled': True}
    class Index:
        def search(self, scoped, text, **kw):
            derived = ('检索假设：' in text) if branch == 'hyde' else ('现象：' in text)
            if derived:
                return [dict(entity=deepcopy(first) | dict(chunk_uid='unique-enhancement', text='新增关键真实证据24V'))]
            return [dict(entity=deepcopy(first) | dict(chunk_uid='local-' + str(i))) for i in range(kw['limit'])]
    g.index_factory = Index
    def rank(q, docs):
        seen.extend(docs)
        return [d|dict(score=.8) for d in sorted(docs, key=lambda d: d['chunk_uid'] != 'unique-enhancement')]
    runner.ranker = rank
    class Model:
        def invoke(self, prompt, **kw): return SimpleNamespace(content='合成检索假设')
        def stream(self, prompt, **kw): yield SimpleNamespace(content='输入24V。')
    runner.llm_factory = Model
    rid = service.create(user, cid, request(question='AX-24无法启动；同时指示灯不亮'))['run_id']
    runner.execute(rid)
    row = repo.get(user, rid)
    status = next(b['status'] for b in row['retrieval_branches'] if b['name'] == branch)
    assert row['state'] == 'completed' and status == 'completed'
    assert any(d['chunk_uid'] == 'unique-enhancement' for d in seen), '成功增强新增候选在重排前被顺序截断'
    formal=deepcopy(seen);seen.clear()
    result=quality_inputs(g,'AX-24无法启动；同时指示灯不亮',runner,tmp_path,rank)
    assert result['stage_counts']['reranked']==len(seen)==20
    assert result['rerank_inputs']==[[d['document_id'],d['revision_id'],d['chunk_uid']] for d in seen]
    assert [(d['document_id'],d['chunk_uid']) for d in seen]==[(d['document_id'],d['chunk_uid']) for d in formal]
