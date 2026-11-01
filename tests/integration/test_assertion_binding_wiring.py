"""随机短前缀Mongo库，正式消费者与恢复；只用合成选择响应。"""
from copy import deepcopy
from types import SimpleNamespace

import pytest
from app.evaluation.jobs import execute_job
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_split_ledger import formal_case
from tests.integration.test_candidate_evidence_quality_fix import attribution_config

pytestmark = pytest.mark.integration


def setup(ctx, tmp_path, monkeypatch, separate, raw='{"references":[1]}'):
    attribution_config(ctx)
    policy=ctx[0]['parameters']['evidence_attribution']
    policy['source_relations']=dict(enabled=True, function_version='source_relation_spans_v1',
        frozen_payloads={c['chunk_uid']:c['payload_sha256']
                         for d in ctx[0]['corpus']['snapshot']['documents'] for c in d['chunks']})
    policy['assertion_binding']=dict(enabled=True,function_version='assertion_binding_v1')
    class Model:
        def stream(self,prompt,**kw):
            ctx[3].append(prompt)
            yield SimpleNamespace(content=raw,response_metadata={'finish_reason':'stop'})
    ctx[2]['query_runner'].llm_factory=Model
    return formal_case(ctx,tmp_path,monkeypatch,separate=separate)


@pytest.mark.parametrize('separate',[False,True])
def test_formal_completed_selection_proof_checkpoint_and_observed_reuse(evaluation_context,tmp_path,monkeypatch,separate):
    cfg,res,prompts,question,repo,service,user,data,catalog=setup(evaluation_context,tmp_path,monkeypatch,separate)
    for key in ('first','reuse'):
        job=service.create_experiment(user,data|dict(client_request_id=key))
        execute_job(repo,catalog,tmp_path/key,job['experiment_id'])
        assert repo.get_experiment(user,job['experiment_id'])['state']=='completed'
        result=repo.results.find_one({'experiment_id':job['experiment_id']})['result']
        assert result['answer_binding']['selected_references']==[1]
        assert 'Cable网络连接' in result['answer'] and result['answer']!='{"references":[1]}'
    row=res['db'].runs.find_one({})
    assert row['evidence_attribution']['assertion_binding']['enabled']
    assert row['answer_binding']['raw_selection']=='{"references":[1]}'
    assert len(prompts)==1 and res['db'].runs.count_documents({})==1
    assert res['db'].evaluation_items.find_one({})['evidence_attribution']['assertion_binding']['enabled']


@pytest.mark.parametrize('separate',[False,True])
def test_formal_free_assertion_fails_without_success_checkpoint(evaluation_context,tmp_path,monkeypatch,separate):
    cfg,res,prompts,question,repo,service,user,data,catalog=setup(
        evaluation_context,tmp_path,monkeypatch,separate,raw='客户端无线访问就是设备上联。[1]')
    job=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'failed',job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']=='failed'
    row=res['db'].runs.find_one({})
    assert row['state']=='failed' and row['error']['code']=='answer_binding_invalid'
    assert row['answer_binding_failure']['raw_selection'].startswith('客户端')
    assert not row.get('answer') and not row.get('completion_snapshot')
    assert res['db'].evaluation_outcomes.count_documents({})==0
    assert len(prompts)==1


@pytest.mark.parametrize('field',['answer','raw','proof','scope','policy'])
def test_reuse_rejects_binding_drift_without_another_call(evaluation_context,tmp_path,monkeypatch,field):
    cfg,res,prompts,question,repo,service,user,data,catalog=setup(evaluation_context,tmp_path,monkeypatch,False)
    job=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'first',job['experiment_id'])
    assert repo.get_experiment(user,job['experiment_id'])['state']=='completed'
    path,value={
        'answer':('answer','伪造的上联结论'),
        'raw':('answer_binding.raw_selection','{"references":[999]}'),
        'proof':('answer_binding.answer_sha256','0'*64),
        'scope':('prompt_reference_map.0.source_relations.frames.0.scope.text','伪造的原句'),
        'policy':('evidence_attribution.assertion_binding.enabled',False)}[field]
    res['db'].runs.update_one({}, {'$set':{path:value}})
    second=service.create_experiment(user,data|dict(client_request_id='resume'))
    execute_job(repo,catalog,tmp_path/'resume',second['experiment_id'])
    assert repo.get_experiment(user,second['experiment_id'])['state']=='failed'
    assert len(prompts)==1
