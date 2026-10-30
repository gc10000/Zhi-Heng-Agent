"""内部组合身份与授权边界；全部为合成来源，不表示模型质量。"""
from copy import deepcopy
import pytest
from app.evaluation.strategy import EvaluationStrategy
from app.runs.models import RunInput, InternalRunInput
from app.knowledge.repository import fingerprint


def fixture():
    from app.retrieval.source_terms import collect_network_terms
    row = dict(owner_id='o', kb_id='k', document_id='d', revision_id='r', chunk_uid='c', ordinal=1,
               text='Cable网络连接。', metadata=dict(product_ids=['p'], heading_path=['概述'], asset_ids=[],
               source_refs=[dict(document_id='d', revision_id='r', kind='pdf', page=3)]))
    from app.retrieval.combination import rows_digest
    scope = dict(owner_id='o', kb_id='k', database='m1_test_combo', collection='m1_test_combo',
                 revisions={'d':'r'}, product_ids=['p'])
    value = dict(enabled=True, scope=scope, corpus_rows_sha256=rows_digest([row]),
                 corpus_snapshot_sha256='a'*64,
                 terms=collect_network_terms([row], revision_ids=['r'], product_ids=['p']),
                 reviewed_sources=[dict(document_id='d', revision_id='r', chunk_uid='c',
                     row_sha256=rows_digest([row]), proof_sha256='b'*64)])
    return value, row


def test_internal_configuration_is_explicit_and_public_request_cannot_enable():
    assert 'retrieval_combination' in EvaluationStrategy.model_fields
    assert 'retrieval_combination' in InternalRunInput.model_fields
    assert 'retrieval_combination' not in RunInput.model_fields
    assert not EvaluationStrategy().retrieval_combination.enabled


def test_missing_legacy_is_off_and_recovery_cannot_append_policy():
    from app.retrieval.combination import CombinationPolicy, validate_run_combination
    assert not validate_run_combination({}, CombinationPolicy()).enabled
    value, _ = fixture()
    with pytest.raises(Exception, match='组合'):
        validate_run_combination({}, value)
    row = dict(retrieval_combination=value, retrieval_combination_sha256=fingerprint(value))
    # 正式存储使用规范化后的完整载荷。
    payload=CombinationPolicy.model_validate(value).model_dump(mode='json')
    row.update(retrieval_combination=payload, retrieval_combination_sha256=fingerprint(payload))
    assert validate_run_combination(row,value).enabled
    row['retrieval_combination_sha256']='0'*64
    with pytest.raises(Exception):validate_run_combination(row,value)


@pytest.mark.parametrize('change', ['owner','database','collection','revision','product','text','terms','proof'])
def test_authorization_and_source_drift_rejected_before_loading_or_query(change):
    from app.retrieval.combination import authorize_combination
    value, row=fixture(); calls=[]
    args=dict(owner_id='o',kb_id='k',database='m1_test_combo',collection='m1_test_combo',
              revisions=[dict(document_id='d',active_revision_id='r')],product_ids=['p'])
    if change=='owner':args['owner_id']='other'
    if change=='database':args['database']='m1_test_other'
    if change=='collection':args['collection']='m1_test_other'
    if change=='revision':args['revisions'][0]['active_revision_id']='other'
    if change=='product':args['product_ids']=['other']
    if change=='text':row['text']='改变的文字'
    if change=='terms':value['terms'][0]['term']='invented'
    if change=='proof':value['reviewed_sources'][0]['row_sha256']='c'*64
    with pytest.raises(ValueError):
        authorize_combination(value,loader=lambda: calls.append(True) or [row],**args)
    if change in {'owner','database','collection','revision','product'}:assert not calls


def test_valid_source_is_rederived_and_unknown_versions_fail():
    from app.retrieval.combination import CombinationPolicy, authorize_combination
    value,row=fixture()
    result=authorize_combination(value,loader=lambda:[row],owner_id='o',kb_id='k',database='m1_test_combo',
        collection='m1_test_combo',revisions=[dict(document_id='d',active_revision_id='r')],product_ids=['p'])
    assert result.terms==value['terms']
    for key in ['function_version','source_terms_version','fusion_version','context_version']:
        with pytest.raises(ValueError):CombinationPolicy.model_validate(value|{key:'unknown'})


def test_execution_input_identity_includes_full_policy():
    from app.evaluation.execution_identity import run_input
    from types import SimpleNamespace
    class Cursor(list):
        def sort(self,*a):return self
        def limit(self,*a):return self
    db=SimpleNamespace(messages=SimpleNamespace(find=lambda *a:Cursor()))
    base=dict(run_id='run',conversation_id='conv',owner_id='o',kb_id='k')
    assert run_input(base|dict(retrieval_combination={'enabled':True},retrieval_combination_sha256='x'),db)!=run_input(base,db)


def test_formal_retrieve_projects_only_authorized_scope_and_passes_retention():
    from app.retrieval.search import retrieve, RetrievalPolicy
    from app.retrieval.models import QueryPlan
    from app.retrieval.combination import CombinationPolicy
    value,_=fixture();calls=[]
    class Index:
        def search(self,repo,query,**kw):calls.append((query,kw));return []
    plan=QueryPlan(original_query='设备上联方式',search_queries=('设备上联方式',),
                   product_ids=('p',),scope_groups=(('p',),),revision_ids=('r',),route='answer')
    retrieve(Index(),None,plan,embedder=None,revision_snapshot=[],policy=RetrievalPolicy(),
             combination=CombinationPolicy.model_validate(value))
    assert calls[0][0]=='设备上联方式\n原件网络介质术语：Cable'
    assert calls[0][1]['branch_retention'] is True


def test_default_retrieve_port_stays_exactly_legacy():
    from app.retrieval.search import retrieve,RetrievalPolicy
    from app.retrieval.models import QueryPlan
    calls=[]
    class Index:
        def search(self,*a,**kw):calls.append((a,kw));return []
    plan=QueryPlan(original_query='问题',search_queries=('问题',),product_ids=('p',),scope_groups=(('p',),))
    retrieve(Index(),None,plan,embedder=None,revision_snapshot=[],policy=RetrievalPolicy())
    assert set(calls[0][1])=={'embedder','revision_snapshot','product_ids','limit'}


@pytest.mark.parametrize('fault',['target','snapshot','revision'])
def test_experiment_binding_rejects_config_drift(fault):
    from app.evaluation.strategy import validate_combination_config
    value,_=fixture()
    snapshot={'format':'synthetic'};value['corpus_snapshot_sha256']=fingerprint(snapshot)
    cfg=dict(strategy='m4-configured',target={k:value['scope'][k] for k in ['owner_id','kb_id','database','collection']},
        corpus=dict(snapshot=snapshot,documents=[dict(document_id='d',revision_id='r')]),
        parameters=dict(retrieval_combination=value,source_prerequisites=dict(enabled=True,scope=value['scope']),
            retrieval=dict(exclude_image_descriptions=True,query_projection='scoped_subject_v1',comparison_context='scope_first_v1')))
    validate_combination_config(cfg)
    if fault=='target':cfg['target']['database']='m1_test_other'
    if fault=='snapshot':cfg['corpus']['snapshot']['format']='changed'
    if fault=='revision':cfg['corpus']['documents'][0]['revision_id']='changed'
    with pytest.raises(ValueError):validate_combination_config(cfg)


def test_real_index_retains_real_heads_without_fabricating_weighted_score():
    from types import SimpleNamespace
    from app.knowledge.index import V2Index
    from app.retrieval.search import RetrievalPolicy
    calls=[]
    def hit(uid):return dict(entity=dict(chunk_uid=uid,document_id='d',revision_id='r',text=uid,
        metadata=dict(product_ids=['p'],source_refs=[dict(document_id='d',revision_id='r',kind='pdf',page=1)])),distance=.8)
    class Client:
        def hybrid_search(self,**kw):calls.append(kw);return [[hit('weighted')]]
        def search(self,**kw):calls.append(kw);return [[hit(kw['anns_field'])]]
    repo=SimpleNamespace(owner_id='o',kb_id='k',get_revision=lambda rid:dict(document_id='d'))
    result=V2Index(Client(),'m1_test_combo',dense_dim=2).search(repo,'问题',
        embedder=lambda texts:dict(dense=[[1.,0.]],sparse=[{1:1.}]),
        revision_snapshot=[dict(document_id='d',active_revision_id='r')],product_ids=['p'],
        policy=RetrievalPolicy(),branch_retention=True)
    assert [r['entity']['chunk_uid'] for r in result]==['dense_vector','sparse_vector','weighted']
    assert [s['stage'] for s in result[1]['retrieval_trace']]==['learned_sparse','branch_heads_v1']
    assert len(calls)==3 and calls[0]['limit']==20


def test_missing_persisted_policy_hash_is_not_recovery_authorization():
    from app.retrieval.combination import payload,validate_run_combination
    value,_=fixture()
    with pytest.raises(Exception):validate_run_combination({'retrieval_combination':payload(value)},value)


def test_combo_reader_stops_at_bound_and_closes_iterator():
    from types import SimpleNamespace
    from app.knowledge.index import V2Index
    closed=[]
    class Iterator:
        def next(self):return [{'ordinal':1}]*3
        def close(self):closed.append(True)
    index=V2Index(SimpleNamespace(query_iterator=lambda **kw:Iterator()),'m1_test_combo')
    repo=SimpleNamespace(owner_id='o',kb_id='k',get_revision=lambda r:dict(document_id='d'))
    with pytest.raises(ValueError):index.revision_rows(repo,'r',max_rows=2)
    assert closed


@pytest.mark.parametrize('mode',['global','scope_first_v1'])
def test_disabling_combination_restores_exact_old_context_and_prompt(mode):
    from types import SimpleNamespace
    from app.runs.query_runner import QueryRunner
    from app.retrieval.combination import CombinationPolicy
    from app.retrieval.search import RetrievalPolicy
    from app.retrieval.selection import select_context
    from tests.unit.test_compare_branch_context import plan,hit,ranked
    from app.query_process.agent.nodes.node_answer_output import step_2_construct_prompt
    from app.knowledge.citation_api import controlled_markdown
    candidates=[hit('a0','a'),hit('b0','b'),hit('head','a',heads=('learned_sparse',))]
    rows=ranked(*candidates);p=plan()
    runner=QueryRunner(None,SimpleNamespace(events=None),None,retrieval_policy=RetrievalPolicy(comparison_context=mode))
    try:
        # 模拟已启用消费者关闭回切，不沿用旧启用Run。
        value,_=fixture();runner.retrieval_combination=CombinationPolicy.model_validate(value)
        runner.retrieval_combination=CombinationPolicy()
        seeds,trace=runner.context_seeds(rows,candidates,p)
        expected=select_context(rows,limit=10,scope_groups=p.scope_groups,mode=mode)
        assert seeds==expected and trace=={}
        docs=[h.document() for h in expected]
        old=dict(session_id='synthetic',is_stream=True,original_query='合成比较问题',item_names=['A','B'],
            reranked_docs=[d|dict(text=controlled_markdown(d['text'],set(d['asset_ids']))) for d in docs],
            history=[],answer_budget=runner.answer_budget,evidence_groups=[],
            evidence_scope_note='比较只能依据本轮参考内容，未提供某型号证据时必须明确资料不足，不得推断其参数。')
        old_prompt=step_2_construct_prompt(old)
        new,new_prompt=runner.evidence_prompt('合成比较问题',docs,[],p,item_names=['A','B'],history=[],session_id='synthetic')
        assert new==old and new_prompt==old_prompt
        assert not runner.authorize_combination(None,None,None,None,None).enabled
    finally:runner.close()
