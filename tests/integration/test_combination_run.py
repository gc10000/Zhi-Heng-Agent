"""正式Run、配置与恢复接线；随机Mongo、合成来源/模型，不证明真实答案质量。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.integration.test_run_claim import run_context,request
from tests.integration.test_query_runs import query_context
from app.runs.models import InternalRunInput
from app.knowledge.repository import fingerprint

pytestmark=pytest.mark.integration


def setup(context):
    from app.retrieval.source_terms import collect_network_terms
    from app.retrieval.combination import rows_digest,CombinationPolicy
    from app.retrieval.prerequisites import SourcePrerequisitePolicy
    from app.retrieval.search import RetrievalPolicy
    user,cid,conv,repo,service,g,runner,entity,product=context
    entity.update(ordinal=0,text='Cable网络连接。合成设备参数24V。')
    entity['metadata'].update(heading_path=['概述'],source_refs=[dict(kind='pdf',page=3,
        document_id=entity['document_id'],revision_id=entity['revision_id'])])
    rows=[entity|dict(owner_id=g.owner_id,kb_id='k')];calls=[];prompts=[]
    class Index:
        collection='m1_test_combo'
        def revision_rows(self,scoped,rid,**kw):calls.append('source');return deepcopy(rows)
        def search(self,scoped,text,**kw):
            calls.append(('search',text,kw))
            assert kw['branch_retention'] is True
            assert '原件网络介质术语：Cable' in text
            return [dict(entity=entity)]
        def prerequisite_rows(self,*a,**kw):return deepcopy(rows)
    g.index_factory=Index
    scope=dict(owner_id=g.owner_id,kb_id='k',database=repo.db.name,collection=Index.collection,
        revisions={entity['document_id']:entity['revision_id']},product_ids=[product['product_id']])
    combo=CombinationPolicy(enabled=True,scope=scope,corpus_snapshot_sha256='a'*64,
        corpus_rows_sha256=rows_digest(rows),terms=collect_network_terms(rows,
        revision_ids=list(scope['revisions'].values()),product_ids=scope['product_ids']),
        reviewed_sources=[dict(document_id=entity['document_id'],revision_id=entity['revision_id'],
        chunk_uid=entity['chunk_uid'],row_sha256=rows_digest(rows),proof_sha256='b'*64)])
    source=SourcePrerequisitePolicy(enabled=True,scope=scope)
    runner.retrieval_combination=combo;runner.source_prerequisites=source
    runner.retrieval_policy=RetrievalPolicy(exclude_image_descriptions=True,
        query_projection='scoped_subject_v1',comparison_context='scope_first_v1')
    class Model:
        def stream(self,prompt,**kw):prompts.append(prompt);yield SimpleNamespace(content='合成24V [1]。')
    runner.llm_factory=Model
    data=InternalRunInput(**request(question='AX-24上联方式').model_dump(),
        source_prerequisites=source,retrieval_combination=combo)
    return combo,rows,calls,prompts,data


def test_formal_run_enabled_reuses_completed_identity_and_persists_policy(query_context):
    from app.retrieval.combination import payload
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    combo,rows,calls,prompts,data=setup(query_context)
    rid=service.create(user,cid,data)['run_id'];runner.execute(rid);runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='completed'
    assert len(prompts)==1 and row['retrieval_combination']==payload(combo)
    assert row['retrieval_combination_execution']['policy_sha256']==fingerprint(payload(combo))
    assert service.create(user,cid,data)['run_id']==rid


@pytest.mark.parametrize('fault',['late_enable','version','terms','scope','snapshot','row','source_hash'])
def test_drift_never_reaches_model(query_context,fault):
    from app.retrieval.combination import CombinationPolicy
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    combo,rows,calls,prompts,data=setup(query_context)
    rid=service.create(user,cid,request(question=data.question) if fault=='late_enable' else data)['run_id']
    if fault in {'version','terms','scope','snapshot'}:
        changed=combo.model_dump(mode='json')
        if fault=='version':changed['function_version']='next'
        if fault=='terms':changed['terms'][0]['term']='invented'
        if fault=='scope':changed['scope']['collection']='m1_test_other'
        if fault=='snapshot':changed['corpus_snapshot_sha256']='c'*64
        runner.retrieval_combination=changed
    if fault=='row':rows[0]['text']='变化'
    if fault=='source_hash':repo.runs.update_one({'run_id':rid},{'$set':{'retrieval_combination_sha256':'0'*64}})
    runner.execute(rid);row=repo.get(user,rid)
    assert row['state']=='failed' and not prompts
    assert not any(isinstance(c,tuple) for c in calls)


def test_old_default_input_fingerprint_and_explicit_off_equal(query_context):
    from app.retrieval.combination import CombinationPolicy
    user,cid,conv,repo,service,*_=query_context
    data=request()
    rid=service.create(user,cid,data)['run_id']
    explicit=InternalRunInput(**data.model_dump(),retrieval_combination=CombinationPolicy())
    assert service.create(user,cid,explicit)['run_id']==rid
    row=repo.get(user,rid)
    assert row['identity']==fingerprint(data.model_dump()) and 'retrieval_combination' not in row


def test_same_request_changed_policy_is_conflict(query_context):
    from app.api.errors import APIError
    user,cid,conv,repo,service,*_=query_context
    combo,rows,calls,prompts,data=setup(query_context)
    service.create(user,cid,data)
    with pytest.raises(APIError) as exc:service.create(user,cid,request(question=data.question))
    assert exc.value.status==409


def test_created_before_worker_crash_reuses_same_run(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    combo,rows,calls,prompts,data=setup(query_context)
    # 只prepare后退出：正式create/reconcile补足会话占用，不创建第二Run。
    rid=repo.prepare(user,cid,data)['run_id']
    assert service.create(user,cid,data)['run_id']==rid
    runner.execute(rid)
    assert repo.get(user,rid)['state']=='completed' and len(prompts)==1


def test_running_interruption_uses_official_recovery_without_new_request(query_context):
    from datetime import datetime,timedelta,timezone
    from app.runs.query_runner import ExecutionStopped
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    combo,rows,calls,prompts,data=setup(query_context)
    def stop(*a,**kw):raise ExecutionStopped()
    runner.ranker=stop
    rid=service.create(user,cid,data)['run_id'];runner.execute(rid)
    assert repo.get(user,rid)['state']=='running' and not prompts
    runner.commands.clock=lambda:datetime.now(timezone.utc)+timedelta(hours=1)
    assert rid in runner.commands.recover()
    assert repo.get(user,rid)['state']=='interrupted'
    assert service.create(user,cid,data)['run_id']==rid
    runner.execute(rid)
    assert not prompts and conv.get(user,cid)['active_run_id'] is None


def test_missing_backend_cache_stops_before_model(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    combo,rows,calls,prompts,data=setup(query_context)
    original=g.index_factory
    class Index(original):
        def search(self,*a,**kw):raise KeyError('synthetic saved response cache miss')
    g.index_factory=Index
    rid=service.create(user,cid,data)['run_id'];runner.execute(rid)
    assert repo.get(user,rid)['state']=='failed' and not prompts


def test_full_formal_comparison_protects_low_rank_sparse_head_and_both_scopes(query_context):
    from app.knowledge.api import ProductInput
    from app.knowledge.index import V2Index
    from app.retrieval.combination import CombinationPolicy,rows_digest
    from app.retrieval.source_terms import collect_network_terms
    from app.retrieval.prerequisites import SourcePrerequisitePolicy
    from app.retrieval.search import RetrievalPolicy
    user,cid,conv,repo,service,g,runner,entity,first=query_context
    second=g.add_product(user,'k',ProductInput(kb_id='k',model='BX-48'))
    scoped=g.repo('k');doc=scoped.register_document('second',name='合成第二设备',product_ids=[second['product_id']])
    rev=scoped.create_revision(doc.document_id,'second',original_sha256='c'*64,object_key='isolated/second')
    scoped.documents.update_one({'document_id':doc.document_id},{'$set':{'active_revision_id':rev.revision_id}})
    conv.conversations.update_one({'conversation_id':cid},{'$set':{'product_ids':[first['product_id'],second['product_id']]}})
    rows=[]
    for product,did,rid,term in [(first,entity['document_id'],entity['revision_id'],'Cable'),(second,doc.document_id,rev.revision_id,'3G')]:
        for i in range(11):
            text=f'{term}网络连接。' if i==0 else ('合成低分必要正文。' if i==10 else f'合成资料{i}。')
            rows.append(dict(chunk_uid=f'{product["model"]}-{i}',document_id=did,revision_id=rid,ordinal=i,
                owner_id=g.owner_id,kb_id='k',text=text,metadata=dict(product_ids=[product['product_id']],
                heading_path=['概述' if i==0 else '操作'],asset_ids=[],source_refs=[dict(kind='pdf',
                    page=30 if i==10 else 3,document_id=did,revision_id=rid)])))
    class Client:
        def scoped(self,expr):return [r for r in rows if any(p in expr for p in r['metadata']['product_ids'])]
        def hybrid_search(self,**kw):return [[dict(entity=r,distance=.9-i*.01) for i,r in enumerate(self.scoped(kw['reqs'][0].expr))]]
        def search(self,**kw):
            found=self.scoped(kw['filter'])
            if kw['anns_field']=='sparse_vector':found=[found[-1],*found[:-1]]
            return [[dict(entity=r,distance=.8-i*.01) for i,r in enumerate(found)]]
        def query_iterator(self,**kw):
            found=[r for r in rows if r['revision_id'] in kw['filter']]
            class Iterator:
                def __init__(self):self.value=deepcopy(found)
                def next(self):out=self.value;self.value=[];return out
                def close(self):pass
            return Iterator()
        def query(self,**kw):return self.scoped(kw['filter'])[:kw['limit']]
    g.index_factory=lambda:V2Index(Client(),'m1_test_compare_combo',dense_dim=2)
    scope=dict(owner_id=g.owner_id,kb_id='k',database=repo.db.name,collection='m1_test_compare_combo',
        revisions={entity['document_id']:entity['revision_id'],doc.document_id:rev.revision_id},
        product_ids=[first['product_id'],second['product_id']])
    target=rows[10]
    combo=CombinationPolicy(enabled=True,scope=scope,corpus_snapshot_sha256='a'*64,corpus_rows_sha256=rows_digest(rows),
        terms=collect_network_terms(rows,revision_ids=list(scope['revisions'].values()),product_ids=scope['product_ids']),
        reviewed_sources=[dict(document_id=target['document_id'],revision_id=target['revision_id'],chunk_uid=target['chunk_uid'],
            row_sha256=rows_digest([target]),proof_sha256='b'*64)])
    runner.retrieval_combination=combo;runner.source_prerequisites=SourcePrerequisitePolicy(enabled=True,scope=scope)
    runner.retrieval_policy=RetrievalPolicy(exclude_image_descriptions=True,query_projection='scoped_subject_v1',comparison_context='scope_first_v1')
    runner.ranker=lambda q,docs:sorted([d|dict(score=.001 if d['ordinal']==10 else 1-d['ordinal']*.02) for d in docs],key=lambda d:d['score'],reverse=True)
    prompts=[]
    class Model:
        def stream(self,prompt,**kw):prompts.append(prompt);yield SimpleNamespace(content='合成比较 [1]。')
    runner.llm_factory=Model
    data=InternalRunInput(**request(question='AX-24与BX-48的上联方式相同吗？请比较。').model_dump(),
        source_prerequisites=runner.source_prerequisites,retrieval_combination=combo)
    rid=service.create(user,cid,data)['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='completed' and row['query_plan']['route']=='compare'
    assert len(row['citations'])==10 and '合成低分必要正文' in prompts[0]
    assert {p for c in row['citations'] for p in next(r for r in rows if r['chunk_uid']==c['chunk_uid'])['metadata']['product_ids']}==set(scope['product_ids'])
    assert any(c['chunk_uid']==target['chunk_uid'] and c['source_refs'][0]['page']==30 for c in row['citations'])
    assert row['retrieval_combination_execution']['applied'] is True
