"""独立Mongo验证正式入口父块扩展，模型/检索端口均注入。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.integration.test_run_claim import run_context, request
from tests.integration.test_query_runs import query_context

pytestmark = pytest.mark.integration


def test_parent_prerequisite_reaches_actual_prompt_and_persistent_citations(query_context):
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    runner.expansion_policy = dict(enabled=True, max_chars=6000, max_added=4)
    child = deepcopy(entity) | dict(ordinal=1)
    child['metadata'].update(section_id='s', product_ids=[product['product_id']], parent_chunk_uid='parent')
    parent = deepcopy(child) | dict(chunk_uid='parent', ordinal=0, text='前提：必须先断电，再检查接线。')
    parent['metadata']['parent_chunk_uid'] = None
    class Index:
        def search(self, *a, **kw): return [dict(entity=child)]
        def related_rows(self, scoped, seeds, **kw):
            assert scoped.owner_id == 'organization' and scoped.kb_id == 'k'
            return [parent | dict(owner_id='organization', kb_id='k')]
    g.index_factory = Index
    prompts = []
    class Model:
        def stream(self, prompt):
            prompts.append(prompt); yield SimpleNamespace(content='断电后检查，输入电源为24V。')
    runner.llm_factory = Model
    rid = service.create(user, cid, request())['run_id']; runner.execute(rid)
    row = repo.get(user, rid)
    assert row['state'] == 'completed'
    assert '必须先断电' in prompts[0], '不能只检索到后半块就丢失父块前提'
    assert {c['chunk_uid'] for c in row['citations']} == {'chunk-one', 'parent'}
    assert any(t['chunk_uid'] == 'parent' and t['selected'] for t in row['retrieval_trace'])
    messages = conv.history(user, cid)['items']
    assert messages[-1]['citations'] == row['citations']


def test_wrong_scope_expansion_fails_run_without_success_message(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    runner.expansion_policy=dict(enabled=True)
    seed=deepcopy(entity)|dict(ordinal=1)
    seed['metadata'].update(section_id='s',product_ids=[product['product_id']])
    class Index:
        def search(self,*a,**kw):return [dict(entity=seed)]
        def related_rows(self,*a,**kw):return [seed|dict(owner_id='other',kb_id='k')]
    g.index_factory=Index
    rid=service.create(user,cid,request())['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='failed' and row['error']['stage']=='rerank'
    assert conv.messages.count_documents(dict(run_id=rid,role='assistant'))==0
    assert not any(e['type']=='run.completed' for e in runner.events.read(user,rid))


def test_real_milvus_related_lookup_keeps_bounds_and_sources(mongo_db):
    import os
    from uuid import uuid4
    from pymilvus import MilvusClient
    from app.knowledge.index import V2Index
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.models import Chunk,SourceRef
    from app.retrieval.adapters import from_index_hits
    client=MilvusClient(uri=os.environ['MILVUS_URL'])
    index=V2Index(client,'m1_test_m4_related_'+uuid4().hex,dense_dim=2)
    scoped=KnowledgeRepository(mongo_db,owner_id='owner',kb_id='kb')
    try:
        index.ensure_collection()
        doc=scoped.register_document('source',name='合成表格资料')
        rev=scoped.create_revision(doc.document_id,'v1',original_sha256='a'*64,object_key='m4-test/related/source')
        attempt=scoped.claim_attempt(rev.revision_id,expected_attempt=0)
        chunks=[Chunk(chunk_uid=uuid4().hex,document_id=doc.document_id,revision_id=rev.revision_id,
            section_id='s',ordinal=i,text='表头与数据'+str(i),product_ids=('AX',) if i!=2 else ('BX',),
            source_refs=(SourceRef(document_id=doc.document_id,revision_id=rev.revision_id,kind='pdf',page=2),)) for i in range(4)]
        chunks[1]=chunks[1].model_copy(update=dict(parent_chunk_uid=chunks[0].chunk_uid))
        index.write_revision(scoped,rev.revision_id,chunks,attempt=attempt,
            embedder=lambda texts:dict(dense=[[1.,0.] for t in texts],sparse=[{1:.5} for t in texts]))
        source_rows=index.revision_rows(scoped,rev.revision_id)
        seed=from_index_hits([dict(entity=r) for r in source_rows if r['ordinal']==1])[0]
        related=index.related_rows(scoped,[seed],radius=1)
        assert {r['ordinal'] for r in related}=={0,1}
        assert all(r['owner_id']=='owner' and r['kb_id']=='kb' for r in related)
        assert next(r for r in related if r['ordinal']==0)['metadata']['source_refs'][0]['page']==2
    finally:client.close()
