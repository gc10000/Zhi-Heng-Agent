"""仅合成供应商检查正式adapter配置/检查点，不写真实评测。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from tests.integration.test_evaluation_run_adapter import evaluation_context

pytestmark=pytest.mark.integration


def test_adapter_propagates_policy_and_reuses_same_completed_request(evaluation_context):
    from app.evaluation.query_adapter import RealQueryExecutor
    from app.retrieval.prerequisites import policy_payload
    cfg,factory,resources,prompts,question,scoped=evaluation_context
    cfg=deepcopy(cfg);target=cfg['target'];g=resources['knowledge']()
    original=g.index_factory().search()[0]['entity'];pid=g.products.collection.find_one({})['product_id']
    original['metadata']['product_ids']=[pid];original['metadata']['content_kind']='table';original['metadata']['heading_path']=['配件'];original['ordinal']=2
    parent=deepcopy(original)|dict(chunk_uid='prereq-object',ordinal=1,text='了解 外设 Alpha')
    parent['metadata']['content_kind']='text'
    class Index:
        collection=target['collection']
        def search(self,*a,**kw):return [dict(entity=original)]
        def prerequisite_rows(self,repo,**kw):return [parent|dict(owner_id=target['owner_id'],kb_id=target['kb_id'])]
    g.index_factory=Index
    p=dict(enabled=True,scope=dict(owner_id=target['owner_id'],kb_id=target['kb_id'],database=target['database'],collection=target['collection'],revisions={d['document_id']:d['revision_id'] for d in cfg['corpus']['documents']},product_ids=[pid]))
    cfg.update(strategy='m4-configured',parameters=dict(source_prerequisites=p))
    with RealQueryExecutor(cfg,resource_factory=factory) as execute:first=execute(question)
    with RealQueryExecutor(cfg,resource_factory=factory) as execute:second=execute(question)
    assert first['run_id']==second['run_id'] and len(prompts)==1
    row=resources['runs'].get(execute.user,first['run_id'])
    assert row['source_prerequisites']==policy_payload(p)
    assert [c['chunk_uid'] for c in row['citations']]==['prereq-object',original['chunk_uid']]
    assert '了解 外设 Alpha' in prompts[0]
    assert resources['db'].evaluation_items.count_documents({})==1
    # 新预算是新配置/检查点/请求，不允许覆盖或继承旧完成结果。
    changed=deepcopy(cfg);changed['parameters']['source_prerequisites']['max_added']=3
    with RealQueryExecutor(changed,resource_factory=factory) as execute:third=execute(question)
    assert third['run_id']!=first['run_id'] and len(prompts)==2
    assert resources['db'].evaluation_items.count_documents({})==2
