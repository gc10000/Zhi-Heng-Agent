"""正式持久入口验证预算、引用编号与资产修订，模型端口注入。"""
from types import SimpleNamespace
import pytest
from tests.integration.test_run_claim import run_context,request
from tests.integration.test_query_runs import query_context

pytestmark=pytest.mark.integration


def test_question_overflow_never_calls_model_or_saves_assistant(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    runner.answer_budget=dict(context_window=512,output_tokens=64,reserve_tokens=16,max_chars=12000)
    calls=[]
    class Model:
        def stream(self,prompt,**kwargs):
            calls.append(prompt);yield SimpleNamespace(content='24V')
    runner.llm_factory=Model
    rid=service.create(user,cid,request(question='参数中English🙂'*200))['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='failed' and row['error']['code']=='prompt_budget_exceeded'
    assert calls==[] and conv.messages.count_documents(dict(run_id=rid,role='assistant'))==0


def test_unknown_reference_is_never_emitted_or_persisted_as_success(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    class Model:
        def stream(self,prompt,**kwargs):
            for text in ['参数为24V [','999',']。']:yield SimpleNamespace(content=text)
    runner.llm_factory=Model
    rid=service.create(user,cid,request())['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='failed' and row['error']['code']=='answer_citation_invalid'
    assert '[999]' not in row['answer']
    assert not any('[999]' in str(e['payload']) for e in runner.events.read(user,rid))
    assert conv.messages.count_documents(dict(run_id=rid,role='assistant'))==0


def test_selected_asset_from_other_revision_rejected_before_model(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    entity['metadata']['asset_ids']=['wrong-revision-image']
    g.db.knowledge_assets.insert_one(dict(asset_id='wrong-revision-image',document_id=entity['document_id'],revision_id='other'))
    calls=[]
    class Model:
        def stream(self,prompt,**kwargs):calls.append(prompt);yield SimpleNamespace(content='24V')
    runner.llm_factory=Model
    rid=service.create(user,cid,request())['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='failed' and row['error']['code']=='citation_scope_invalid'
    assert calls==[] and conv.messages.count_documents(dict(run_id=rid,role='assistant'))==0


def test_comparison_with_one_missing_model_explicitly_preserves_partial_scope(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    from app.knowledge.api import ProductInput
    other=g.add_product(user,'k',ProductInput(kb_id='k',model='AX-48'))
    entity['metadata']['product_ids']=[product['product_id']]
    class Index:
        def search(self,*a,**kw):return [dict(entity=entity)] if kw['product_ids']==[product['product_id']] else []
    g.index_factory=Index
    prompts=[]
    class Model:
        def stream(self,prompt,**options):prompts.append(prompt);yield SimpleNamespace(content='仅能确认AX-24为24V [1]。AX-48资料不足。')
    runner.llm_factory=Model
    rid=service.create(user,cid,request(question='比较AX-24与AX-48供电'))['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='completed' and row['answer_support']=='partial_scope'
    assert 'AX-48' in row['missing_evidence_models']
    assert '证据限制' in prompts[0] and 'AX-48' in prompts[0]


def test_truncated_output_is_labelled_in_stream_history_and_final(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    class Model:
        def stream(self,prompt,**options):
            yield SimpleNamespace(content='输入为24V [1]。')
            yield SimpleNamespace(content='',response_metadata=dict(finish_reason='length'))
    runner.llm_factory=Model
    rid=service.create(user,cid,request())['run_id'];runner.execute(rid)
    row=repo.get(user,rid)
    assert row['state']=='completed' and row['answer_support']=='partial_output'
    assert '达到输出长度上限' in row['answer']
    assert conv.history(user,cid)['items'][-1]['text']==row['answer']
    events=runner.events.read(user,rid)
    assert ''.join(e['payload']['text'] for e in events if e['type']=='answer.delta')==row['answer']
