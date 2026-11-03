"""新授权使用独立r2身份；旧已halt批次不能再次进入当前准入。"""
from copy import deepcopy

import pytest

from app.infrastructure.providers.output_contract import parse_contract
from tests.unit.test_connection_048_admission import contract


def batch_contract(batch):
    value=deepcopy(contract(True))
    value['ledger_id']='m6-connection-comparison-048-'+batch
    value['admission']['member_slot']=value['ledger_id']+'-support-v1-048'
    value['admission']['authorization']['path']='docs/development/reviews/M6-connection-comparison-048-authorization-'+batch+'.json'
    return value


def test_new_r2_contract_uses_separate_fixed_identity():
    from app.infrastructure.providers import connection_comparison_048_risk as risk
    policy=parse_contract(batch_contract('r2'))
    assert policy.ledger_id==risk.BATCH=='m6-connection-comparison-048-r2'
    assert policy.admission.member_slot==risk.SLOT


def test_consumed_r1_contract_is_rejected_by_current_admission():
    with pytest.raises(ValueError):
        parse_contract(batch_contract('r1'))


@pytest.mark.parametrize('field',['ledger_id','member_slot','authorization'])
def test_r2_cannot_wrap_any_old_batch_component(field):
    current=batch_contract('r2');old=batch_contract('r1')
    if field=='ledger_id':current[field]=old[field]
    else:current['admission'][field]=old['admission'][field]
    with pytest.raises(ValueError):parse_contract(current)
