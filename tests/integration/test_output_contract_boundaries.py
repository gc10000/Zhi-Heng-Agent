"""原独立反例落实到正式job与隔离账本，全部为合成响应。"""
from types import SimpleNamespace
import pytest
from app.api.errors import APIError
from tests.unit.test_output_contract import verified_case
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration.test_evaluation_split_ledger import formal_case
from tests.integration.test_diagnostic_output_contract import output_case

pytestmark=pytest.mark.integration


@pytest.mark.parametrize('reasoning',[None,0,8,9,-1,True,9.5,'9'])
def test_detail_settlement_and_replay_are_safe(mongo_db,monkeypatch,reasoning):
    from app.infrastructure.providers.output_contract import OutputLedger
    p,_,_=verified_case(monkeypatch);ledger=OutputLedger(mongo_db,p)
    ledger.begin('r','i')
    row=ledger.settle('r','i',{'input':3,'output':8},completed=True,reasoning=reasoning)
    assert ledger.settle('r','i',{'input':3,'output':8},completed=True,reasoning=reasoning)==row
    valid=reasoning is None or type(reasoning) is int and 0<=reasoning<=8
    assert row['state']==('open' if valid else 'blocked')
    if not valid:
        assert row['new_output_tokens'] is None and row['unknown_windows']
        assert not next(iter(row['settled'].values()))['usage_validation']['valid']
        with pytest.raises(APIError):OutputLedger(mongo_db,p).begin('next','i2')
        with pytest.raises(APIError):ledger.settle('r','i',{'input':3,'output':8},completed=True,reasoning=0)


@pytest.mark.parametrize('reasoning',[9,-1,True,9.5,'9',None,0,8])
def test_formal_job_cannot_complete_with_invalid_detail(evaluation_context,tmp_path,monkeypatch,reasoning):
    from app.evaluation.jobs import execute_job
    output_case(evaluation_context,monkeypatch,output=8)
    res=evaluation_context[2];prompts=evaluation_context[3];client=res['query_runner'].llm_factory()
    def stream(prompt,**kw):
        prompts.append(prompt)
        usage={'input_tokens':20,'output_tokens':8}
        if reasoning is not None:usage['output_token_details']={'reasoning':reasoning}
        yield SimpleNamespace(content='合成结果。[1]',usage_metadata=usage,response_metadata={'finish_reason':'stop'})
    client.stream=stream
    cfg,res,prompts,q,repo,service,user,data,catalog=formal_case(evaluation_context,tmp_path,monkeypatch)
    job=service.create_experiment(user,data);execute_job(repo,catalog,tmp_path/'run',job['experiment_id'])
    valid=reasoning is None or type(reasoning) is int and 0<=reasoning<=8
    assert repo.get_experiment(user,job['experiment_id'])['state']==('completed' if valid else 'failed')
    ledger=res['db'].diagnostic_output_accounts.find_one({})
    assert ledger['state']==('open' if valid else 'blocked')
    run=res['db'].runs.find_one({})
    assert run['telemetry']['usage_validation']['valid']==valid
    if not valid:assert run['output_settlement']['state']=='blocked'
