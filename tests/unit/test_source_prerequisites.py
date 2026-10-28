"""自编来源结构反例，不包含真实产品/原件内容。"""
import pytest
from app.retrieval.models import RetrievalHit
from app.retrieval import expansion


def hit(uid,ordinal,text,*,page=3,kind='text',heading=('配件','接口'),doc='d',rev='r',product='p'):
    return RetrievalHit(chunk_uid=uid,document_id=doc,revision_id=rev,ordinal=ordinal,text=text,
        metadata=dict(heading_path=list(heading),product_ids=[product],content_kind=kind,asset_ids=[],
            source_refs=[dict(document_id=doc,revision_id=rev,kind='pdf',page=page)]))


def retain(seeds,rows,**kwargs):
    return expansion.retain_source_prerequisites(seeds,rows,**kwargs)


def test_cover_date_and_nearest_table_object_are_atomic_original_sources():
    date=hit('date',0,'某某公司\n\n2020 年 07 月',page=1,heading=('手册',))
    first=hit('one',3,'了解 外设 Alpha',page=2)
    second=hit('two',9,'了解 外设 Beta',page=3)
    seed=hit('row',11,'充电口 | 不传输数据',kind='table',page=4)
    result=retain([seed],[date,first,second,seed])
    assert [h.chunk_uid for h in result.selected]==['date','two','row']
    assert result.groups==[['date','two','row']]
    assert result.selected[1].text==second.text and result.selected[-1].metadata==seed.metadata


@pytest.mark.parametrize('change',[dict(doc='other'),dict(rev='old'),dict(product='other'),dict(heading=('其他章节',)),dict(page=1)])
def test_unrelated_object_never_becomes_prerequisite(change):
    seed=hit('row',11,'充电口 | 不传输数据',kind='table',page=4)
    obj=hit('other',9,'了解 外设 Gamma',**change)
    assert [h.chunk_uid for h in retain([seed],[obj,seed]).selected]==['row']


def test_newer_section_boundary_and_image_summary_do_not_supply_object():
    seed=hit('row',11,'接口 | 数据',kind='table')
    obj=hit('obj',8,'了解 外设 Alpha')
    boundary=hit('boundary',9,'其他操作',heading=('新章节',))
    image=hit('image',10,'了解 外设 Beta');image.metadata['source_refs'][0]['kind']='image_description'
    assert [h.chunk_uid for h in retain([seed],[obj,boundary,image,seed]).selected]==['row']


def test_cover_date_is_not_arbitrary_date_or_other_product():
    seed=hit('body',11,'操作步骤')
    date=hit('date',0,'示例日期：2020年7月',page=1)
    other=hit('other',1,'2020 年 07 月',page=1,product='other')
    assert [h.chunk_uid for h in retain([seed],[date,other,seed]).selected]==['body']


def test_oversized_or_capped_prerequisite_excludes_dependent_seed():
    seed=hit('row',11,'接口 | 数据',kind='table')
    obj=hit('obj',9,'了解 外设 Alpha\n'+('必要条件'*100))
    assert not retain([seed],[obj,seed],max_chars=100).selected
    assert not retain([seed],[obj,seed],max_added=0).selected


def test_duplicate_sources_deduplicate_and_conflicts_reject():
    date=hit('date',0,'2020 年 07 月',page=1)
    a=hit('a',8,'操作甲');b=hit('b',9,'操作乙')
    result=retain([a,b],[date,a,b]);assert [h.chunk_uid for h in result.selected]==['date','a','b']
    assert result.groups==[['date','a'],['date','b']]
    with pytest.raises(ValueError):retain([a],[a,a.model_copy(update={'text':'冲突'})])


def test_source_refs_and_input_limit_checked():
    seed=hit('row',11,'操作');bad=hit('date',0,'2020 年 07 月',page=1)
    bad.metadata['source_refs'][0]['revision_id']='foreign'
    with pytest.raises(ValueError):retain([seed],[bad,seed])
    with pytest.raises(ValueError):retain([seed],[seed]*1001)


def test_final_prompt_budget_keeps_or_drops_the_entire_source_group():
    from app.answering.service import AnswerBudget,build_budgeted_prompt
    date=hit('date',0,'2020 年 07 月',page=1)
    obj=hit('object',8,'了解 外设 Alpha')
    seed=hit('row',9,'接口 | 数据',kind='table')
    result=retain([seed],[date,obj,seed])
    docs=[h.document() for h in result.selected]
    for budget,expected in [(1000,3),(20,0)]:
        packed=build_budgeted_prompt(docs,[],question='查询',items='',render=lambda **kw:kw['context'],
            budget=AnswerBudget(max_chars=budget),groups=result.groups)
        assert len(packed['used_doc_indices'])==expected


def test_ambiguous_cover_dates_do_not_invent_one_version():
    seed=hit('row',9,'操作')
    dates=[hit('a',0,'2020 年 07 月',page=1),hit('b',1,'2021 年 08 月',page=1)]
    assert [h.chunk_uid for h in retain([seed],[*dates,seed]).selected]==['row']


def test_default_expansion_does_not_enable_prerequisites():
    seed=hit('row',9,'操作')
    def forbidden(*args,**kwargs):pytest.fail('默认禁用路径不能读取前提')
    assert expansion.expand_evidence([seed],loader=forbidden,owner_id='o',kb_id='k',policy=expansion.ExpansionPolicy()).selected==[seed]
