"""随机Mongo，合成索引/模型验证正式QueryRunner接线；非真实质量证明。"""
from types import SimpleNamespace
import pytest
from tests.integration.test_query_runs import query_context
from tests.integration.test_run_claim import run_context, request
from tests.integration.test_source_prerequisite_run import setup_source

pytestmark=pytest.mark.integration

@pytest.mark.parametrize('enabled',[False,True])
def test_off_on_formal_run_preserves_request_prompt_sources_and_resume(query_context,enabled):
 from app.retrieval.search import RetrievalPolicy
 from app.runs.models import InternalRunInput
 from app.evaluation.validate_dataset import fingerprint
 user,cid,conv,repo,service,g,runner,entity,product=query_context
 cfg,calls,prompts=setup_source(query_context)
 runner.retrieval_policy=RetrievalPolicy(query_projection='scoped_subject_v1' if enabled else 'original',exclude_image_descriptions=True)
 model=product['model'];question=model+'首次登录后应如何修改密码？'
 captured=[]
 class Index:
  collection='m1_test_source'
  def search(self,scoped,text,**kw):captured.append((text,kw));return [dict(entity=entity)]
  def prerequisite_rows(self,scoped,seeds,**kw):
   return [entity|dict(owner_id=g.owner_id,kb_id='k')]
 g.index_factory=Index
 data=InternalRunInput(**(request().model_dump()|dict(question=question)),source_prerequisites=cfg)
 rid=service.create(user,cid,data)['run_id'];runner.execute(rid);runner.execute(rid)
 row=repo.get(user,rid)
 assert row['state']=='completed' and len(prompts)==1 and len(captured)==1
 assert captured[0][0]==('该设备首次登录后应如何修改密码？' if enabled else question)
 assert row['question']==question and question in prompts[0]
 assert row['query_plan']['original_query']==question
 assert row['query_plan']['search_queries']==[captured[0][0]]
 assert row['retrieval_policy']['query_projection']==('scoped_subject_v1' if enabled else 'original')
 assert row['product_snapshot']['product_ids']==[product['product_id']]
 assert row['citations'] and service.create(user,cid,data)['run_id']==rid
