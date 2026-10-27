"""真实语法边界，不使用数据库或模型。"""
import pytest
from app.answering.image_selection import answer_assets, select_answer_images


@pytest.mark.parametrize('body,expected',[
    ('![图](/api/v1/assets/a)',{'a'}),('![图](asset://a)',{'a'}),
    ('`![图](asset://a)`',set()),('``![图](asset://a)``',set()),
    ('```markdown\n![图](asset://a)\n```',set()),('~~~\n![图](asset://a)\n~~~',set()),
    ('    ![图](asset://a)',set()),('\\![图](asset://a)',set()),
    ('![图](https://host/a)',set()),('![图](asset://unknown)',set()),
    ('[链接](asset://a)',set()),('![图][ref]\n[ref]: asset://a',set()),
    ('![图](asset://a)\n```\n![图](asset://b)',{'a'}),
])
def test_only_controlled_explicit_images_are_selected(body,expected):
    assert answer_assets(body,{'a','b'})==expected


def test_selection_keeps_original_evidence_and_does_not_mutate_it():
    original=[{'asset_ids':['a','b'],'text':'证据'}]
    out=select_answer_images('![图](asset://a)',original)
    assert out[0]['answer_asset_ids']==['a'] and out[0]['asset_ids']==['a','b']
    assert 'answer_asset_ids' not in original[0]
