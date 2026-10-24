"""旧图不得保留占位KG；汇合必须等待受控分支一次完成。"""


def test_legacy_graph_has_no_placeholder_kg_and_uses_single_barrier():
    from app.query_process.agent.main_graph import query_app
    graph=query_app.get_graph()
    assert 'node_query_kg' not in graph.nodes,'占位sleep节点不得继续注册在可执行图'
    # 一个真正的等待屏障由LangGraph的多起点边而非多条普通边表达。
    from app.query_process.agent.main_graph import builder
    assert len(builder.waiting_edges)==1,'不同分支必须汇合一次'


import copy
import threading
import time
import pytest
from app.retrieval.models import QueryPlan
from app.retrieval.routing import EnhancementPolicy,enhancement_queries
from app.retrieval.graph import run_retrieval_graph


def plan(question='AX-24无法启动故障'):
    return QueryPlan(original_query=question,search_queries=(question,),product_ids=('p',),revision_ids=('r',),
        scope_groups=(('p',),),route='answer',slots=dict(device='AX-24'))


def hit(key):return dict(entity=dict(chunk_uid=key,document_id='d',revision_id='r',text='真实证据'+key,metadata={}))


@pytest.mark.parametrize('question',['AX-24电压是多少','AX-24错误码E100故障','AX-24配置端口入口'])
def test_explicit_parameters_and_codes_do_not_trigger_hyde(question):
    p=plan(question)
    result=run_retrieval_graph(p,lambda q:[hit('local')],policy=EnhancementPolicy(hyde_enabled=True,decomposition_enabled=True),
        hyde=lambda *a:pytest.fail('明确参数/错误码不触发付费增强'))
    assert [b['status'] for b in result.branches]==['completed','skipped','skipped']
    assert len(result.hits)==1 and result.merge_count==1


def test_disabled_path_still_answers_locally_without_tool_configuration():
    result=run_retrieval_graph(plan(),lambda q:[hit('local')],policy=EnhancementPolicy(),hyde=lambda *a:pytest.fail('禁用'))
    assert len(result.hits)==1 and result.branches[1]['status']=='skipped'


@pytest.mark.parametrize('slow',['local','hyde','decomposition'])
def test_branch_order_and_finite_decomposition_merge_exactly_once(slow):
    p=plan('AX-24无法启动并且指示灯不亮同时网络异常')
    seen=[]
    def search(q):
        branch='hyde' if '检索假设' in q.search_queries[0] else 'local' if q.search_queries==p.search_queries else 'decomposition'
        if branch==slow:time.sleep(.02)
        seen.append(q)
        return [hit(branch)]
    result=run_retrieval_graph(p,search,policy=EnhancementPolicy(hyde_enabled=True,decomposition_enabled=True,max_queries=3),
        hyde=lambda q,policy:'合成检索假设')
    assert [h['entity']['chunk_uid'] for h in result.hits]==['local','hyde','decomposition']
    assert result.merge_count==1 and all(b['status']=='completed' for b in result.branches)
    assert all(q.product_ids==p.product_ids and q.revision_ids==p.revision_ids and q.scope_groups==p.scope_groups for q in seen)
    assert max(len(q.search_queries) for q in seen)<=2
    assert '合成检索假设' not in str(result.hits)


@pytest.mark.parametrize('outcome',['empty','failure'])
def test_optional_empty_and_failure_degrade_without_losing_local_evidence(outcome):
    def hyde(q,p):
        if outcome=='failure':raise TimeoutError('synthetic-private-prompt')
        return '假设'
    def search(p):return [] if '检索假设' in p.search_queries[0] else [hit('local')]
    result=run_retrieval_graph(plan(),search,policy=EnhancementPolicy(hyde_enabled=True),hyde=hyde)
    assert [h['entity']['chunk_uid'] for h in result.hits]==['local']
    assert result.branches[1]['status']==('empty' if outcome=='empty' else 'failed')
    assert 'synthetic-private-prompt' not in str(result.branches)


def test_late_timeout_result_never_mutates_already_merged_pack():
    release=threading.Event();entered=threading.Event()
    def hyde(q,p):entered.set();assert release.wait(2);return '迟到假设'
    result=run_retrieval_graph(plan(),lambda p:[hit('late' if '检索假设' in p.search_queries[0] else 'local')],
        policy=EnhancementPolicy(hyde_enabled=True,timeout_seconds=.02),hyde=hyde)
    assert entered.is_set() and result.branches[1]['status']=='timeout'
    before=copy.deepcopy(result)
    release.set();time.sleep(.04)
    assert result==before and len(result.hits)==1 and result.merge_count==1


def test_saturated_optional_capacity_degrades_without_queueing(monkeypatch):
    from app.retrieval import graph
    empty=threading.BoundedSemaphore(1);empty.acquire()
    monkeypatch.setattr(graph,'_SLOTS',empty)
    result=run_retrieval_graph(plan(),lambda p:[hit('local')],policy=EnhancementPolicy(hyde_enabled=True),
        hyde=lambda *a:pytest.fail('忙时不得排入后台付费任务'))
    assert result.branches[1]['status']=='busy' and len(result.hits)==1


def test_required_local_failure_propagates_instead_of_optional_fake_success():
    def fail(p):raise ValueError('synthetic-local-failure')
    with pytest.raises(ValueError):run_retrieval_graph(plan(),fail,policy=EnhancementPolicy())


@pytest.mark.parametrize('change',[dict(max_queries=4),dict(hyde_enabled=1),dict(timeout_seconds=float('nan')),dict(hyde_max_chars=2001),dict(extra=1)])
def test_invalid_enhancement_policy_rejected(change):
    with pytest.raises(ValueError):EnhancementPolicy(**change)


@pytest.mark.parametrize('delayed',['local','hyde'])
def test_real_compiled_legacy_graph_waits_then_answers_once(monkeypatch,delayed):
    import json
    from app.query_process.agent import main_graph as legacy
    monkeypatch.setenv('RETRIEVAL_ENHANCEMENT_JSON',json.dumps(dict(hyde_enabled=True)))
    calls=[]
    monkeypatch.setattr(legacy,'node_item_name_confirm',lambda s:dict(item_names=['AX-24'],rewritten_query=s['original_query']))
    def branch(name,key):
        def invoke(s):
            if name==delayed:time.sleep(.02)
            calls.append(name);return {key:[name]}
        return invoke
    monkeypatch.setattr(legacy,'node_search_embedding',branch('local','embedding_chunks'))
    monkeypatch.setattr(legacy,'node_search_embedding_hyde',branch('hyde','hyde_embedding_chunks'))
    monkeypatch.setattr(legacy,'node_web_search_mcp',lambda s:pytest.fail('无显式许可不得访问外网'))
    def fusion(s):
        assert s['embedding_chunks']==['local'] and s['hyde_embedding_chunks']==['hyde']
        calls.append('fusion');return dict(rrf_chunks=['both'])
    monkeypatch.setattr(legacy,'node_rrf',fusion)
    monkeypatch.setattr(legacy,'node_rerank',lambda s:dict(reranked_docs=['both']))
    def answer(s):calls.append('answer');return dict(answer='合成回答')
    monkeypatch.setattr(legacy,'node_answer_output',answer)
    result=legacy.query_app.invoke(dict(original_query='AX-24无法启动故障',session_id='synthetic',is_stream=False))
    assert result['answer']=='合成回答'
    assert calls.count('fusion')==calls.count('answer')==1
    assert set(calls[:2])=={'local','hyde'}
