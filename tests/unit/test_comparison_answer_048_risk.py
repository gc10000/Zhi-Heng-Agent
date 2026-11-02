"""比较答复048合同与风险档案默认关闭，synthetic only。"""
import pytest


def test_new_authorized_comparison_attempt_uses_fresh_identity():
    from app.infrastructure.providers import comparison_answer_048_risk as risk
    from app.infrastructure.providers import source_relation_048_risk as consumed
    from app.infrastructure.providers.output_contract import (
        COMPARISON_ANSWER_048_AUTHORIZATION_PATH,
        COMPARISON_ANSWER_048_SLOT,
    )

    assert risk.BATCH == 'm6-comparison-answer-048-risk-r3'
    assert risk.SLOT == 'm6-comparison-answer-048-r3-support-v1-048'
    assert risk.BATCH != 'm6-comparison-answer-048-risk-r2'
    assert risk.SLOT != 'm6-comparison-answer-048-r2-r2-support-v1-048'
    assert risk.SLOT == COMPARISON_ANSWER_048_SLOT
    assert risk.AUTHORIZED_GIT['path'] == COMPARISON_ANSWER_048_AUTHORIZATION_PATH
    assert risk.AUTHORIZED_GIT['path'].endswith('M6-comparison-answer-048-authorization-r3.json')
    assert risk.AUTHORIZED_GIT['commit'] != 'bb77462df031088cbfd03b17c100ceaa31d84748'
    assert risk.ACCOUNT_COLLECTION != consumed.ACCOUNT_COLLECTION


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
        'ledger_id': 'm6-comparison-answer-048-canary-r3',
        'prior_input_tokens': 53089,
        'prior_output_tokens': 30412,
        'prior_source_sha256': 'b' * 64,
        'max_total_input_tokens': 81505,
        'max_total_output_tokens': 34508,
        'admission': {
            'authorization': {
                'commit': 'c' * 40,
                'path': 'docs/development/reviews/M6-comparison-answer-048-authorization-r3.json',
                'sha256': 'd' * 64,
            },
            'manifest_sha256': 'e' * 64,
            'member_slot': 'm6-comparison-answer-048-r3-support-v1-048',
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
            'path': 'docs/development/reviews/M6-comparison-answer-048-authorization-r3.json',
            'sha256': 'd' * 64}, 'manifest_sha256': 'e' * 64, 'member_slot': 'another-slot'}},
    ):
        bad = comparison_contract(enabled=True) | change
        with pytest.raises(ValueError):
            parse_contract(bad)


def test_comparison_risk_profile_binds_only_the_new_authorization_and_slot():
    from app.infrastructure.providers import comparison_answer_048_risk as risk
    from app.infrastructure.providers import source_relation_048_risk as old
    from app.infrastructure.providers.output_contract import parse_contract
    from app.answering.reviewed_subjects import evidence_bytes
    import json

    assert risk.AUTHORIZED_GIT == {
        'commit': '4a49b6ae4223edc0f110b4a7ca4f1da0871bfb87',
        'path': 'docs/development/reviews/M6-comparison-answer-048-authorization-r3.json',
        'sha256': '5a3d2d2f03efc94ab2d2748a1df213e524eb40b0ddadd175f72773be007f0293',
    }
    authorized_contract = comparison_contract(enabled=True)
    authorized_contract['admission']['authorization'] = risk.AUTHORIZED_GIT
    policy = parse_contract(authorized_contract)
    authorized = json.loads(evidence_bytes(risk.AUTHORIZED_GIT))
    assert authorized['status'] == 'authorized_for_one_stream_only'
    assert authorized['user_authorization']['question_id'] == risk.QUESTION_ID
    assert authorized['user_authorization']['max_provider_streams'] == 1
    assert authorized['supersedes_failed_attempt']['batch'] == risk.SUPERSEDED_BATCH
    assert authorized['supersedes_failed_attempt']['retry_or_reuse_authorized'] is False
    assert risk.BATCH != old.BATCH
    assert risk.SLOT != old.SLOT
    assert risk.ACCOUNT_COLLECTION != old.ACCOUNT_COLLECTION
    assert policy.admission.authorization.model_dump(mode='json') == risk.AUTHORIZED_GIT
    wrong_policy = parse_contract(comparison_contract(enabled=True))
    with pytest.raises(ValueError, match='固定Git授权'):
        risk.sources(wrong_policy)


def make_authorized_comparison_case(tmp_path, monkeypatch, *, evaluation_control_database=None):
    import copy
    import hashlib
    import json

    from app.infrastructure.providers import comparison_answer_048_risk as risk
    from app.infrastructure.providers.output_contract import parse_contract
    from app.knowledge.repository import fingerprint

    monkeypatch.setattr(risk, 'ROOT', tmp_path)

    def save(relative, value):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return risk.sha(path)

    question = {
        'id': risk.QUESTION_ID,
        'question': '比较两款合成设备的上联介质。',
        'product_names': ['合成A', '合成B'],
        'history': [],
        'split': 'dev',
    }
    dataset_path = tmp_path / 'output/catalog/version-1.jsonl'
    dataset_path.parent.mkdir(parents=True)
    dataset_path.write_text(json.dumps(question, ensure_ascii=False) + '\n', encoding='utf-8')
    dataset_sha256 = risk.sha(dataset_path)
    split_manifest_sha256 = save('output/catalog/version-1-manifest.json', {'version': 1, 'rows': 1})

    config = {
        'strategy': 'm6-comparison-synthetic',
        'target': {
            'database': 'm1_test_m4_comparison_target',
            'collection': 'synthetic_products',
            'owner_id': 'synthetic-owner',
            'kb_id': 'synthetic-kb',
            'bucket': 'synthetic-bucket',
            'object_prefix': 'synthetic/comparison/',
        },
        'parameters': {
            'answer_budget': {
                'context_window': 32768,
                'output_tokens': 4096,
                'reserve_tokens': 256,
                'max_chars': 12000,
            },
            'evidence_attribution': {
                'enabled': True,
                'source_relations': {'enabled': True, 'function_version': 'source_relation_spans_v1'},
                'comparison_answer': {'enabled': True, 'function_version': 'comparison_answer_v1'},
            },
        },
        'question_ids': [risk.QUESTION_ID],
        'dataset_sha256': dataset_sha256,
        'split_manifest_sha256': split_manifest_sha256,
        'versions': {'code': risk.code_version(), 'prompt': 'synthetic-prompt-v1', 'model': 'synthetic'},
        'phase': 'development',
        'split': 'dev',
        'execution_mode': 'real_query_runner',
        'metric_schema_version': 1,
        'experiment_id': risk.SLOT,
    }
    result = {
        'prompt': '合成冻结prompt：只比较设备上联。',
        'context': [{'text': '合成冻结证据原文。'}],
        'groups': [{'group': 'uplink', 'source_ids': ['synthetic-source']}],
        'prompt_reference_map': [{'reference': 1, 'source_id': 'synthetic-source'}],
        'budget': {'input_tokens': 123, 'input_limit': 28416},
    }
    source_config = copy.deepcopy(config)
    source_config['experiment_id'] = 'synthetic-parent-experiment'
    anchor = {'new_config': source_config, 'result': result, 'new_request_key': 'synthetic-request-key'}
    source_input_path = 'output/anchor.json'
    source_input_sha256 = save(source_input_path, anchor)

    execution_manifest = {
        'entries': [{
            'version': 1,
            'ordinal': 27,
            'question_id': risk.QUESTION_ID,
            'source': {'question_sha256': fingerprint(question)},
        }],
    }
    execution_manifest_path = 'output/original-execution.json'
    execution_manifest_sha256 = save(execution_manifest_path, execution_manifest)
    master = {
        'version_sources': [{
            'version': 1,
            'control_database': 'm1_test_m4_comparison_control',
            'owner_id': 'synthetic-owner',
            'kb_id': 'synthetic-kb',
            'dataset_sha256': dataset_sha256,
            'split_manifest_sha256': split_manifest_sha256,
        }],
    }
    master_path = 'output/master.json'
    master_sha256 = save(master_path, master)

    history_path = 'output/history-receipt.json'
    history_source_sha256 = save(history_path, {'sealed': 'synthetic usage receipt'})
    prior = {
        'input_tokens': 53089,
        'output_tokens': 30412,
        'sources': {'history': {'path': history_path, 'sha256': history_source_sha256}},
    }
    prior['sha256'] = fingerprint(prior)

    authorization_ref = {
        'commit': 'c' * 40,
        'path': 'docs/development/reviews/M6-comparison-answer-048-authorization-r3.json',
        'sha256': 'd' * 64,
    }
    member = {
        'version': 1,
        'ordinal': 27,
        'question_id': risk.QUESTION_ID,
        'expected_generation': True,
        'fixed_slot': risk.SLOT,
        'source_input_path': source_input_path,
        'source_input_file_sha256': source_input_sha256,
        'source_config_sha256': fingerprint(source_config),
        'source_result_sha256': fingerprint(result),
        'prompt_utf8_sha256': hashlib.sha256(result['prompt'].encode()).hexdigest(),
        'dataset_sha256': dataset_sha256,
        'split_manifest_sha256': split_manifest_sha256,
    }
    endpoint_sha256 = 'a' * 64
    authorization = {
        'kind': 'coordinator_scoped_comparison_answer_048_authorization',
        'admission_version': risk.VERSION,
        'fixed_batch_slot': risk.BATCH,
        'evaluation_control_database': evaluation_control_database or 'm1_test_m4_comparison_control',
        'single_experimental_change': 'comparison_answer_v1_with_assertion_binding_disabled',
        'risk': {
            'gateway_capability_status': 'unknown',
            'coordinator_accepts_unknown_paid_upper_bound_only_for_this_one_stream': True,
        },
        'members': [member],
        'dispatch_order': [risk.SLOT],
        'original_master_path': master_path,
        'original_master_file_sha256': master_sha256,
        'original_execution_manifest_path': execution_manifest_path,
        'original_execution_manifest_sha256': execution_manifest_sha256,
        'full_dataset_rows_per_version': 1,
        'dev_rows_per_version': 1,
        'heldout_rows_per_version': 0,
        'prior_usage': prior,
        'runtime': {
            'n': 1,
            'model': 'qwen3.8-flash',
            'endpoint_sha256': endpoint_sha256,
            'client_versions': {'openai': '2.28.0', 'langchain-openai': '1.1.11'},
            'limit_field': 'max_completion_tokens',
            'requested_total_output_tokens': 4096,
            'thinking': False,
            'temperature': 0.1,
            'timeout_seconds': 120,
            'sdk_max_retries': 0,
            'stream': True,
        },
        'budget': {
            'context_window': 32768,
            'output_tokens_requested': 4096,
            'reserve_tokens': 256,
            'max_chars': 12000,
            'single_input_limit': 28416,
            'prior_diagnostic_input_tokens': 53089,
            'prior_diagnostic_output_tokens': 30412,
            'max_total_diagnostic_input_tokens': 81505,
            'max_total_diagnostic_output_tokens': 34508,
            'max_new_product_jobs': 1,
            'max_new_product_streams': 1,
            'max_attempts_per_member': 1,
        },
    }
    halt_path = 'output/m6-authorized-products/m6-comparison-answer-048-risk-r2/halt.json'
    old_halt = {
        'retry_authorized': False,
        'failure_code': 'eval_set_version_conflict',
        'authorization_sha256': 'a03ae58460630f43509571e64e669b6152e204985e7cb01975d5c6648f7eea6b',
        'provider_requests': 0,
        'provider_streams': 0,
    }
    authorization['supersedes_failed_attempt'] = {
        'batch': risk.SUPERSEDED_BATCH,
        'halt_path': halt_path,
        'halt_sha256': save(halt_path, old_halt),
        'halt_must_remain_unchanged': True,
        'retry_or_reuse_authorized': False,
    }
    authorization_bytes = json.dumps(authorization).encode('utf-8')
    authorization_ref['sha256'] = hashlib.sha256(authorization_bytes).hexdigest()
    monkeypatch.setattr(risk, 'AUTHORIZED_GIT', authorization_ref)
    from app.answering import reviewed_subjects
    import subprocess

    def git_show(args, *, cwd, capture_output, timeout):
        assert args == ['git', 'show', f"{authorization_ref['commit']}:{authorization_ref['path']}"]
        assert reviewed_subjects.Path(cwd) == reviewed_subjects.Path(reviewed_subjects.__file__).resolve().parents[2]
        assert capture_output is True and timeout == 10
        return subprocess.CompletedProcess(args, 0, stdout=authorization_bytes, stderr=b'')

    reviewed_subjects._git_bytes.cache_clear()
    monkeypatch.setattr(reviewed_subjects.subprocess, 'run', git_show)

    contract = comparison_contract(enabled=True)
    contract['endpoint_sha256'] = endpoint_sha256
    contract['admission']['authorization'] = authorization_ref
    contract['prior_source_sha256'] = risk.prior_receipt(authorization)['sha256']
    policy = parse_contract(contract)
    config['parameters']['answer_budget'].update(
        output_token_field='max_completion_tokens',
        output_contract=policy.model_dump(mode='json'),
    )
    return {
        'risk': risk,
        'policy': policy,
        'config': config,
        'question': question,
        'result': result,
        'authorization': authorization,
        'save': save,
        'fingerprint': fingerprint,
    }


def test_authorized_comparison_freezes_and_validates_the_complete_synthetic_source_path(tmp_path, monkeypatch):
    from app.knowledge.repository import fingerprint

    case = make_authorized_comparison_case(tmp_path, monkeypatch)
    risk = case['risk']
    policy = case['policy']

    auth, member, anchor, parent = risk.sources(policy)
    assert auth['fixed_batch_slot'] == risk.BATCH
    assert member['fixed_slot'] == risk.SLOT
    assert anchor['result']['prompt'] == '合成冻结prompt：只比较设备上联。'
    assert parent['control_database'] == 'm1_test_m4_comparison_control'
    assert risk.authorized_inputs(auth, member) == {
        'id': 'support-v1-048',
        'question': '比较两款合成设备的上联介质。',
        'product_names': ['合成A', '合成B'],
        'history': [],
    }

    manifest = risk.build_manifest([(
        case['config'], case['question'], 'm1_test_m4_comparison_control',
    )])
    assert manifest['dispatch_order'] == ['m6-comparison-answer-048-r3-support-v1-048']
    assert manifest['entries'][0]['question']['question'] == '比较两款合成设备的上联介质。'
    assert manifest['entries'][0]['input_sha256'] == fingerprint({
        'id': 'support-v1-048',
        'question': '比较两款合成设备的上联介质。',
        'product_names': ['合成A', '合成B'],
        'history': [],
    })

    frozen = risk.build_manifest([(
        case['config'], case['question'], 'm1_test_m4_comparison_control',
    )])
    assert frozen == manifest
    policy = policy.model_copy(update={
        'admission': policy.admission.model_copy(update={'manifest_sha256': fingerprint(manifest)}),
    })
    case['config']['parameters']['answer_budget']['output_contract'] = policy.model_dump(mode='json')
    risk.prepare_manifest(manifest)
    assert risk.require(policy) == manifest
    assert risk.validate_config(case['config'], 'm1_test_m4_comparison_control', question=case['question']) == manifest

    with pytest.raises(ValueError, match='不可覆盖'):
        risk.prepare_manifest(manifest | {'artifacts': {'changed': True}})

    changed_config = __import__('copy').deepcopy(case['config'])
    changed_config['target']['collection'] = 'unfrozen_collection'
    with pytest.raises(ValueError):
        risk.validate_config(changed_config, 'm1_test_m4_comparison_control', question=case['question'])

    prompt_state = {
        'prompt_used_docs': case['result']['context'],
        'prompt_reference_map': case['result']['prompt_reference_map'],
        'evidence_groups': case['result']['groups'],
        'prompt_budget': case['result']['budget'] | {'policy': 'synthetic-policy'},
    }
    risk.validate_prompt(policy, case['result']['prompt'], prompt_state)
    with pytest.raises(ValueError, match='prompt'):
        risk.validate_prompt(policy, case['result']['prompt'] + '漂移', prompt_state)


def test_new_comparison_authorization_rejects_modified_old_batch_halt(tmp_path, monkeypatch):
    case = make_authorized_comparison_case(tmp_path, monkeypatch)
    risk = case['risk']
    halt_path = tmp_path / case['authorization']['supersedes_failed_attempt']['halt_path']
    halt_path.write_text('{"retry_authorized":true}', encoding='utf-8')

    with pytest.raises(ValueError, match='旧048失败批次停止证明'):
        risk.sources(case['policy'])


def test_comparison_run_uses_authorized_evaluation_database_separate_from_source_database(tmp_path, monkeypatch):
    official_database = 'product_knowledge_rag_m6_eval_control'
    case = make_authorized_comparison_case(
        tmp_path, monkeypatch, evaluation_control_database=official_database,
    )
    risk = case['risk']

    manifest = risk.build_manifest([(
        case['config'], case['question'], official_database,
    )])

    assert manifest['shared_control_database'] == official_database
    assert manifest['entries'][0]['control_database'] == official_database
    policy = case['policy'].model_copy(update={
        'admission': case['policy'].admission.model_copy(update={
            'manifest_sha256': case['fingerprint'](manifest),
        }),
    })
    case['config']['parameters']['answer_budget']['output_contract'] = policy.model_dump(mode='json')
    risk.prepare_manifest(manifest)
    assert risk.validate_config(case['config'], official_database, question=case['question']) == manifest

    with pytest.raises(ValueError, match='配置|主体|源码|冻结'):
        risk.build_manifest([(
            case['config'], case['question'], 'unauthorized-evaluation-database',
        )])


def test_authorized_comparison_rejects_source_and_question_drift_after_freeze(tmp_path, monkeypatch):
    import copy

    case = make_authorized_comparison_case(tmp_path, monkeypatch)
    risk = case['risk']
    manifest = risk.build_manifest([(
        case['config'], case['question'], 'm1_test_m4_comparison_control',
    )])
    policy = case['policy'].model_copy(update={
        'admission': case['policy'].admission.model_copy(update={
            'manifest_sha256': case['fingerprint'](manifest),
        }),
    })
    case['config']['parameters']['answer_budget']['output_contract'] = policy.model_dump(mode='json')
    risk.prepare_manifest(manifest)

    changed_question = copy.deepcopy(case['question'])
    changed_question['question'] = '改写后的合成问题。'
    with pytest.raises(ValueError, match='身份|不匹配|冻结'):
        risk.validate_config(case['config'], 'm1_test_m4_comparison_control', question=changed_question)

    case['save']('output/anchor.json', case['authorization']['members'][0] | {'tampered': True})
    with pytest.raises(ValueError, match='漂移'):
        risk.sources(policy)


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
