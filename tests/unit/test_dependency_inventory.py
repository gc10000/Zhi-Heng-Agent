"""异常安装元数据保留unknown，不能令整份库存失败或丢记录。"""
from email.message import Message
from types import SimpleNamespace
from scripts.verification.dependency_inventory import installed


def test_distribution_without_name_is_retained(monkeypatch):
    good=Message();good['Name']='known';good['License-Expression']='MIT'
    bad=Message()
    monkeypatch.setattr('scripts.verification.dependency_inventory.metadata.distributions',lambda:[
        SimpleNamespace(metadata=good,version='1',files=[]),SimpleNamespace(metadata=bad,version=None,files=[])])
    rows=installed()
    assert len(rows)==2
    assert any(row['name'] is None and row['declared_license']=='unknown' for row in rows)
