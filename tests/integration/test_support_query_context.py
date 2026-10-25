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


def test_withdrawn_device_blocks_old_history_and_single_catalog_auto_selection(query_context):
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    support = SupportRepository(conv, repo)
    confirmed = support.update(user, cid, SupportInput(expected_version=0,
        values={'device': 'AX-24', 'symptom': '通信失败'}))

    old = service.create(user, cid, RunInput(question='AX-24的电源呢', kb_id='k', client_request_id='old-answer'))
    runner.execute(old['run_id'])
    assert repo.get(user, old['run_id'])['state'] == 'completed'

    withdrawn = support.update(user, cid, SupportInput(expected_version=confirmed['version'], clear_slots=['device']))
    assert withdrawn['slots']['device']['value'] is None

    fresh = service.create(user, cid, RunInput(question='它的电源呢', kb_id='k', client_request_id='after-withdrawal'))
    runner.execute(fresh['run_id'])
    result = repo.get(user, fresh['run_id'])

    assert result['state'] == 'awaiting_input', result.get('error')
    assert result['query_plan']['route'] == 'clarify'
    assert result['query_plan']['reason'] == 'model_required_after_context_reset'
    assert not result.get('answer')


def test_withdrawn_device_allows_explicit_new_model_to_resume_query(query_context):
    from app.knowledge.api import ProductInput
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    support = SupportRepository(conv, repo)
    confirmed = support.update(user, cid, SupportInput(expected_version=0,
        values={'device': 'AX-24', 'symptom': '通信失败'}))
    old = service.create(user, cid, RunInput(question='AX-24的电源呢', kb_id='k', client_request_id='old-explicit'))
    runner.execute(old['run_id'])
    support.update(user, cid, SupportInput(expected_version=confirmed['version'], clear_slots=['device']))

    new_product = g.add_product(user, 'k', ProductInput(kb_id='k', model='AX-48'))
    original_entity = entity
    class Index:
        def search(self, scoped, text, **kwargs):
            assert kwargs['product_ids'] == [new_product['product_id']]
            copied = original_entity | {'metadata': original_entity['metadata'] | {'product_ids': [new_product['product_id']]}}
            return [{'entity': copied}]
    g.index_factory = Index

    fresh = service.create(user, cid, RunInput(question='AX-48的电源呢', kb_id='k', client_request_id='new-explicit'))
    runner.execute(fresh['run_id'])
    result = repo.get(user, fresh['run_id'])
    assert result['state'] == 'completed', result.get('error')
    assert result['query_plan']['reason'] == 'catalog_exact'
    assert result['query_plan']['product_ids'] == [new_product['product_id']]


def test_legacy_withdrawal_snapshot_blocks_old_history_after_upgrade(query_context):
    """r2撤回快照没有subject_withdrawn时，仍按撤回事实隔离旧主体。"""
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    support = SupportRepository(conv, repo)
    confirmed = support.update(user, cid, SupportInput(expected_version=0,
        values={'device': 'AX-24', 'symptom': '通信失败'}))
    old = service.create(user, cid, RunInput(question='AX-24的电源呢', kb_id='k', client_request_id='legacy-old'))
    runner.execute(old['run_id'])
    withdrawn = support.update(user, cid, SupportInput(expected_version=confirmed['version'], clear_slots=['device']))
    fresh = service.create(user, cid, RunInput(question='它的电源呢', kb_id='k', client_request_id='legacy-after'))
    legacy = repo.get(user, fresh['run_id'])['support_snapshot']
    legacy.pop('subject_withdrawn', None)
    legacy['history'] = withdrawn['history']
    repo.runs.update_one({'run_id': fresh['run_id']}, {'$set': {'support_snapshot': legacy}})

    runner.execute(fresh['run_id'])
    result = repo.get(user, fresh['run_id'])
    assert result['state'] == 'awaiting_input', result.get('error')
    assert result['query_plan']['reason'] == 'model_required_after_context_reset'
    assert not result.get('answer')


def test_withdrawn_explicit_product_selection_ignores_old_history(query_context):
    """撤回后选择器传入的新型号不能被旧助手主体冲突阻断。"""
    from app.knowledge.api import ProductInput
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    support = SupportRepository(conv, repo)
    confirmed = support.update(user, cid, SupportInput(expected_version=0,
        values={'device': 'AX-24', 'symptom': '通信失败'}))
    old = service.create(user, cid, RunInput(question='AX-24的电源呢', kb_id='k', client_request_id='selector-old'))
    runner.execute(old['run_id'])
    support.update(user, cid, SupportInput(expected_version=confirmed['version'], clear_slots=['device']))
    new_product = g.add_product(user, 'k', ProductInput(kb_id='k', model='AX-48'))
    original_entity = entity
    class Index:
        def search(self, scoped, text, **kwargs):
            assert kwargs['product_ids'] == [new_product['product_id']]
            copied = original_entity | {'metadata': original_entity['metadata'] | {'product_ids': [new_product['product_id']]}}
            return [{'entity': copied}]
    g.index_factory = Index

    fresh = service.create(user, cid, RunInput(question='它的电源呢', kb_id='k',
        client_request_id='selector-new', product_ids=[new_product['product_id']]))
    runner.execute(fresh['run_id'])
    result = repo.get(user, fresh['run_id'])
    assert result['state'] == 'completed', result.get('error')
    assert result['query_plan']['reason'] == 'explicit_selection'
    assert result['query_plan']['product_ids'] == [new_product['product_id']]


def _prepare_reconfirmed_device(query_context):
    """建立撤回后重新确认的正式入口，并把检索限制在新型号。"""
    from app.knowledge.api import ProductInput
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    support = SupportRepository(conv, repo)
    confirmed = support.update(user, cid, SupportInput(expected_version=0,
        values={'device': 'AX-24', 'symptom': '通信失败'}))
    old = service.create(user, cid, RunInput(question='AX-24的电源呢', kb_id='k', client_request_id='reconfirm-old'))
    runner.execute(old['run_id'])
    assert repo.get(user, old['run_id'])['state'] == 'completed'
    linked = support.update(user, cid, SupportInput(expected_version=confirmed['version'],
        values={'question': old['question']}, run_id=old['run_id']))
    withdrawn = support.update(user, cid, SupportInput(expected_version=linked['version'], clear_slots=['device']))
    new_product = g.add_product(user, 'k', ProductInput(kb_id='k', model='AX-48'))
    reconfirmed = support.update(user, cid, SupportInput(expected_version=withdrawn['version'],
        values={'device': 'AX-48'}))
    original_entity = entity

    class Index:
        def search(self, scoped, text, **kwargs):
            assert kwargs['product_ids'] == [new_product['product_id']]
            copied = original_entity | {'metadata': original_entity['metadata'] | {
                'product_ids': [new_product['product_id']]}}
            return [{'entity': copied}]

    g.index_factory = Index
    return user, cid, repo, service, runner, support, new_product, reconfirmed


def test_reconfirmed_device_is_current_subject_without_explicit_selection(query_context):
    user, cid, repo, service, runner, support, new_product, reconfirmed = _prepare_reconfirmed_device(query_context)
    assert reconfirmed['subject_withdrawn'] is False
    fresh = service.create(user, cid, RunInput(question='它的电源呢', kb_id='k', client_request_id='reconfirm-new'))
    runner.execute(fresh['run_id'])
    result = repo.get(user, fresh['run_id'])
    assert result['state'] == 'completed', result.get('error')
    assert result['query_plan']['product_ids'] == [new_product['product_id']]
    assert result['query_plan']['reason'] in {'explicit_selection', 'confirmed_context'}


def test_legacy_reconfirmed_device_overrides_withdrawal_history(query_context):
    user, cid, repo, service, runner, support, new_product, reconfirmed = _prepare_reconfirmed_device(query_context)
    fresh = service.create(user, cid, RunInput(question='它的电源呢', kb_id='k', client_request_id='legacy-reconfirm-new'))
    legacy = repo.get(user, fresh['run_id'])['support_snapshot']
    legacy.pop('subject_withdrawn', None)
    repo.runs.update_one({'run_id': fresh['run_id']}, {'$set': {'support_snapshot': legacy}})
    runner.execute(fresh['run_id'])
    result = repo.get(user, fresh['run_id'])
    assert result['state'] == 'completed', result.get('error')
    assert result['query_plan']['product_ids'] == [new_product['product_id']]


def test_reconfirmed_device_can_be_withdrawn_again(query_context):
    user, cid, repo, service, runner, support, new_product, reconfirmed = _prepare_reconfirmed_device(query_context)
    withdrawn_again = support.update(user, cid, SupportInput(expected_version=reconfirmed['version'], clear_slots=['device']))
    assert withdrawn_again['subject_withdrawn'] is True
    fresh = service.create(user, cid, RunInput(question='它的电源呢', kb_id='k', client_request_id='reconfirm-withdrawn-again'))
    runner.execute(fresh['run_id'])
    result = repo.get(user, fresh['run_id'])
    assert result['state'] == 'awaiting_input', result.get('error')
    assert result['query_plan']['reason'] == 'model_required_after_context_reset'


def test_unconfirmed_reconfirmation_does_not_clear_withdrawal_boundary(query_context):
    user, cid, conv, repo, service, g, runner, entity, product = query_context
    support = SupportRepository(conv, repo)
    confirmed = support.update(user, cid, SupportInput(expected_version=0,
        values={'device': 'AX-24', 'symptom': '通信失败'}))
    old = service.create(user, cid, RunInput(question='AX-24的电源呢', kb_id='k', client_request_id='unconfirmed-old'))
    runner.execute(old['run_id'])
    linked = support.update(user, cid, SupportInput(expected_version=confirmed['version'],
        values={'question': old['question']}, run_id=old['run_id']))
    withdrawn = support.update(user, cid, SupportInput(expected_version=linked['version'], clear_slots=['device']))
    candidate = support.update(user, cid, SupportInput(expected_version=withdrawn['version'],
        values={'device': 'AX-48'}, confirmed=False))
    assert candidate['subject_withdrawn'] is True
    fresh = service.create(user, cid, RunInput(question='它的电源呢', kb_id='k', client_request_id='unconfirmed-reconfirm'))
    runner.execute(fresh['run_id'])
    result = repo.get(user, fresh['run_id'])
    assert result['state'] == 'awaiting_input', result.get('error')
    assert result['query_plan']['reason'] == 'model_required_after_context_reset'
