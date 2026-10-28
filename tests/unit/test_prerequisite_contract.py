"""新增内部消费者配置不能改变浏览器契约或默认启用。"""
import json
from pathlib import Path
from app.runs.models import RunInput,InternalRunInput


def test_openapi_still_matches_checked_contract():
    from app.main import create_app
    assert create_app().openapi()==json.loads(Path('docs/architecture/openapi-v1.json').read_text('utf8'))
    assert 'source_prerequisites' not in RunInput.model_fields
    assert 'source_prerequisites' in InternalRunInput.model_fields


def test_query_runner_does_not_read_environment_to_enable_source_policy(monkeypatch):
    from app.runs.query_runner import QueryRunner
    from types import SimpleNamespace
    monkeypatch.setenv('SOURCE_PREREQUISITES_JSON','{"enabled":true}')
    runner=QueryRunner(None,SimpleNamespace(events=None),lambda:None)
    try:assert not runner.source_prerequisites.enabled
    finally:runner.close()
