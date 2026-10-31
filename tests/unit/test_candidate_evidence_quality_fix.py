"""候选证据修复反例：合成内容，不连接数据库或模型。"""
from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import patch
import pytest
from app.evaluation.review_repairs import ReviewRepairs
from app.evaluation.reviews import DIMENSIONS
from app.evaluation.repository import EvaluationRepository
from app.evaluation.query_adapter import RealQueryExecutor


def effective(*, replaced, original_checked, replacement_checked, rule=False, original_critical=()):
    targets=[];originals=[];seals=[]
    for i,dimensions in enumerate(replaced):
        q=f'q{i}'
        targets.append(dict(question_id=q,replace_dimensions=dimensions,correct_actionability_na=rule,
            actionability_applicable=False if rule else None,rationale='合成非操作题'))
        for n in (1,2):
            originals.append(dict(question_id=q,round=n,review_id=f'old-{i}-{n}',review_execution_id=f'old-{n}',reviewer_id='old',
                scores={d:1 for d in DIMENSIONS},dimension_evidence={d:'合成旧来源' for d in DIMENSIONS},
                critical_errors=list(original_critical),source_checked=original_checked[i]))
    for n in (1,2):
        seals.append((dict(round=n,id=f'new-{n}',sha256=f'new-sha-{n}',execution_id=f'new-exec-{n}',reviewer_id='new',
            judgments=[dict(question_id=f'q{i}',scores={d:2 for d in dims},dimension_evidence={d:'合成新来源' for d in dims},
                critical_errors=[],source_checked=replacement_checked[i][n-1]) for i,dims in enumerate(replaced) if dims]),{}))
    case=dict(id='case',sha256='case-sha',scope={},targets=targets,original_seal_hashes=['old'],controller_id='controller',artifact={})
    att=dict(id='att',scope={},case_sha256='case-sha',original_seal_hashes=['old'],repair_seal_hashes=sorted(s['sha256'] for s,_ in seals),controller_id='controller',artifact={})
    r=object.__new__(ReviewRepairs);r.active=lambda _:case;r.case=lambda *args:(case,[],originals)
    r._repair_pairs=lambda _:seals;r.policy=SimpleNamespace(checked=lambda _:None)
    r.db=SimpleNamespace(evaluation_review_repair_attestations=SimpleNamespace(find_one=lambda _:att))
    before=deepcopy(originals)
    with patch('app.evaluation.review_repairs.dp.verify_artifact',lambda _:None):rows,_=r.effective(None,'experiment')
    assert originals==before
    assert all(r['critical_errors']==list(original_critical) for r in rows)
    return rows


@pytest.mark.parametrize('dims,old,new,expected',[
    (list(DIMENSIONS),False,(True,True),(True,True)),
    (['citation_support'],False,(True,True),(False,False)),
    (list(DIMENSIONS),True,(False,False),(False,False)),
    (list(DIMENSIONS),True,(True,True),(True,True)),
    (list(DIMENSIONS),False,(True,False),(True,False)),
])
def test_checked_follows_all_actually_selected_dimensions(dims,old,new,expected):
    rows=effective(replaced=[dims],original_checked=[old],replacement_checked=[new],original_critical=['wrong_object'])
    assert tuple(r['source_checked'] for r in rows)==expected


def test_multiple_selected_judgments_do_not_share_last_checked_flag():
    rows=effective(replaced=[list(DIMENSIONS)]*2,original_checked=[False,True],replacement_checked=[(True,True),(False,True)])
    assert [r['source_checked'] for r in rows]==[True,True,False,True]


def test_rule_na_alone_does_not_prove_unchecked_sources():
    rows=effective(replaced=[[]],original_checked=[False],replacement_checked=[(True,True)],rule=True)
    assert all(not r['source_checked'] and r['scores']['actionability']=='not_applicable' for r in rows)


def test_repository_preserves_public_state_and_sanitized_candidates():
    saved=[]
    repo=object.__new__(EvaluationRepository)
    repo.experiments=SimpleNamespace(find_one=lambda _: {})
    repo.results=SimpleNamespace(replace_one=lambda query,value,**kw:saved.append(value))
    result=dict(state='awaiting_input',behavior='clarify',answer='',citations=[],
        candidates=[dict(product_id='p',model='合成型号',owner_id='private',secret='private')],worker_token='private')
    repo.save_results('e',1,[dict(id='q',category='clarification',question='合成题')],[dict(id='q',status='completed',result=result)])
    assert saved[0]['result']['state']=='awaiting_input'
    assert saved[0]['result']['candidates']==[dict(product_id='p',model='合成型号')]
    assert 'worker_token' not in saved[0]['result']
    assert result['candidates'][0]['secret']=='private'


def test_adapter_clarification_uses_only_authorized_public_candidates():
    adapter=object.__new__(RealQueryExecutor);adapter.config={};adapter.products={'合成型号':'p'}
    result=adapter.project_result(dict(run_id='r',state='awaiting_input',
        candidates=[dict(product_id='p',model='合成型号',worker_token='private'),dict(product_id='other',model='越权')]))
    assert result['candidates']==[dict(product_id='p',model='合成型号')]
