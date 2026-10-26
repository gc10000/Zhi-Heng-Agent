"""受控模型宿主只接收实验ID，认证与并发预算先于执行。"""
from uuid import uuid4
from fastapi.testclient import TestClient
from app.infrastructure.model_host import app, evaluation_slot


def test_model_host_evaluation_requires_token_and_valid_uuid(monkeypatch):
    monkeypatch.setenv('MODEL_HOST_TOKEN', 'test-only-host-token')
    from app.evaluation import jobs
    calls = []
    monkeypatch.setattr(jobs, 'run_local_job', calls.append)
    with TestClient(app) as client:
        assert client.post('/evaluation-jobs/'+str(uuid4())).status_code == 401
        headers = {'X-Model-Token': 'test-only-host-token'}
        assert client.post('/evaluation-jobs/not-a-uuid', headers=headers).status_code == 422
        eid = str(uuid4())
        assert client.post('/evaluation-jobs/'+eid, headers=headers).status_code == 200
    assert calls == [eid]


def test_busy_model_host_does_not_start_another_evaluation(monkeypatch):
    monkeypatch.setenv('MODEL_HOST_TOKEN', 'test-only-host-token')
    from app.evaluation import jobs
    calls = []
    monkeypatch.setattr(jobs, 'run_local_job', calls.append)
    assert evaluation_slot.acquire(blocking=False)
    try:
        with TestClient(app) as client:
            result = client.post('/evaluation-jobs/'+str(uuid4()), headers={'X-Model-Token':'test-only-host-token'})
            assert result.status_code == 429
    finally:
        evaluation_slot.release()
    assert calls == []
