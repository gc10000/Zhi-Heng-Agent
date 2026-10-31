"""默认关闭的证据归属候选；只证明输入合同，不证明模型质量。"""
from copy import deepcopy
import pytest
from app.query_process.agent.nodes.node_answer_output import step_2_construct_prompt


def policy():
    return dict(enabled=True,function_version='attributed_assertions_v1',
        scope=dict(owner_id='o',kb_id='k',database='m1_test_attr',collection='m1_test_attr',revisions={'d':'r'},product_ids=['p']),
        corpus_snapshot_sha256='a'*64,documents=[dict(document_id='d',revision_id='r',original_sha256='b'*64)],products={'p':'合成网关'})


def document(uid='c'):
    return dict(document_id='d',revision_id='r',chunk_id=uid,chunk_uid=uid,source='local',title='接口表',text='合成接口支持介质X。',
        metadata=dict(product_ids=['p']),source_refs=[dict(document_id='d',revision_id='r',kind='pdf',page=3)],asset_ids=[])


def test_prompt_uses_exact_source_attribution_and_fixed_assertion_contract():
    state=dict(original_query='比较设备接口',history=[],item_names=['合成网关'],reranked_docs=[document()],evidence_attribution=policy())
    prompt=step_2_construct_prompt(state)
    assert 'attributed_assertions_v1' in prompt
    assert '合成网关' in prompt and 'document_id' in prompt
    assert '物理页' in prompt and '3' in prompt
    assert '不得把当前摘录未包含扩写为原件没有' in prompt
    assert state['prompt_reference_map'][0]['chunk_uid']=='c'
    assert state['prompt_reference_map'][0]['reference_number']==1


def test_missing_attribution_is_unknown_and_not_inferred_from_title():
    from app.answering.evidence_attribution import evidence_labels
    doc=document();doc['metadata']={};doc['source_refs'][0]['page']=None
    result=evidence_labels([doc],policy())[0]
    assert result['products']==[] and result['physical_pages']==[]
    assert result['product_status']=='unknown' and result['page_status']=='unknown'


@pytest.mark.parametrize('change',[dict(document_id='foreign'),dict(revision_id='foreign'),dict(metadata={'product_ids':['foreign']}),
    dict(source_refs=[dict(document_id='foreign',revision_id='r',kind='pdf',page=3)])])
def test_foreign_evidence_rejected_without_guessing(change):
    from app.answering.evidence_attribution import evidence_labels
    with pytest.raises(ValueError):evidence_labels([document()|change],policy())


def test_disabled_prompt_identical_and_inputs_immutable():
    base=dict(original_query='合成问题',item_names=[],history=[],reranked_docs=[document()]);before=deepcopy(base)
    prompt=step_2_construct_prompt(base)
    other=deepcopy(before);other['evidence_attribution']={'enabled':False}
    assert step_2_construct_prompt(other)==prompt
    assert base['reranked_docs']==before['reranked_docs']


def test_policy_is_internal_versioned_and_run_drift_fails_closed():
    from app.answering.evidence_attribution import payload,validate_run_attribution
    from app.runs.models import RunInput,InternalRunInput
    from app.knowledge.repository import fingerprint
    p=payload(policy());data=dict(question='合成题',kb_id='k',client_request_id='q')
    with pytest.raises(ValueError):RunInput(**data,evidence_attribution=p)
    assert InternalRunInput(**data,evidence_attribution=p).evidence_attribution.enabled
    validate_run_attribution(dict(evidence_attribution=p,evidence_attribution_sha256=fingerprint(p)),p)
    with pytest.raises(Exception):validate_run_attribution({},p)
    with pytest.raises(ValueError):payload(policy()|dict(function_version='unreviewed'))


def test_reference_numbers_follow_selected_documents_with_unknown_pages():
    docs=[document('known'),document('unknown')]
    docs[1]['source_refs'][0]['page']=None
    state=dict(original_query='合成问题',reranked_docs=docs,evidence_attribution=policy())
    step_2_construct_prompt(state)
    assert [r['reference_number'] for r in state['prompt_reference_map']]==[1,2]
    assert state['prompt_reference_map'][1]['page_status']=='unknown'
    assert state['prompt_reference_map'][1]['chunk_uid']=='unknown'


def test_adapter_and_repository_keep_formal_reference_map_in_public_result():
    from types import SimpleNamespace
    from app.answering.evidence_attribution import evidence_labels
    from app.evaluation.query_adapter import RealQueryExecutor
    from app.evaluation.repository import EvaluationRepository
    mapping=[dict(evidence_labels([document()],policy())[0],reference_number=1)]
    adapter=object.__new__(RealQueryExecutor)
    adapter.config={'parameters':{'evidence_attribution':policy()}}
    adapter.documents={'d':{'revision_id':'r','original_sha256':'b'*64}}
    adapter.resources={'knowledge':lambda:None}
    row=dict(run_id='r1',state='completed',answer='合成正文[1]',prompt_reference_map=mapping,
        citations=[dict(document_id='d',revision_id='r',chunk_uid='c',source_refs=document()['source_refs'],asset_ids=[])])
    result=adapter.project_result(row)
    assert result['prompt_reference_map']==mapping
    saved=[];repo=object.__new__(EvaluationRepository)
    repo.experiments=SimpleNamespace(find_one=lambda _: {})
    repo.results=SimpleNamespace(replace_one=lambda q,v,**kw:saved.append(v))
    repo.save_results('e',1,[dict(id='q',category='parameter',question='合成问题')],
        [dict(id='q',status='completed',result=result)])
    assert saved[0]['result']['prompt_reference_map']==mapping
