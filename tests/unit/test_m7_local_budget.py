"""仅合成SQLite预留，无权重或网络。"""
import json
from concurrent.futures import ThreadPoolExecutor
import pytest
from app.infrastructure.queue.demo_model_budget import reserve


def test_model_budget_persistent_concurrency_and_no_refund(tmp_path,monkeypatch):
    ledger=tmp_path/'local.sqlite'; auth=tmp_path/'auth.json'
    auth.write_text(json.dumps(dict(kind='m7_explicit_local_model_authorization_v1',
        limits=dict(texts=64,reranks=8,pairs=512),ledger_path=str(ledger.resolve()),model_configuration={'BGE_DEVICE':'synthetic'})),encoding='utf-8')
    monkeypatch.setenv('M7_DEMO_LOCAL_LEDGER',str(ledger));monkeypatch.setenv('M7_DEMO_LOCAL_AUTHORIZATION',str(auth))
    monkeypatch.setenv('BGE_DEVICE','synthetic')
    def attempt(_):
        try:reserve('embedding',['x']*16);return True
        except ValueError:return False
    with ThreadPoolExecutor(max_workers=8) as pool:assert sum(pool.map(attempt,range(8)))==4
    for i in range(8):reserve('rerank',[['q','p']]*64)
    with pytest.raises(ValueError):reserve('rerank',[['q','p']])
    monkeypatch.setenv('M7_DEMO_LOCAL_LEDGER',str(tmp_path/'other.sqlite'))
    with pytest.raises(ValueError):reserve('embedding',['x'])
