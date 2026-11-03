"""新连接比较的正式job同/分库、失败持久化和首次outcome前恢复；全部合成来源。"""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from app.evaluation.jobs import execute_job
from app.knowledge.repository import fingerprint
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_comparison_answer_wiring import setup
from tests.unit.test_connection_comparison_wiring import RAW

pytestmark = pytest.mark.integration


def configure_sources(ctx, fault=None):
    from app.evaluation.corpus import corpus_snapshot
    from app.knowledge.models import content_hash
    from app.knowledge.index import V2Index
    from app.retrieval.combination import rows_digest
    from app.retrieval.source_terms import collect_network_terms
    from app.retrieval.adapters import score_record
    cfg, _, res, _, _, scoped = ctx
    g=res['knowledge'](); target=cfg['target']
    pids={p['model']:p['product_id'] for p in g.products.collection.find({})}
    original_index=g.index_factory()
    prior=original_index.search(None,None,product_ids=[pids['AX']])[0]['entity']
    doc=scoped.register_document('connection-b',name='合成乙手册',product_ids=[pids['BX']])
    revision=scoped.create_revision(doc.document_id,'connection-b',original_sha256=cfg['corpus']['documents'][0]['original_sha256'],object_key='m4-test/adapter/connection-b')
    scoped.revisions.update_one({'revision_id':revision.revision_id},{'$set':{'status':'published'}})
    scoped.documents.update_one({'document_id':doc.document_id},{'$set':{'active_revision_id':revision.revision_id}})
    def row(uid,pid,did,rid,ordinal,heading,text):
        return dict(chunk_uid=uid,owner_id=target['owner_id'],kb_id=target['kb_id'],document_id=did,
            revision_id=rid,ordinal=ordinal,text=text,content_sha256=content_hash(text.encode()),
            metadata=dict(product_ids=[pid],heading_path=[heading],content_kind='text',asset_ids=[],
                source_refs=[dict(kind='pdf',page=ordinal+1,document_id=did,revision_id=rid)]))
    rows=[row('source',pids['AX'],prior['document_id'],prior['revision_id'],0,'产品概述',
        '为了实现对设备的管理，AX通过3G/4G网络连接到运营商无线控制器。'),
        row('b-intro',pids['BX'],doc.document_id,revision.revision_id,0,'产品简介',
            'BX融合了Cable网络和无线路由器的功能。'),
        row('b-path',pids['BX'],doc.document_id,revision.revision_id,1,'排障',
            '请确认设备Cable口的同轴电缆是否插牢，同轴电缆另一端与入户接口是否连接正确。')]
    if fault=='missing':
        rows[:]=[r for r in rows if r['chunk_uid']!='b-intro']
    if fault=='ambiguous':
        rows.append(row('b-other-intro',pids['BX'],doc.document_id,revision.revision_id,3,
            '产品概述','BX融合了Cable网络和无线路由器的功能。'))
    bounded_reads={}
    class Index:
        collection=target['collection']
        payload=staticmethod(V2Index.payload)
        def revision_rows(self,repo,rid,**kwargs):
            if kwargs.get('max_rows') is not None:
                bounded_reads[rid]=bounded_reads.get(rid,0)+1
                if fault=='loader' and bounded_reads[rid]>1:
                    raise ValueError('合成：完整标量来源读取超过边界')
            return [deepcopy(r) | (dict(dense_vector=[1.,0.],sparse_vector={1:.5})
                if kwargs.get('vectors') else {}) for r in rows if r['revision_id']==rid]
        def search(self,repo,query,**kwargs):
            return [dict(entity=deepcopy(r),retrieval_trace=[score_record('dense',1,.8,'inner_product'),
                score_record('learned_sparse',1,.6,'inner_product'),score_record('weighted_fusion',1,1.4,'milvus_weighted_ip')])
                for r in rows if r['metadata']['product_ids']==kwargs['product_ids'] and r['chunk_uid'] not in {'b-intro','b-other-intro'}]
        def prerequisite_rows(self,*args,**kwargs):
            return [deepcopy(r) for r in rows if r['chunk_uid'] not in {'b-intro','b-other-intro'}]
    g.index_factory=Index
    cfg['corpus']['documents'].append(dict(document_id=doc.document_id,revision_id=revision.revision_id,
        original_sha256=cfg['corpus']['documents'][0]['original_sha256']))
    snapshot=corpus_snapshot(g,target,cfg['corpus']['documents']); cfg['corpus']['snapshot']=snapshot
    params=cfg['parameters']; combo=params['retrieval_combination']; scope=combo['scope']
    scope['revisions']={d['document_id']:d['revision_id'] for d in cfg['corpus']['documents']}
    combo.update(corpus_snapshot_sha256=fingerprint(snapshot),corpus_rows_sha256=rows_digest(rows),
        terms=collect_network_terms(rows,revision_ids=list(scope['revisions'].values()),product_ids=list(pids.values())))
    combo['reviewed_sources'][0]['row_sha256']=rows_digest([rows[0]])
    params['source_prerequisites']['scope']=deepcopy(scope)
    policy=params['evidence_attribution']
    policy.update(scope=deepcopy(scope),corpus_snapshot_sha256=fingerprint(snapshot),
        documents=[{k:d[k] for k in ('document_id','revision_id','original_sha256')} for d in cfg['corpus']['documents']])
    policy['source_relations']['frozen_payloads']={r['chunk_uid']:fingerprint(r) for r in rows}
    params['answer_budget']=dict(context_window=32768,output_tokens=512,reserve_tokens=64,max_chars=12000)
    if fault=='budget':
        params['answer_budget']['max_chars']=50
    res['connection_rows']=rows


def case(ctx,tmp_path,monkeypatch,*,separate=False,fault=None,**kwargs):
    return setup(ctx,tmp_path,monkeypatch,separate=separate,version='connection_comparison_v1',
        configure_sources=lambda ctx:configure_sources(ctx,fault),raw=kwargs.pop('raw',RAW),**kwargs)


@pytest.mark.parametrize('separate',[False,True])
def test_formal_success_reuse_and_sanitized_public_result(evaluation_context,tmp_path,monkeypatch,separate):
    cfg,res,prompts,question,repo,service,user,data,catalog=case(evaluation_context,tmp_path,monkeypatch,separate=separate)
    for key in ['first','reuse']:
        job=service.create_experiment(user,data|dict(client_request_id=key))
        execute_job(repo,catalog,tmp_path/key,job['experiment_id'])
        assert repo.get_experiment(user,job['experiment_id'])['state']=='completed'
        result=repo.results.find_one({'experiment_id':job['experiment_id']})['result']
        assert result['comparison_summary']['comparison_status']=='qualified_medium_difference'
        assert set(result['comparison_summary'])=={'function_version','comparison_target','comparison_status','answer_sha256'}
        assert '融合Cable网络和无线路由器' in result['answer']
        assert not any(k in result for k in ('source_facts','raw_selection','comparison_answer','comparison_context_assembly'))
    run=res['db'].runs.find_one({})
    assert [d['chunk_uid'] for d in run['prompt_used_docs']]==run['comparison_context_assembly']['documents']
    assert res['db'].runs.count_documents({})==1 and len(prompts)==1
    assert res['db'].evaluation_outcomes.count_documents({})==1
    assert len(run['prompt_used_docs'])==3
    events=list(res['db'].run_events.find({},{'payload':1}))
    assert RAW not in str(events) and 'source_facts' not in str(events)


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('interrupted',[False,True])
def test_failed_selection_persists_raw_without_outcome_or_retry(evaluation_context,tmp_path,monkeypatch,separate,interrupted):
    raw=RAW[:25] if interrupted else 'not-json'
    cfg,res,prompts,question,repo,service,user,data,catalog=case(evaluation_context,tmp_path,monkeypatch,
        separate=separate,raw=raw,interrupted=interrupted)
    job=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'failed',job['experiment_id'])
    run=res['db'].runs.find_one({})
    assert run['state']=='failed' and run['comparison_answer_failure']['raw_selection']==raw
    assert run['comparison_answer_failure']['function_version']=='connection_comparison_v1'
    assert not run.get('answer') and not run.get('completion_snapshot')
    assert res['db'].evaluation_outcomes.count_documents({})==0 and len(prompts)==1
    assert raw not in str(list(res['db'].run_events.find({},{'payload':1})))


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('mutation',[None,'source_facts','result','assembly','coordinated_source'])
def test_first_outcome_recovery_rebinds_sources_without_new_call(evaluation_context,tmp_path,monkeypatch,separate,mutation):
    cfg,res,prompts,question,repo,service,user,data,catalog=case(evaluation_context,tmp_path,monkeypatch,separate=separate)
    original=res['query_runner'].execute
    def crash(rid):
        original(rid)
        raise RuntimeError('合成：Run完成而首次outcome尚未冻结')
    monkeypatch.setattr(res['query_runner'],'execute',crash)
    job=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'first',job['experiment_id'])
    row=res['db'].runs.find_one({})
    assert row['state']=='completed' and len(prompts)==1
    assert res['db'].evaluation_outcomes.count_documents({})==0
    if mutation=='source_facts': row['comparison_answer']['source_facts'][0]['medium']='ethernet'
    if mutation=='result': row['comparison_answer']['result']['status']='qualified_medium_same'
    if mutation=='assembly': row['comparison_context_assembly']['max_docs']=99
    if mutation=='coordinated_source':
        from app.answering.comparison_answers import bind_comparison_response, build_frame_catalog, prompt_used_identity
        from app.answering.evidence_attribution import evidence_labels
        from app.knowledge.models import content_hash
        policy=deepcopy(cfg['parameters']['evidence_attribution'])
        doc=next(d for d in row['prompt_used_docs'] if '3G/4G网络' in d['text'])
        before=doc['text']; doc['text']=before.replace('3G/4G网络','以太网')
        assert doc['text']!=before
        doc['content_sha256']=content_hash(doc['text'].encode())
        raw= {k:doc[k] for k in ('chunk_uid','owner_id','kb_id','document_id','revision_id','ordinal','text','metadata','content_sha256')}
        policy['source_relations']['frozen_payloads'][doc['chunk_uid']]=fingerprint(raw)
        row['prompt_reference_map']=[dict(l,reference_number=i+1) for i,l in enumerate(evidence_labels(row['prompt_used_docs'],policy))]
        citation=next(c for c in row['citations'] if c['text']==before)
        citation['text']=doc['text']
        context=row['comparison_context_assembly']
        context['frozen_pool_sha256']=fingerprint(sorted(policy['source_relations']['frozen_payloads'].items()))
        context['identity_sha256']=fingerprint({k:v for k,v in context.items() if k!='identity_sha256'})
        prompt_question=row['query_plan'].get('rewritten_query') or row['question']
        prompt_question+='\n\n证据限制：比较只能依据本轮参考内容，未提供某型号证据时必须明确资料不足，不得推断其参数。'
        row['comparison_prompt_used_sha256']=prompt_used_identity(prompt_question,row['prompt_reference_map'],row['prompt_used_docs'],row['comparison_target'])
        row['answer'],row['comparison_answer']=bind_comparison_response(RAW,
            build_frame_catalog(row['prompt_reference_map'],row['prompt_used_docs'],policy),row['product_snapshot']['product_ids'],
            row['comparison_target'],row['comparison_policy_sha256'],row['comparison_prompt_used_sha256'],policy['products'],
            version='connection_comparison_v1',comparison_context=context)
    if mutation:
        res['db'].runs.replace_one({'run_id':row['run_id']},row)
    monkeypatch.setattr(res['query_runner'],'execute',original)
    reuse=service.create_experiment(user,data|dict(client_request_id='recover'))
    execute_job(repo,catalog,tmp_path/'reuse',reuse['experiment_id'])
    assert repo.get_experiment(user,reuse['experiment_id'])['state']==('failed' if mutation else 'completed')
    assert len(prompts)==1 and res['db'].runs.count_documents({})==1


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('fault,code', [('missing','comparison_source_missing'),
    ('ambiguous','comparison_source_ambiguous'),('budget','required_source_budget_exceeded'),
    ('loader','comparison_source_invalid')])
def test_source_fault_settles_formal_job_before_generation(evaluation_context,tmp_path,monkeypatch,separate,fault,code):
    cfg,res,prompts,question,repo,service,user,data,catalog=case(evaluation_context,tmp_path,monkeypatch,
        separate=separate,fault=fault)
    from app.evaluation.query_adapter import RealQueryExecutor
    with RealQueryExecutor(cfg):
        pass
    job=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/fault,job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']=='failed'
    run=res['db'].runs.find_one({})
    assert run['state']=='failed' and run['error']['code']==code
    assert not run.get('answer') and not run.get('completion_snapshot')
    from app.runs.telemetry import run_telemetry
    assert run_telemetry(res['runs'],user,run['run_id'])['failure_code']==code
    assert not prompts and res['db'].evaluation_outcomes.count_documents({})==0


def test_new_mode_unresolved_target_keeps_zero_call_clarification(evaluation_context,tmp_path,monkeypatch):
    cfg,res,prompts,question,repo,service,user,data,catalog=case(evaluation_context,tmp_path,monkeypatch,
        question_text='比较AX与BX的功能差异')
    job=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'clarification',job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']=='completed'
    run=res['db'].runs.find_one({})
    assert run['answer']=='请明确需要比较两台设备的哪一项信息。'
    assert not prompts and 'comparison_context_assembly' not in run
