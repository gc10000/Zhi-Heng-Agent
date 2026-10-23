"""过滤表达式必须转义字符串并强制范围/活动修订。"""
import json
import pytest


def test_scope_and_revision_filter_escape_untrusted_values():
    from app.retrieval.filters import scoped_filter
    value='name" or kb_id != "x\\\n'
    expr=scoped_filter(owner_id='u',kb_id=value,revision_ids=['r1','r2'])
    assert 'kb_id == '+json.dumps(value,ensure_ascii=False) in expr
    assert 'owner_id == "u"' in expr and 'revision_id in ["r1", "r2"]' in expr


def test_empty_active_set_is_deny_all_and_no_numeric_ids():
    from app.retrieval.filters import scoped_filter
    assert 'revision_id in []' in scoped_filter(owner_id='u',kb_id='k',revision_ids=[])
    with pytest.raises(ValueError):scoped_filter(owner_id='u',kb_id='k',revision_ids=[123])
