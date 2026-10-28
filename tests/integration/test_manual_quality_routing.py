"""正式Run入口的语义修复接线；隔离Mongo与合成供应商，不证明模型质量。"""
from types import SimpleNamespace
from copy import deepcopy
import pytest
from tests.integration.test_query_runs import query_context
from tests.integration.test_run_claim import run_context, request
from app.knowledge.api import ProductInput

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('question',[
    'G540 上的 USB 2.0 接口每台都有卡槽吗？',
    '仅凭 G540 型号能否确定 USB 2.0 位置一定相同？',
    'MateDock 3 上标为 USB-C 充电的接口能传数据吗？',
    'MateDock 2 上 HDMI 与 VGA 能否并行输出？'])
def test_known_subject_reaches_scoped_retrieval_and_persisted_run(query_context,question):
    user,cid,conv,repo,service,g,runner,entity,_=query_context
    product=g.add_product(user,'k',ProductInput(kb_id='k',model='华为擎云 G540',brand='华为',aliases=['G540']))
    evidence=deepcopy(entity)
    evidence['metadata']['product_ids']=[product['product_id']]
    evidence['metadata']['heading_path']=['合成配件说明']
    evidence['text']='仅为隔离接线用说明，不能据此确认真实设备能力。'
    calls=[];prompts=[]
    class Index:
        def search(self,scoped,text,**kw):
            calls.append(kw['product_ids']);return [dict(entity=evidence)]
    class Stub:
        def stream(self,prompt,**kw):
            prompts.append(prompt);yield SimpleNamespace(content='合成接线结果 [1]。')
    g.index_factory=Index;runner.llm_factory=Stub
    rid=service.create(user,cid,request(question=question))['run_id'];runner.execute(rid)
    result=repo.get(user,rid)
    assert result['state']=='completed' and result['query_plan']['route']=='answer'
    assert calls==[[product['product_id']]]
    assert evidence['text'] in prompts[0] and question in prompts[0]
    assert result['citations'][0]['text']==evidence['text']
    assert result['citations'][0]['source_refs']==evidence['metadata']['source_refs']
    assert result['citations'][0]['answer_asset_ids']==[]
    runner.execute(rid)
    assert len(prompts)==1 and conv.messages.count_documents(dict(run_id=rid,role='assistant'))==1
