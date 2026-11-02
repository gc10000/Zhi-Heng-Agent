"""比较答复048合同与风险档案默认关闭，synthetic only。"""
import pytest


def comparison_contract(*, enabled=False):
    return {
        'enabled': enabled,
        'function_version': 'diagnostic_comparison_answer_048_v1',
        'thinking': False,
        'status': 'unknown',
        'semantics': 'unknown',
        'n': 1,
        'endpoint_sha256': 'a' * 64,
        'model': 'qwen3.8-flash',
        'client_versions': {'openai': '2.28.0', 'langchain-openai': '1.1.11'},
        'limit_field': 'max_completion_tokens',
        'per_request_total_output_tokens': 4096,
        'ledger_id': 'm6-comparison-answer-048-canary-r1',
        'prior_input_tokens': 53089,
        'prior_output_tokens': 30412,
        'prior_source_sha256': 'b' * 64,
        'max_total_input_tokens': 81505,
        'max_total_output_tokens': 34508,
        'admission': {
            'authorization': {
                'commit': 'c' * 40,
                'path': 'docs/development/reviews/M6-comparison-answer-048-authorization-r1.json',
                'sha256': 'd' * 64,
            },
            'manifest_sha256': 'e' * 64,
            'member_slot': 'm6-comparison-answer-048-r1-r1-support-v1-048',
        },
    }


def test_comparison_contract_is_registered_explicit_and_default_off():
    from app.infrastructure.providers.output_contract import (
        ComparisonAnswer048Contract, is_product_risk, parse_contract, payload, require_capability,
    )

    policy = parse_contract(comparison_contract())
    assert isinstance(policy, ComparisonAnswer048Contract)
    assert policy.enabled is False
    assert not is_product_risk(policy)
    assert payload(policy) is None
    assert parse_contract(policy.model_dump(mode='json')) == policy
    assert require_capability(policy) == policy

    from app.answering.service import AnswerBudget
    accepted = AnswerBudget.model_validate({'output_tokens': 4096,
        'output_token_field': 'max_completion_tokens',
        'output_contract': comparison_contract(enabled=True)})
    assert isinstance(accepted.output_contract, ComparisonAnswer048Contract)


def test_enabled_comparison_contract_routes_only_to_its_new_risk_profile():
    from app.infrastructure.providers.output_contract import is_product_risk, parse_contract, risk_handler

    policy = parse_contract(comparison_contract(enabled=True))
    assert is_product_risk(policy)
    assert risk_handler(policy).__name__.endswith('comparison_answer_048_risk')


def test_comparison_contract_rejects_unbounded_or_mutated_identity():
    from app.infrastructure.providers.output_contract import parse_contract

    for change in (
        {'n': 2},
        {'thinking': True},
        {'status': 'verified'},
        {'model': 'another-model'},
        {'limit_field': 'max_tokens'},
        {'per_request_total_output_tokens': 4097},
        {'prior_input_tokens': 0},
        {'max_total_input_tokens': 81504},
        {'max_total_output_tokens': 34507},
        {'ledger_id': 'old-blocked-ledger'},
        {'admission': {'authorization': {'commit': 'c' * 40,
            'path': 'docs/development/reviews/M6-comparison-answer-048-authorization-r1.json',
            'sha256': 'd' * 64}, 'manifest_sha256': 'e' * 64, 'member_slot': 'another-slot'}},
    ):
        bad = comparison_contract(enabled=True) | change
        with pytest.raises(ValueError):
            parse_contract(bad)


def test_comparison_risk_profile_has_no_authorization_or_old_slot_fallback():
    from app.infrastructure.providers import comparison_answer_048_risk as risk
    from app.infrastructure.providers import source_relation_048_risk as old
    from app.infrastructure.providers.output_contract import parse_contract

    policy = parse_contract(comparison_contract(enabled=True))
    assert risk.AUTHORIZED_GIT is None
    assert risk.BATCH != old.BATCH
    assert risk.SLOT != old.SLOT
    assert risk.ACCOUNT_COLLECTION != old.ACCOUNT_COLLECTION
    with pytest.raises(ValueError, match='授权'):
        risk.sources(policy)
    with pytest.raises(ValueError, match='授权'):
        risk.prepare_manifest({'authorization': None})
    with pytest.raises(ValueError, match='授权'):
        risk.open_client(policy)


def test_comparison_prior_usage_requires_the_frozen_receipt_and_source_hashes(tmp_path, monkeypatch):
    from app.infrastructure.providers import comparison_answer_048_risk as risk
    from app.knowledge.repository import fingerprint

    monkeypatch.setattr(risk, 'ROOT', tmp_path)
    source = tmp_path / 'sealed-history.json'
    source.write_text('{"synthetic":true}', encoding='utf8')
    source_ref = {'path': 'sealed-history.json', 'sha256': risk.sha(source)}
    value = {'input_tokens': 53089, 'output_tokens': 30412,
        'sources': {'sealed_history': source_ref}}
    auth = {'prior_usage': value | {'sha256': fingerprint(value)}}
    assert risk.prior_receipt(auth) == value | {'sha256': fingerprint(value)}
    with pytest.raises(ValueError, match='hash'):
        risk.prior_receipt({'prior_usage': value | {'sha256': '0' * 64}})
    with pytest.raises(ValueError, match='53089/30412'):
        risk.prior_receipt({'prior_usage': value | {'input_tokens': 0}})
    with pytest.raises(ValueError, match='来源文件或hash'):
        risk.prior_receipt({'prior_usage': value | {'sources': {
            'sealed_history': source_ref | {'sha256': '0' * 64}}}})


def test_comparison_old_account_check_reads_consumed_comparison_collection(tmp_path, monkeypatch):
    from app.infrastructure.providers import comparison_answer_048_risk as risk
    from app.infrastructure.providers import source_relation_048_risk as consumed
    from app.knowledge.repository import fingerprint

    monkeypatch.setattr(risk, 'ROOT', tmp_path)
    batch = tmp_path / 'output/m6-authorized-products' / consumed.BATCH
    batch.mkdir(parents=True)
    halt = {'reason': 'sealed'}
    (batch / 'halt.json').write_text(__import__('json').dumps(halt), encoding='utf8')
    manifest = {'version': consumed.VERSION, 'batch_slot': consumed.BATCH,
        'dispatch_order': [consumed.SLOT], 'shared_control_database': 'control'}
    (batch / 'planned.json').write_text(__import__('json').dumps(manifest), encoding='utf8')
    saved = {'_id': 'old-account', 'state': 'blocked', 'pending': None,
        'unknown_windows': [], 'settled': {consumed.SLOT: {'completed': True}}, 'halt': halt}
    saved_path = tmp_path / 'account.json'
    saved_path.write_text(__import__('json').dumps(saved), encoding='utf8')
    settlement_path = tmp_path / 'settled.json'
    settlement_path.write_text(__import__('json').dumps({'account': saved}), encoding='utf8')
    auth = {'previous_batch': consumed.BATCH, 'previous_account_snapshot_path': 'account.json',
        'previous_settlement_source_path': 'settled.json',
        'previous_account_snapshot_sha256': risk.sha(saved_path),
        'previous_manifest_sha256': fingerprint(manifest),
        'previous_halt_sha256': risk.sha(batch / 'halt.json'),
        'previous_settlement_source_sha256': risk.sha(settlement_path)}
    monkeypatch.setattr(risk, 'sources', lambda _: (auth, {}, {}, {}))

    class Collection:
        def find_one(self, query):
            self.query = query
            return saved

    class Database:
        def __init__(self):
            self.rows = Collection()
        def __getitem__(self, name):
            self.collection_name = name
            return self.rows

    class Client:
        def __init__(self):
            self.database = Database()
        def __getitem__(self, name):
            self.database_name = name
            return self.database

    client = Client()
    risk.validate_previous_account(None, client)
    assert client.database_name == 'control'
    assert client.database.collection_name == consumed.ACCOUNT_COLLECTION
    assert client.database.collection_name != risk.ACCOUNT_COLLECTION

    auth['previous_account_snapshot_sha256'] = '0' * 64
    with pytest.raises(ValueError, match='blocked状态'):
        risk.validate_previous_account(None, client)


def test_output_ledger_routes_comparison_to_its_own_profile(monkeypatch):
    from app.infrastructure.providers import comparison_answer_048_risk as risk
    from app.infrastructure.providers.output_contract import OutputLedger, parse_contract

    class RoutedLedger:
        def __init__(self, db, contract):
            self.db, self.contract = db, contract

    monkeypatch.setattr(risk, 'ComparisonAnswer048Ledger', RoutedLedger)
    db = object()
    policy = parse_contract(comparison_contract(enabled=True))
    ledger = OutputLedger(db, policy)
    assert isinstance(ledger, RoutedLedger)
    assert ledger.db is db
    assert ledger.contract == policy
