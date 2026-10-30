"""来源术语投影仅作隔离检索候选；合成原件、不访问模型。"""
import pytest
from app.retrieval.models import QueryPlan
from app.retrieval.source_terms import collect_network_terms, project_network_terms, VERSION


def row(text='设备融合了OptiNet 网络和无线路由器的功能。',heading='2.1 产品简介'):
    return dict(chunk_uid='c',document_id='d',revision_id='r',text=text,metadata=dict(
        product_ids=['p'],heading_path=[heading],content_kind='text',
        source_refs=[dict(document_id='d',revision_id='r',kind='pdf',page=8)]))


def plan(query='甲和乙的上联方式相同吗？'):
    return QueryPlan(original_query=query,search_queries=(query,),product_ids=('p',),revision_ids=('r',),scope_groups=(('p',),),route='compare')


def test_source_literal_and_fingerprint_preserved():
    terms=collect_network_terms([row()],revision_ids=('r',),product_ids=('p',))
    assert len(terms)==1 and terms[0]['term']=='OptiNet' and terms[0]['source_refs'][0]['page']==8
    assert terms[0]['chunk_sha256'] and VERSION=='source_network_terms_v1'
    assert project_network_terms(plan(),terms,enabled=True).search_queries==('甲和乙的上联方式相同吗？\n原件网络介质术语：OptiNet',)


def test_default_off_and_non_network_questions_unchanged():
    terms=collect_network_terms([row()],revision_ids=('r',),product_ids=('p',))
    assert project_network_terms(plan(),terms)==plan()
    p=plan('如何修改登录密码？');assert project_network_terms(p,terms,enabled=True)==p


@pytest.mark.parametrize('change',[
    dict(heading_path=['附录 故障排除']),dict(content_kind='image_description'),
    dict(source_refs=[dict(document_id='d',revision_id='r',kind='pdf',page=None)]),
])
def test_ineligible_sources_cannot_supply_terms(change):
    r=row();r['metadata'].update(change)
    assert collect_network_terms([r],revision_ids=('r',),product_ids=('p',))==[]


@pytest.mark.parametrize('field,value',[('revision_id','foreign'),('product_ids',['foreign']),('document_id','foreign')])
def test_scope_or_reference_mismatch_rejected(field,value):
    r=row()
    if field=='product_ids':r['metadata'][field]=value
    else:r[field]=value
    with pytest.raises(ValueError):collect_network_terms([r],revision_ids=('r',),product_ids=('p',))


def test_unknown_model_and_code_not_projected():
    terms=collect_network_terms([row()],revision_ids=('r',),product_ids=('p',))
    for p in [plan().model_copy(update={'unconfirmed_tokens':('unknown',)}),plan().model_copy(update={'route':'clarify'}),plan('上联`<IP>`是否配置？')]:
        assert project_network_terms(p,terms,enabled=True)==p


def test_catalog_is_built_without_question_and_keeps_negation_in_query():
    terms=collect_network_terms([row()],revision_ids=('r',),product_ids=('p',))
    p=plan('2014版本是否不支持上联？')
    assert project_network_terms(p,terms,enabled=True).search_queries[0].startswith(p.search_queries[0])


def test_over_budget_terms_do_not_select_favorable_subset():
    rows=[row('AlphaNet 网络、BetaNet 网络、GammaNet 网络。')]
    assert collect_network_terms(rows,revision_ids=('r',),product_ids=('p',))==[]


def test_network_equipment_model_is_not_a_medium():
    rows=[row('融合AlphaNet 网络和其他功能，配合ZX900 网络集中器。')]
    assert [t['term'] for t in collect_network_terms(rows,revision_ids=('r',),product_ids=('p',))]==['AlphaNet']


def test_terms_cannot_be_reused_for_another_revision_or_product():
    terms=collect_network_terms([row()],revision_ids=('r',),product_ids=('p',))
    with pytest.raises(ValueError):project_network_terms(plan().model_copy(update={'revision_ids':('other',)}),terms,enabled=True)
