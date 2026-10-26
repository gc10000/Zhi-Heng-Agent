"""受影响题先行必须实际选择子集，不能只改界面数量。"""
import pytest
from app.evaluation.runner import run_experiment
from tests.unit.test_evaluation_dataset import case, freeze


def test_question_subset_executes_only_frozen_dev_members(tmp_path):
    rows=[case('q1','dev','g1'),case('q2','dev','g2'),case('q3','heldout','g3')]
    dataset,manifest,config=freeze(tmp_path,rows)
    config['question_ids']=['q2']
    seen=[]
    def execute(row):
        seen.append(row['id'])
        return dict(answer='合成答案',citations=[])
    report=run_experiment(dataset,manifest,config,tmp_path/'out',execute)
    assert seen==['q2']
    assert report['selected_ids']==['q2']


@pytest.mark.parametrize('ids',[[],['q1','q1'],['heldout'],['missing'],'q1'])
def test_subset_rejects_unknown_duplicate_and_heldout(tmp_path,ids):
    dataset,manifest,config=freeze(tmp_path,[case('q1','dev','g1'),case('heldout','heldout','g2')])
    config['question_ids']=ids
    with pytest.raises(ValueError):
        run_experiment(dataset,manifest,config,tmp_path/'out',lambda row:pytest.fail('非法范围不能调用模型'))
