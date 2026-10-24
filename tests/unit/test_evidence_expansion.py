"""扩展的来源、预算、去重与多样性边界；不调用存储或模型。"""
from copy import deepcopy
import pytest
from app.retrieval.expansion import ExpansionPolicy, expand_evidence
from app.retrieval.models import RetrievalHit


def hit(uid='seed', ordinal=2, **changes):
    value = dict(chunk_uid=uid, document_id='d', revision_id='r', ordinal=ordinal, text='设备参数24V。',
        metadata=dict(section_id='s', product_ids=['AX'], heading_path=['参数'], asset_ids=[],
            source_refs=[dict(document_id='d', revision_id='r', kind='pdf', page=2)]))
    value.update(changes)
    if 'metadata' not in changes:
        value['metadata']['source_refs'][0].update(document_id=value['document_id'],revision_id=value['revision_id'])
    return RetrievalHit(**value)


def row(value, **changes):
    return value.model_dump(exclude={'stages'}) | dict(owner_id='owner', kb_id='kb') | changes


def expand(seeds, rows, **policy):
    return expand_evidence(seeds, loader=lambda *a, **kw: rows, owner_id='owner', kb_id='kb',
        policy=ExpansionPolicy(enabled=True, **policy))


def test_adjacent_chunk_cannot_bypass_its_own_missing_prerequisite():
    seed = hit()
    nearby = hit('nearby',3)
    nearby.metadata['parent_chunk_uid'] = 'absent-parent'
    selected = expand([seed], [row(nearby)])
    assert [h.chunk_uid for h in selected.selected] == ['seed']


def test_parent_and_table_header_are_kept_with_original_source_and_asset():
    seed = hit(); seed.metadata['parent_chunk_uid'] = 'parent'
    parent = hit('parent',0,text='| 参数 | 单位 |\n| 电源 | V |')
    parent.metadata['asset_ids'] = ['exact-image']
    before = deepcopy(parent.model_dump())
    result = expand([seed],[row(parent),row(parent)])
    assert [h.chunk_uid for h in result.selected] == ['parent','seed']
    assert result.selected[0].metadata['asset_ids'] == ['exact-image']
    assert result.expanded[0].stages[0].score_kind == 'parent'
    assert parent.model_dump() == before


@pytest.mark.parametrize('change', [dict(document_id='other'),dict(revision_id='old'),
    dict(metadata=hit().metadata | dict(product_ids=['BX'])),
    dict(metadata=hit().metadata | dict(section_id='other',heading_path=['别章']))])
def test_other_document_revision_product_or_section_not_expanded(change):
    seed=hit(); other=hit('other',3,**change)
    assert expand([seed],[row(other)]).expanded == []


@pytest.mark.parametrize('change', [dict(owner_id='other'),dict(kb_id='other')])
def test_wrong_scope_rejected(change):
    with pytest.raises(ValueError): expand([hit()],[row(hit('near',3),**change)])


def test_missing_parent_or_parent_larger_than_budget_omits_incomplete_seed():
    seed=hit(); seed.metadata['parent_chunk_uid']='parent'
    missing=expand([seed],[])
    assert not missing.selected and missing.excluded[0]['reason']=='parent_unavailable'
    parent=hit('parent',0,text='超预算前提'*500)
    large=expand([seed],[row(parent)],max_chars=300)
    assert not large.selected and large.excluded[0]['reason']=='prerequisite_budget'


def test_seed_diversity_before_optional_neighbours_and_added_limit():
    seeds=[hit(f'a{i}',i) for i in range(4)]+[hit('b',0,document_id='b')]
    result=expand(seeds,[row(hit('adj',4))],max_seeds=2,max_added=0)
    assert [h.document_id for h in result.selected] == ['d','b']
    assert not result.expanded


def test_no_recursive_or_whole_chapter_expansion_and_no_duplicate_text_collapse():
    seed=hit()
    rows=[row(hit(f'other{i}',i)) for i in range(100)]
    result=expand([seed],rows,max_added=1)
    assert len(result.expanded)==1
    assert len(result.selected)==2
    assert result.selected[0].text == result.selected[1].text
    assert result.selected[0].identity != result.selected[1].identity


def test_conflicting_same_identity_and_cross_source_rejected():
    seed=hit()
    with pytest.raises(ValueError): expand([seed],[row(seed,text='篡改正文')])
    bad=hit('near',3); bad.metadata['source_refs'][0]['revision_id']='old'
    with pytest.raises(ValueError): expand([seed],[row(bad)])


def test_disabled_never_calls_loader_or_reorders():
    def forbidden(*a,**kw): pytest.fail('禁用扩展不访问存储')
    seeds=[hit('a'),hit('b')]
    result=expand_evidence(seeds,loader=forbidden,owner_id='owner',kb_id='kb',policy=ExpansionPolicy())
    assert result.selected==seeds and not result.expanded
