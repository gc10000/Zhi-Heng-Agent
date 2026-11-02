"""比较048单槽账本故障路径；仅写随机隔离Mongo库与合成证据。"""
from concurrent.futures import ThreadPoolExecutor
import pytest

from app.api.errors import APIError

pytestmark = pytest.mark.integration


def contract():
    from tests.unit.test_comparison_answer_048_risk import comparison_contract
    return comparison_contract(enabled=True)


def test_comparison_contract_is_preserved_by_formal_run_creation(mongo_db):
    from app.conversations.repository import ConversationRepository
    from app.conversations.models import ConversationInput
    from app.runs.repository import RunRepository
    from app.runs.service import RunService
    from app.runs.models import InternalRunInput
    from app.identity.models import Principal
    from app.infrastructure.providers.output_contract import identity, validate_run
    conv = ConversationRepository(mongo_db)
    runs = RunRepository(mongo_db, conv)
    user = Principal(user_id='synthetic-owner', username='隔离合同验证',
        role='maintainer', kb_ids=('synthetic-kb',))
    cid = conv.create(user, ConversationInput(kb_id='synthetic-kb'))['conversation_id']
    policy = contract()
    request = InternalRunInput(kb_id='synthetic-kb', question='比较上联方式',
        client_request_id='synthetic-comparison', output_contract=policy,
        comparison_target='device_uplink', comparison_target_reason='explicit_single_target')
    service = RunService(runs)
    first = service.create(user, cid, request)
    second = service.create(user, cid, request)
    assert first['run_id'] == second['run_id']
    row = runs.get(user, first['run_id'])
    validate_run(row, policy)
    assert all(row[key] == value for key, value in identity(policy).items())
    assert row['state'] == 'pending' and row['comparison_target'] == 'device_uplink'
    assert mongo_db.runs.count_documents({}) == 1
    assert mongo_db.diagnostic_comparison_answer_048_accounts.count_documents({}) == 0


def isolated_ledger(mongo_db, tmp_path, monkeypatch, *, separate=False):
    from types import SimpleNamespace
    from app.infrastructure.providers import comparison_answer_048_risk as risk
    from app.infrastructure.providers.output_contract import OutputLedger

    db = mongo_db.client[mongo_db.name]
    control_database = mongo_db.name + '_control' if separate else mongo_db.name
    policy = contract()
    slot = risk.SLOT
    member = {'fixed_slot': slot, 'expected_generation': True}
    anchor = {'result': {'budget': {'input_tokens': 28416}}}
    entry = {
        'member': member,
        'config_subject': {'target': {'database': db.name}},
        'question': {'id': risk.QUESTION_ID},
    }
    manifest = {'shared_control_database': control_database,
        'dispatch_order': [slot], 'entries': [entry]}
    synthetic_auth = {'runtime': {'model': 'synthetic'}, 'budget': {}}

    monkeypatch.setattr(risk, 'require', lambda _: manifest)
    monkeypatch.setattr(risk, 'sources', lambda _: (synthetic_auth, member, anchor, {}))
    monkeypatch.setattr(risk, 'validate_config', lambda *a, **kw: None)
    monkeypatch.setattr(risk, 'validate_runtime', lambda *a, **kw: None)
    monkeypatch.setattr(risk, 'batch_dir', lambda: tmp_path / 'batch')
    monkeypatch.setattr(risk, 'slot_dir', lambda _: tmp_path / 'batch' / 'members' / slot)
    (tmp_path / 'batch' / 'members' / slot).mkdir(parents=True)

    run_id, identity = 'synthetic-run', 'synthetic-identity'
    db.runs.insert_one({'run_id': run_id, 'identity': identity})
    context = {
        'config': {'synthetic': True}, 'question': {'id': risk.QUESTION_ID},
        'control_database': control_database,
        'execution': {'experiment_id': slot, 'attempt': 1, 'config_sha256': 'a' * 64},
    }
    ledger = OutputLedger(db, policy)
    from app.infrastructure.providers.comparison_answer_048_risk import ComparisonAnswer048Ledger
    assert isinstance(ledger, ComparisonAnswer048Ledger)
    return SimpleNamespace(db=db, ledger=ledger, policy=policy, run_id=run_id,
        identity=identity, context=context, risk=risk)


def begin(case):
    case.ledger.begin(case.run_id, case.identity, input_reservation=28416,
        risk_context=case.context)


def settle(case, usage=None, *, completed=True):
    return case.ledger.settle(case.run_id, case.identity,
        usage if usage is not None else {'input': 12, 'output': 18},
        completed=completed,
        product_state={'visible_body': True, 'truncated': False,
            'finish_reason': 'stop', 'observed_reasoning': False},
        logical_calls={'invoke_started': 0, 'stream_started': 1})


@pytest.mark.parametrize('separate', [False, True])
def test_comparison_single_slot_reserves_exact_budget_and_never_reclaims(mongo_db, tmp_path, monkeypatch, separate):
    case = isolated_ledger(mongo_db, tmp_path, monkeypatch, separate=separate)
    begin(case)
    row = case.ledger._read()
    assert row['state'] == 'pending'
    assert row['logical_reservations'] == 1
    assert row['pending']['input_reservation'] == 28416
    assert row['pending']['output_reservation'] == 4096

    settled = settle(case)
    assert settled['state'] == 'awaiting_review'
    assert settled['prior_input_tokens'] == 53089
    assert settled['prior_output_tokens'] == 30412
    assert settled['known_new_input_tokens'] == 12
    assert settled['known_new_output_tokens'] == 18
    assert case.ledger.rows.count_documents({}) == 1
    assert settled['exact_http_requests'] is None and settled['exact_cost'] is None
    assert case.ledger.rows.database.name == (mongo_db.name + '_control' if separate else mongo_db.name)
    with pytest.raises(APIError):
        begin(case)
    assert case.ledger._read()['logical_reservations'] == 1


@pytest.mark.parametrize('separate', [False, True])
def test_comparison_unknown_usage_or_interrupted_stream_blocks_and_keeps_slot(mongo_db, tmp_path, monkeypatch, separate):
    case = isolated_ledger(mongo_db, tmp_path, monkeypatch, separate=separate)
    begin(case)
    blocked = settle(case, {}, completed=False)
    assert blocked['state'] == 'blocked'
    assert blocked['pending'] is None
    assert blocked['logical_reservations'] == 1
    assert blocked['unknown_windows']
    assert case.risk.ACCOUNT_COLLECTION == 'diagnostic_comparison_answer_048_accounts'
    assert blocked['exact_http_requests'] is None and blocked['exact_cost'] is None
    with pytest.raises(APIError):
        begin(case)
    assert case.ledger._read()['logical_reservations'] == 1


def test_comparison_concurrent_reservations_have_one_winner(mongo_db, tmp_path, monkeypatch):
    from app.infrastructure.providers.output_contract import OutputLedger

    case = isolated_ledger(mongo_db, tmp_path, monkeypatch)
    peer = OutputLedger(case.db, case.policy)

    def reserve(ledger):
        try:
            ledger.begin(case.run_id, case.identity, input_reservation=28416,
                risk_context=case.context)
            return True
        except (APIError, FileExistsError):
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(reserve, (case.ledger, peer))) == 1
    saved = case.ledger._read()
    assert saved['job_reservations'] == 1
    assert saved['logical_reservations'] == 1
