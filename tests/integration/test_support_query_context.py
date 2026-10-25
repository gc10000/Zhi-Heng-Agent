import pytest
from types import SimpleNamespace
from tests.integration.test_query_runs import query_context
from tests.integration.test_run_claim import run_context
from app.support.repository import SupportRepository
from app.support.models import SupportInput
from app.runs.models import RunInput
pytestmark=pytest.mark.integration


def test_real_query_prompt_contains_user_report_and_does_not_reuse_unknown_corrected_model(query_context):
    user,cid,conv,repo,service,g,runner,entity,product=query_context
    support=SupportRepository(conv,repo)
    row=support.update(user,cid,SupportInput(expected_version=0,values={'question':'通信失败','device':'AX-99','symptom':'指示灯熄灭'}))
    # missing_evidence转交不妨碍未来新run携带明确的未知型号，不允许旧目录唯一项自动确认。
    run=service.create(user,cid,RunInput(question='它的电源呢',kb_id='k',client_request_id='corrected-unknown'))
    runner.execute(run['run_id'])
    result=repo.get(user,run['run_id'])
    assert result['state']=='awaiting_input',result.get('error')
    assert result['query_plan']['route']=='clarify'
