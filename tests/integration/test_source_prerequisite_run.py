"""合成索引/供应商与隔离Mongo验证正式消费者；不是模型质量测试。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.integration.test_run_claim import run_context,request
from tests.integration.test_query_runs import query_context

pytestmark=pytest.mark.integration


def setup_source(context,max_chars=6000):
    user,cid,conv,repo,service,g,runner,entity,product=context
    entity['ordinal']=9;entity['text']='充电接口不支持数据传输。'
    entity['metadata'].update(content_kind='table',heading_path=['配件'],source_refs=[dict(kind='pdf',page=3,document_id=entity['document_id'],revision_id=entity['revision_id'])])
    parent=deepcopy(entity)|dict(chunk_uid='object',ordinal=8,text='了解 外设 Alpha')
    parent['metadata']['content_kind']='text'
    calls=[]
    class Index:
        collection='m1_test_source'
        def search(self,*a,**kw):return [dict(entity=entity)]
        def prerequisite_rows(self,scoped,seeds,**kw):
            calls.append(kw);return [parent|dict(owner_id=g.owner_id,kb_id='k')]
    g.index_factory=Index
    cfg=dict(enabled=True,max_chars=max_chars,scope=dict(owner_id=g.owner_id,kb_id='k',database=repo.db.name,collection='m1_test_source',revisions={entity['document_id']:entity['revision_id']},product_ids=[product['product_id']]))
    runner.source_prerequisites=cfg
    prompts=[]
    class Model:
        def stream(self,prompt,**kw):prompts.append(prompt);yield SimpleNamespace(content='合成验证 [1]。')
    runner.llm_factory=Model
    return cfg,calls,prompts


def test_enabled_groups_citations_and_idempotent_internal_request(query_context):
    from app.runs.models import InternalRunInput
    from app.retrieval.prerequisites import SourcePrerequisitePolicy
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    cfg,calls,prompts=setup_source(query_context)
    data=InternalRunInput(**request().model_dump(),source_prerequisites=cfg)
    rid=service.create(user,cid,data)['run_id'];runner.execute(rid);runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='completed' and len(prompts)==1 and len(calls)==1
    assert '了解 外设 Alpha' in prompts[0] and '不支持数据传输' in prompts[0]
    assert [c['chunk_uid'] for c in row['citations']]==['object','chunk-one']
    assert row['evidence_groups']==[['object','chunk-one']]
    assert row['source_prerequisites']==SourcePrerequisitePolicy.model_validate(cfg).model_dump(mode='json')
    assert any(s['stage']=='source_prerequisite' for t in row['retrieval_trace'] for s in t['stages'])
    assert conv.history(user,cid)['items'][-1]['citations']==row['citations']
    assert service.create(user,cid,data)['run_id']==rid
    from app.api.errors import APIError
    with pytest.raises(APIError):service.create(user,cid,request())


def test_changed_config_rejects_before_index_or_model(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    cfg,calls,prompts=setup_source(query_context)
    rid=service.create(user,cid,request())['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='failed' and row['error']['code']=='execution_config_conflict'
    assert not calls and not prompts


def test_source_budget_drops_entire_group_before_provider(query_context):
    from app.runs.models import InternalRunInput
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    cfg,calls,prompts=setup_source(query_context,max_chars=1)
    rid=service.create(user,cid,InternalRunInput(**request().model_dump(),source_prerequisites=cfg))['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='completed' and row['citations']==[] and not prompts
    assert row['source_prerequisites_excluded'][0]['reason']=='source_prerequisite_budget'


def test_disabled_rolls_back_without_reading_prerequisites(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    cfg,calls,prompts=setup_source(query_context)
    runner.source_prerequisites={}
    rid=service.create(user,cid,request())['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='completed' and not calls and len(prompts)==1
    assert [c['chunk_uid'] for c in row['citations']]==['chunk-one']
    assert '了解 外设 Alpha' not in prompts[0]


@pytest.mark.parametrize('fault',['owner','revision','product','ref','asset','expansion','namespace','collection'])
def test_invalid_source_never_reaches_synthetic_supplier(query_context,fault):
    from app.runs.models import InternalRunInput
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    cfg,calls,prompts=setup_source(query_context)
    if fault=='collection':cfg['scope']['collection']='m1_test_other_collection';runner.source_prerequisites=cfg
    if fault=='expansion':runner.expansion_policy=dict(enabled=True)
    elif fault=='namespace':
        # 真库仍是隔离库；只替换消费者看到的名称触发保护。
        runner.knowledge=lambda:SimpleNamespace(db=SimpleNamespace(name='production'))
    else:
        original=g.index_factory()
        class Index:
            collection='m1_test_source'
            def search(self,*a,**kw):return original.search(*a,**kw)
            def prerequisite_rows(self,*a,**kw):
                rows=original.prerequisite_rows(*a,**kw)
                if fault=='owner':rows[0]['owner_id']='foreign'
                elif fault=='revision':rows[0]['revision_id']='foreign'
                elif fault=='product':rows[0]['metadata']['product_ids']=['foreign']
                elif fault=='ref':rows[0]['metadata']['source_refs'][0]['revision_id']='foreign'
                elif fault=='asset':rows[0]['metadata']['asset_ids']=['missing-image']
                return rows
        g.index_factory=Index
    rid=service.create(user,cid,InternalRunInput(**request().model_dump(),source_prerequisites=cfg))['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='failed' and not prompts
    assert conv.messages.count_documents(dict(run_id=rid,role='assistant'))==0


def test_real_milvus_prerequisite_read_is_bounded_and_product_scoped(mongo_db):
    import os
    from uuid import uuid4
    from pymilvus import MilvusClient
    from app.knowledge.index import V2Index
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.models import Chunk,SourceRef
    from app.retrieval.adapters import from_index_hits
    client=MilvusClient(uri=os.environ['MILVUS_URL'])
    index=V2Index(client,'m1_test_m6_prereq_'+uuid4().hex,dense_dim=2)
    scoped=KnowledgeRepository(mongo_db,owner_id='o',kb_id='k')
    try:
        index.ensure_collection()
        doc=scoped.register_document('source',name='合成来源前提资料',product_ids=['p'])
        rev=scoped.create_revision(doc.document_id,'v1',original_sha256='a'*64,object_key='m6-test/prereq/synthetic')
        attempt=scoped.claim_attempt(rev.revision_id,expected_attempt=0)
        chunks=[Chunk(chunk_uid=uuid4().hex,document_id=doc.document_id,revision_id=rev.revision_id,
            ordinal=i,section_id='synthetic',text=['2020 年 07 月','了解 外设 Alpha','充电口 | 不传数据','其他产品'][i],
            product_ids=('p',) if i<3 else ('foreign',),heading_path=('配件',),
            source_refs=(SourceRef(document_id=doc.document_id,revision_id=rev.revision_id,kind='pdf',page=1 if i==0 else 3),)) for i in range(4)]
        index.write_revision(scoped,rev.revision_id,chunks,attempt=attempt,
            embedder=lambda texts:dict(dense=[[1.,0.] for _ in texts],sparse=[{1:.5} for _ in texts]))
        seed=from_index_hits([dict(entity=r) for r in index.revision_rows(scoped,rev.revision_id) if r['ordinal']==2])[0]
        snapshot=[dict(document_id=doc.document_id,active_revision_id=rev.revision_id)]
        result=index.prerequisite_rows(scoped,[seed],revision_snapshot=snapshot,product_ids=['p'],max_rows=3)
        assert len(result)==3 and {r['ordinal'] for r in result}=={0,1,2}
        with pytest.raises(ValueError):index.prerequisite_rows(scoped,[seed],revision_snapshot=snapshot,product_ids=['p'],max_rows=2)
    finally:client.close()


def test_final_prompt_budget_keeps_source_and_dependent_out_together(query_context):
    from app.runs.models import InternalRunInput
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    cfg,calls,prompts=setup_source(query_context)
    runner.answer_budget=dict(context_window=32768,output_tokens=4096,max_chars=1)
    rid=service.create(user,cid,InternalRunInput(**request().model_dump(),source_prerequisites=cfg))['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='completed' and not row['citations'] and not prompts
    assert row['evidence_groups']==[['object','chunk-one']] and row['prompt_budget']['omitted_documents']==2
