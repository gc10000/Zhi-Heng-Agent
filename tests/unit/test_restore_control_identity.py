"""共享恢复控制身份不能因切换源/目标而改变；缺失时写前拒绝。"""
from types import SimpleNamespace
import pytest

from scripts.operations.restore_reservations import control_database


def test_control_identity_stays_shared_across_source_and_target(monkeypatch):
    monkeypatch.delenv('M7_RESTORE_CONTROL_DATABASE', raising=False)
    monkeypatch.setenv('M7_PROJECT_NAME', 'zh-m7-ab12cd')
    assert control_database(SimpleNamespace(database='source-a'), SimpleNamespace(database='target-a')) == 'm1_test_m4_rc_ab12cd'
    assert control_database(SimpleNamespace(database='source-b'), SimpleNamespace(database='target-b')) == 'm1_test_m4_rc_ab12cd'


@pytest.mark.parametrize('value', ['', 'production', 'm1_test_m4_src'])
def test_missing_or_unsafe_control_identity_is_rejected_before_io(monkeypatch, value):
    monkeypatch.delenv('M7_PROJECT_NAME', raising=False)
    monkeypatch.setenv('M7_RESTORE_CONTROL_DATABASE', value)
    with pytest.raises(ValueError):
        control_database(SimpleNamespace(database='m1_test_m4_src'), SimpleNamespace(database='m1_test_m4_dst'))
