"""本轮定向复核：正式身份、完整证明及生成token与渲染字符分离。"""
from types import SimpleNamespace
import pytest
from app.evaluation.jobs import execute_job
from app.evaluation.execution_identity import run_output,result_subject
from app.knowledge.repository import fingerprint
from app.answering.evidence_attribution import validate_run_attribution
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_assertion_binding_wiring import setup

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('separate',[False,True])
def test_review_full_identity_proof_and_usage_reuse(evaluation_context,tmp_path,monkeypatch,separate):
    cfg,res,prompts,q,repo,service,user,data,catalog=setup(evaluation_context,tmp_path,monkeypatch,separate)
    class Measured:
        def stream(self,prompt,**kw):
            prompts.append(prompt)
            yield SimpleNamespace(content='{"references":[1]}',response_metadata={'finish_reason':'stop'},usage_metadata={'input_tokens':101,'output_tokens':7})
    res['query_runner'].llm_factory=Measured
    canonical=cfg['parameters']['evidence_attribution']
    for key in ('first','reuse'):
        job=service.create_experiment(user,data|dict(client_request_id=key))
        execute_job(repo,catalog,tmp_path/key,job['experiment_id'])
        assert repo.get_experiment(user,job['experiment_id'])['state']=='completed'
        r=repo.results.find_one({'experiment_id':job['experiment_id']})['result']
        run=res['db'].runs.find_one({});checkpoint=res['db'].evaluation_items.find_one({})
        link=res['db'].evaluation_execution_links.find_one({'experiment_id':job['experiment_id']})
        for row in (run,checkpoint,link):
            assert row['evidence_attribution']['assertion_binding']==canonical['assertion_binding']
            assert row['evidence_attribution_sha256']==fingerprint(row['evidence_attribution'])
        proof=run['answer_binding']
        assert r['answer_binding']==proof and proof['raw_selection']=='{"references":[1]}'
        assert proof['answer_sha256']==fingerprint(run['answer']) and proof['reference_map_sha256']==fingerprint(run['prompt_reference_map'])
        outcome=res['db'].evaluation_outcomes.find_one({})
        assert outcome['run_output_sha256']==fingerprint(run_output(run))
        # 正式文件结果有额外retrieval参数，按同一project_result核完整结果身份。
        from app.evaluation.query_adapter import RealQueryExecutor
        with RealQueryExecutor(cfg) as reader:full=reader.project_result(run)
        assert outcome['result_sha256']==fingerprint(result_subject(full))
        assert r['token_usage']==dict(input=101,output=7)
        assert len(run['answer'])>7 and run['answer']!='{"references":[1]}'
    assert len(prompts)==1 and res['db'].runs.count_documents({})==1


@pytest.mark.parametrize('separate',[False,True])
def test_review_empty_evidence_run_and_result_complete_consistently(evaluation_context,tmp_path,monkeypatch,separate):
    cfg,res,prompts,q,repo,service,user,data,catalog=setup(evaluation_context,tmp_path,monkeypatch,separate)
    gateway=res['knowledge']();base=gateway.index_factory
    class EmptyIndex(base):
        def search(self,*args,**kwargs):return []
    gateway.index_factory=EmptyIndex
    job=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'empty',job['experiment_id'])
    row=res['db'].runs.find_one({});result=repo.results.find_one({'experiment_id':job['experiment_id']})['result']
    validate_run_attribution(row,cfg['parameters']['evidence_attribution'])
    assert row['state']=='completed' and repo.get_experiment(user,job['experiment_id'])['state']=='completed',row.get('error')
    assert result['behavior']=='insufficient' and result['answer_binding']['status']=='insufficient_evidence'
    assert row['answer_binding']==result['answer_binding']
    assert row['prompt_reference_map']==[] and row['citations']==[] and not prompts
    assert res['db'].evaluation_outcomes.count_documents({})==1


@pytest.mark.parametrize('separate',[False,True])
def test_review_disconnect_persists_partial_selection_and_unknown_usage(evaluation_context,tmp_path,monkeypatch,separate):
    cfg,res,prompts,q,repo,service,user,data,catalog=setup(evaluation_context,tmp_path,monkeypatch,separate)
    partial='{"references":['
    class Interrupted:
        def stream(self,prompt,**kwargs):
            prompts.append(prompt)
            yield SimpleNamespace(content=partial,response_metadata={},usage_metadata={'input_tokens':15,'output_tokens':3})
            raise ConnectionError('synthetic disconnect')
    res['query_runner'].llm_factory=Interrupted
    job=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'disconnect',job['experiment_id'])
    row=res['db'].runs.find_one({});failure=row['answer_binding_failure']
    assert row['state']=='failed' and not row.get('answer') and len(prompts)==1
    assert failure['raw_selection']==partial and failure['failure_code']=='answer_generation_interrupted'
    assert failure['input_sha256'] and row['telemetry_measurements']['token_usage']==dict(input=None,output=None)
    assert res['db'].evaluation_outcomes.count_documents({})==0


def test_review_coordinated_source_rewrite_rejected_before_first_outcome(evaluation_context,tmp_path,monkeypatch):
    from app.answering.assertion_binding import bind_response
    from app.answering.source_relations import extract_frames
    from app.knowledge.models import content_hash
    cfg,res,prompts,q,repo,service,user,data,catalog=setup(evaluation_context,tmp_path,monkeypatch,False)
    job=service.create_experiment(user,data)
    execute_job(repo,catalog,tmp_path/'first',job['experiment_id'])
    row=res['db'].runs.find_one({});assert row['state']=='completed' and len(prompts)==1
    res['db'].evaluation_outcomes.delete_many({'run_id':row['run_id']})
    rewritten='设备甲通过无线方式上联到设备乙。'
    row['prompt_used_docs'][0]['text']=rewritten
    row['citations'][0]['text']=rewritten
    relation=row['prompt_reference_map'][0]['source_relations']
    relation['source']['content_sha256']=content_hash(rewritten.encode())
    relation['frames']=extract_frames(rewritten)
    raw=row['answer_binding']['raw_selection']
    answer,proof=bind_response(raw,row['prompt_reference_map'],row['prompt_used_docs'])
    res['db'].runs.update_one({'run_id':row['run_id']},{'$set':{
        'prompt_used_docs':row['prompt_used_docs'],'citations':row['citations'],
        'prompt_reference_map':row['prompt_reference_map'],'answer':answer,
        'completion_snapshot.text':answer,'answer_binding':proof|dict(raw_selection=raw)}})
    from app.evaluation.query_adapter import RealQueryExecutor
    with RealQueryExecutor(cfg) as reader:
        with pytest.raises(ValueError,match='冻结|来源'):
            reader.project_result(res['db'].runs.find_one({'run_id':row['run_id']}))
    assert res['db'].evaluation_outcomes.count_documents({'run_id':row['run_id']})==0
    assert len(prompts)==1
