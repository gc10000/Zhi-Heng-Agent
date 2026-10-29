"""合成型号与正文的检索词分离；不改路由、原题或生成输入。"""
import pytest
from app.retrieval.query_planner import plan_query
from app.retrieval.search import RetrievalPolicy

PRODUCTS=[dict(product_id='a',model='Vendor AX240',aliases=['甲设备']),dict(product_id='b',model='Vendor BX480',aliases=[])]

def projected(question,products=PRODUCTS):
 from app.retrieval.query_projection import project_scoped_subject
 plan=plan_query(question,products)
 return plan,project_scoped_subject(plan,products)

def test_explicit_scoped_query_policy_is_strict_and_default_unchanged():
 assert RetrievalPolicy().model_dump().get('query_projection')=='original'
 assert RetrievalPolicy(query_projection='scoped_subject_v1').query_projection=='scoped_subject_v1'
 with pytest.raises(ValueError):RetrievalPolicy(query_projection='anything')

def test_confirmed_subject_is_not_repeated_in_function_search():
 before,after=projected('AX240首次登录后应如何修改密码？')
 assert before.original_query==after.original_query=='AX240首次登录后应如何修改密码？'
 assert before.search_queries==('AX240首次登录后应如何修改密码？',)
 assert after.search_queries==('该设备首次登录后应如何修改密码？',)
 assert before.product_ids==after.product_ids==('a',)
 assert before.scope_groups==after.scope_groups

def test_comparison_keeps_both_scopes_and_original_question():
 before,after=projected('比较AX240与BX480的输入要求')
 assert after.search_queries==('比较该设备与该设备的输入要求',)
 assert after.scope_groups==(('a',),('b',)) and before.original_query==after.original_query

@pytest.mark.parametrize('question',['AX241如何登录？','比较AX240与BX481的接口','型号未知，请说明登录方法','什么是通用IP地址？'])
def test_unknown_or_general_never_loses_subject_boundary(question):
 before,after=projected(question)
 assert after==before

@pytest.mark.parametrize('question',['AX240命令`show AX240`如何执行？','AX240输入 <ADDRESS> 是什么意思？','AX240\n```cli\nshow AX240\n```'])
def test_code_and_parameter_text_are_not_projected(question):
 before,after=projected(question)
 assert after==before

def test_accessory_name_versions_and_negative_qualifiers_are_preserved():
 products=[dict(product_id='pc',model='华为擎云 G540',brand='华为',aliases=['G540'])]
 before,after=projected('G540的MateDock 3在2019版是否不支持USB 3.0数据传输？',products)
 assert after.search_queries==('该设备的MateDock 3在2019版是否不支持USB 3.0数据传输？',)
 assert after.original_query==before.original_query

def test_accessory_only_query_does_not_mask_it_as_computer():
 products=[dict(product_id='pc',model='华为擎云 G540',brand='华为',aliases=['G540'])]
 before,after=projected('MateDock 3充电接口支持数据传输吗？',products)
 assert after==before

def test_documented_variant_retains_its_version_boundary():
 products=[dict(product_id='a',model='H3C LA2608',brand='H3C',aliases=[])]
 before,after=projected('2014年6W100版LA2608-GM/GU可以与任意品牌AC互通吗？',products)
 assert after==before

def test_uncertain_unicode_coordinates_fail_closed():
 before,after=projected('ß AX240登录的路径是什么？')
 assert after==before

def test_missing_authorized_product_cannot_project():
 from app.retrieval.query_projection import project_scoped_subject
 plan=plan_query('AX240登录',PRODUCTS)
 with pytest.raises(ValueError):project_scoped_subject(plan,[])


def test_retrieval_executor_consumes_projection_instead_of_silently_ignoring_it():
 from types import SimpleNamespace
 from app.evaluation.retrieval_grid import RetrievalExecutor
 from tests.unit.test_retrieval_grid import fixture_config
 from tests.unit.test_evaluation_dataset import case
 cfg=fixture_config();seen=[]
 entity=dict(document_id='d',revision_id='r',chunk_uid='c',text='合成登录步骤',metadata=dict(source_refs=[dict(kind='pdf',page=2)],asset_ids=[]))
 index=SimpleNamespace(search=lambda repo,text,**kw:seen.append(text) or [dict(entity=entity)])
 repo=SimpleNamespace(kb_id='kb',get_active_revisions=lambda:[dict(document_id='d',active_revision_id='r')])
 products=[dict(product_id='a',model='AX240',aliases=[])]
 gateway=SimpleNamespace(owner_id='owner',repo=lambda kb:repo,index=lambda:index,product_kbs=SimpleNamespace(distinct=lambda *a:['a']),products=SimpleNamespace(collection=SimpleNamespace(find=lambda *a:products)))
 q=case();q.update(question='AX240登录步骤',product_names=['AX240'])
 runner=RetrievalExecutor(cfg,gateway,embedder=lambda texts:dict(dense=[[1.,0.]],sparse=[{1:.5}]),ranker=lambda q,docs:[d|dict(score=.9) for d in docs])
 runner.execute(q,RetrievalPolicy(query_projection='scoped_subject_v1'))
 assert seen==['该设备登录步骤']


def test_compensating_unicode_expansion_and_composition_cannot_fake_coordinate_match():
 before,after=projected('ß AX240 e\u0301登录路径？')
 assert after==before
