"""条件增强经正式入口只交付真实资料，假设只用作查询。"""
from types import SimpleNamespace
import pytest
from tests.integration.test_run_claim import run_context,request
from tests.integration.test_query_runs import query_context

pytestmark=pytest.mark.integration


def test_enabled_symptom_hyde_retrieves_real_evidence_without_exposing_hypothesis(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    runner.enhancement_policy=dict(hyde_enabled=True)
    queries=[];prompts=[]
    class Index:
        def search(self,scoped,text,**kw):
            queries.append(text)
            assert kw['product_ids']==[product['product_id']]
            return [dict(entity=entity)] if 'synthetic-hypothesis-canary' in text else []
    class Model:
        def invoke(self,prompt,**kw):prompts.append(prompt);return SimpleNamespace(content='synthetic-hypothesis-canary')
        def stream(self,prompt,**kw):
            assert 'synthetic-hypothesis-canary' not in prompt and '24V' in prompt
            yield SimpleNamespace(content='输入24V [1]。')
    g.index_factory=Index;runner.llm_factory=Model
    rid=service.create(user,cid,request(question='AX-24无法启动故障'))['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert len(prompts)==1,'模糊症状显式启用后必须实际运行条件HyDE'
    assert row['state']=='completed' and len(row['citations'])==1
    assert 'synthetic-hypothesis-canary' not in row['answer']
    assert len(queries)==2 and any('synthetic-hypothesis-canary' in q for q in queries)
    assert {b['status'] for b in row['retrieval_branches'] if b['name']=='hyde'}=={'completed'}
