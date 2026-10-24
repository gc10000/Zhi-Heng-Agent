"""正式入口的缓存隔离，不接真实模型。"""
import pytest
from tests.integration.test_run_claim import run_context,request
from tests.integration.test_query_runs import query_context
from app.conversations.models import ConversationInput

pytestmark=pytest.mark.integration


def test_identical_queries_in_independent_conversations_reuse_only_scoped_embedding(query_context,monkeypatch):
    import json
    monkeypatch.setenv('MODEL_RUNTIME_JSON',json.dumps(dict(cache_enabled=True)))
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    calls=[]
    runner.embedder=lambda texts:calls.extend(texts) or dict(dense=[[1.,0.] for _ in texts],sparse=[{1:.5} for _ in texts])
    class Index:
        def search(self,scoped,text,**kw):
            kw['embedder']([text]);return [dict(entity=entity)]
    g.index_factory=Index
    first=service.create(user,cid,request())['run_id'];runner.execute(first)
    other=conv.create(user,ConversationInput(kb_id='k',product_ids=[product['product_id']]))['conversation_id']
    second=service.create(user,other,request())['run_id'];runner.execute(second)
    assert repo.get(user,first)['state']==repo.get(user,second)['state']=='completed'
    assert len(calls)==1,'相同授权/产品/修订/模型/策略与问题只编码一次，不缓存答案'
    assert conv.messages.count_documents(dict(role='assistant'))==2
