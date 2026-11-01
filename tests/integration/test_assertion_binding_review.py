"""本轮定向复核：正式身份、完整证明及生成token与渲染字符分离。"""
from types import SimpleNamespace
import pytest
from app.evaluation.jobs import execute_job
from app.evaluation.execution_identity import run_output,result_subject
from app.knowledge.repository import fingerprint
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
