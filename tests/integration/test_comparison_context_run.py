"""正式Run的比较范围选择、来源前提组合与关闭回切；供应商仅为合成夹具。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.integration.test_run_claim import run_context,request
from tests.integration.test_query_runs import query_context

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('mode',['global','scope_first_v1'])
@pytest.mark.parametrize('prerequisites',[False,True])
def test_formal_comparison_reserves_both_scopes_only_when_enabled(query_context,mode,prerequisites):
    from app.knowledge.api import ProductInput
    from app.runs.models import InternalRunInput
    from app.retrieval.search import RetrievalPolicy
    user,cid,conv,repo,service,g,runner,entity,first=query_context
    second=g.add_product(user,'k',ProductInput(kb_id='k',model='BX-48'))
    knowledge=g.repo('k');doc=knowledge.register_document('second',name='合成手册',product_ids=[second['product_id']])
    rev=knowledge.create_revision(doc.document_id,'second',original_sha256='b'*64,object_key='isolated/two.md')
    knowledge.documents.update_one({'document_id':doc.document_id},{'$set':{'active_revision_id':rev.revision_id}})
    other=deepcopy(entity)|dict(chunk_uid='other',document_id=doc.document_id,revision_id=rev.revision_id,text='另一设备合成有线接口依据。')
    other['metadata'].update(product_ids=[second['product_id']],source_refs=[dict(document_id=doc.document_id,revision_id=rev.revision_id,kind='markdown',line_start=1)])
    entities=[entity|dict(chunk_uid='a-'+str(i)) for i in range(20)]+[other]
    class Index:
        collection='m1_test_compare'
        def search(self,scoped,text,**kw):
            return [dict(entity=e) for e in entities if e['metadata']['product_ids']==kw['product_ids']]
        def prerequisite_rows(self,*a,**kw):return [e|dict(owner_id=g.owner_id,kb_id='k') for e in entities]
    g.index_factory=Index
    runner.retrieval_policy=RetrievalPolicy(comparison_context=mode,exclude_image_descriptions=True,query_projection='scoped_subject_v1')
    runner.ranker=lambda q,docs:sorted([d|dict(score=.001 if d['document_id']==doc.document_id else .9) for d in docs],key=lambda d:d['score'],reverse=True)
    prompts=[]
    class Model:
        def stream(self,prompt,**kw):prompts.append(prompt);yield SimpleNamespace(content='明确标识的合成协议答案。')
    runner.llm_factory=Model
    source={}
    if prerequisites:
        source=dict(enabled=True,scope=dict(owner_id=g.owner_id,kb_id='k',database=repo.db.name,collection='m1_test_compare',
            revisions={entity['document_id']:entity['revision_id'],doc.document_id:rev.revision_id},product_ids=[first['product_id'],second['product_id']]))
        runner.source_prerequisites=source
    data=InternalRunInput(**(request().model_dump()|dict(question='请分别比较AX-24与BX-48的接入方式')),source_prerequisites=source)
    rid=service.create(user,cid,data)['run_id'];runner.execute(rid);runner.execute(rid)
    saved=repo.get(user,rid)
    assert saved['state']=='completed',saved.get('error')
    assert len(prompts)==1 and saved['retrieval_policy']['comparison_context']==mode
    assert len(saved['citations'])<=10
    assert any(c['document_id']==doc.document_id for c in saved['citations'])==(mode=='scope_first_v1')
    assert ('另一设备合成有线接口依据' in prompts[0])==(mode=='scope_first_v1')
    assert service.create(user,cid,data)['run_id']==rid
