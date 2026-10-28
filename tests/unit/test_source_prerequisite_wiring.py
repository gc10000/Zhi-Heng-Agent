"""默认关闭的内部配置、身份和读取边界，全部为自编合成数据。"""
from types import SimpleNamespace
import pytest
from tests.unit.test_source_prerequisites import hit


def config(**changes):
    value=dict(enabled=True,scope=dict(owner_id='o',kb_id='k',database='m1_test_isolated',collection='m1_test_isolated',revisions={'d':'r'},product_ids=['p']))
    return value|changes


def test_default_disabled_internal_configuration_does_not_change_public_input():
    from app.retrieval.prerequisites import SourcePrerequisitePolicy
    from app.runs.models import RunInput,InternalRunInput
    assert not SourcePrerequisitePolicy().enabled
    data=dict(question='接口',kb_id='k',client_request_id='one')
    assert InternalRunInput(**data).model_dump(exclude_defaults=True)==RunInput(**data).model_dump(exclude_defaults=True)
    with pytest.raises(ValueError):RunInput(**data,source_prerequisites=config())


@pytest.mark.parametrize('change',[dict(enabled='true'),dict(function_version='other'),dict(max_rows=1001),dict(max_added=5),dict(max_chars=6001),dict(scope=None)])
def test_invalid_execution_configuration_is_not_silently_accepted(change):
    from app.retrieval.prerequisites import SourcePrerequisitePolicy
    with pytest.raises(ValueError):SourcePrerequisitePolicy.model_validate(config(**change))


def test_configuration_identity_and_old_checkpoint_rejection():
    from app.retrieval.prerequisites import SourcePrerequisitePolicy,validate_run_policy
    from app.api.errors import APIError
    policy=SourcePrerequisitePolicy.model_validate(config())
    with pytest.raises(APIError):validate_run_policy({},policy)
    with pytest.raises(APIError):validate_run_policy({'source_prerequisites':policy.model_dump(mode='json')},SourcePrerequisitePolicy())
    validate_run_policy({'source_prerequisites':policy.model_dump(mode='json')},policy)
    validate_run_policy({},SourcePrerequisitePolicy())


def test_strategy_carries_explicit_source_configuration():
    from app.evaluation.strategy import strategy_policies
    p=strategy_policies(dict(strategy='m4-configured',parameters=dict(source_prerequisites=config())))
    assert p.source_prerequisites.enabled and p.source_prerequisites.function_version=='1'


def test_bounded_index_reader_filters_before_loading_and_rejects_overflow():
    from app.knowledge.index import V2Index
    seed=hit('s',8,'接口表',kind='table')
    calls=[]
    class Client:
        def query(self,**kw):calls.append(kw);return []
    repo=SimpleNamespace(owner_id='o',kb_id='k',get_revision=lambda rid:dict(document_id='d'))
    index=V2Index(Client(),'m1_test_isolated')
    assert index.prerequisite_rows(repo,[seed],revision_snapshot=[dict(document_id='d',active_revision_id='r')],product_ids=['p'],max_rows=3)==[]
    assert calls[0]['limit']==4 and 'owner_id == "o"' in calls[0]['filter'] and 'document_id == "d"' in calls[0]['filter'] and 'metadata["product_ids"]' in calls[0]['filter']
    index.client=SimpleNamespace(query=lambda **kw:[{}]*4)
    with pytest.raises(ValueError):index.prerequisite_rows(repo,[seed],revision_snapshot=[dict(document_id='d',active_revision_id='r')],product_ids=['p'],max_rows=3)


@pytest.mark.parametrize('bad',[dict(owner_id='other'),dict(kb_id='other'),dict(revision_id='other'),dict(metadata={'product_ids':['foreign']})])
def test_untrusted_loaded_row_cannot_cross_authorization(bad):
    from app.retrieval.prerequisites import authorized_source_selection,SourcePrerequisitePolicy
    seed=hit('s',9,'接口表',kind='table')
    raw=hit('date',0,'2020 年 07 月',page=1).model_dump(exclude={'stages'})|dict(owner_id='o',kb_id='k')|bad
    with pytest.raises(ValueError):authorized_source_selection([seed],loader=lambda **kw:[raw],policy=SourcePrerequisitePolicy.model_validate(config()),owner_id='o',kb_id='k',revisions=[dict(document_id='d',active_revision_id='r')],product_ids=['p'])


def test_request_identity_changes_with_enabled_version_budget_and_scope():
    from app.runs.models import InternalRunInput
    from app.retrieval.prerequisites import policy_payload
    from app.knowledge.repository import fingerprint
    base=dict(question='接口',kb_id='k',client_request_id='one')
    payloads=[config(),config(max_chars=5000),config(max_added=3),config(scope=dict(owner_id='o',kb_id='k',database='m1_test_isolated',collection='m1_test_isolated',revisions={'d':'r2'},product_ids=['p'])),dict(enabled=False)]
    identities=[fingerprint(InternalRunInput(**base,source_prerequisites=p).model_dump(mode='json')) for p in payloads]
    assert len(set(identities))==len(payloads)
    assert policy_payload(config())['function_version']=='1'


def test_reader_rejects_unknown_revision_before_first_index_read():
    from app.knowledge.index import V2Index
    def forbidden(**kw):pytest.fail('越界种子不能发读取')
    index=V2Index(SimpleNamespace(query=forbidden),'m1_test_isolated')
    seed=hit('s',2,'正文',rev='foreign')
    with pytest.raises(ValueError):index.prerequisite_rows(SimpleNamespace(owner_id='o',kb_id='k'),[seed],revision_snapshot=[dict(document_id='d',active_revision_id='r')],product_ids=['p'])
