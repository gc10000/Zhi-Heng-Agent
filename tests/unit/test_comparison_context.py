"""比较上下文在固定总预算内保留每个已召回且已重排的产品范围。"""
from copy import deepcopy
import pytest
from app.retrieval.models import RetrievalHit
from app.retrieval.search import RetrievalPolicy


def h(uid, product):
    return RetrievalHit(chunk_uid=uid,document_id='d-'+product,revision_id='r-'+product,
        text='原件内容'+uid,metadata=dict(product_ids=[product]))


def test_explicit_scope_first_keeps_second_product_without_increasing_limit():
    from app.retrieval.selection import select_context
    rows=[h(str(i),'a') for i in range(12)]+[h('b','b')]
    before=deepcopy(rows)
    chosen=select_context(rows,limit=10,scope_groups=(('a',),('b',)),mode='scope_first_v1')
    assert len(chosen)==10 and chosen[:2]==[rows[0],rows[-1]]
    assert chosen[2:]==rows[1:9] and rows==before


def test_default_and_single_scope_preserve_order():
    from app.retrieval.selection import select_context
    rows=[h(str(i),'a') for i in range(12)]
    assert RetrievalPolicy().comparison_context=='global'
    for mode in ['global','scope_first_v1']:
        assert select_context(rows,limit=10,scope_groups=(('a',),),mode=mode)==rows[:10]


def test_empty_scope_does_not_create_evidence_and_limit_cannot_silently_starve():
    from app.retrieval.selection import select_context
    rows=[h('a','a'),h('b','b')]
    assert select_context(rows[:1],limit=2,scope_groups=(('a',),('b',)),mode='scope_first_v1')==rows[:1]
    with pytest.raises(ValueError):select_context(rows,limit=1,scope_groups=(('a',),('b',)),mode='scope_first_v1')


def test_unknown_policy_rejected():
    with pytest.raises(ValueError):RetrievalPolicy(comparison_context='any')


def test_unauthorized_product_is_not_selected_as_a_comparison_side():
    from app.retrieval.selection import select_context
    with pytest.raises(ValueError):
        select_context([h('x','foreign')],limit=10,scope_groups=(('a',),('b',)),mode='scope_first_v1')
