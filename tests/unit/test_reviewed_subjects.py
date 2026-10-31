"""合成表格旁挂关系；不包含真实原件、答案或审核身份。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from app.knowledge.models import content_hash, stable_id
from app.knowledge.repository import fingerprint
from tests.unit.test_evidence_attribution import policy, document


def test_subject_policy_is_opt_in_and_default_identity_is_unchanged():
    from app.answering.evidence_attribution import payload
    assert 'reviewed_subjects' not in payload()
    assert 'reviewed_subjects' not in payload(policy())


def test_unverified_subject_config_cannot_be_silently_ignored():
    from app.answering.evidence_attribution import payload
    with pytest.raises(ValueError):
        payload(policy() | {'reviewed_subjects': {'enabled': True}})


def test_subject_binding_uses_table_row_identity_instead_of_matching_text():
    from app.answering.reviewed_subjects import row_chunk_identity
    row=['USB接口','连接设备。']
    first=row_chunk_identity('r', segment_offset=0, table_index=4, row_index=0, cells=row, max_chars=2000)
    second=row_chunk_identity('r', segment_offset=0, table_index=8, row_index=0, cells=row, max_chars=2000)
    assert first != second
    assert first['content_sha256'] == second['content_sha256']


def test_subject_labels_require_verified_binding_and_leave_unknown_pages():
    from app.answering.reviewed_subjects import attach_subject
    doc=document('same');doc['source_refs'][0]['page']=None
    with pytest.raises(ValueError):attach_subject(doc, {'enabled':True})


def test_two_tables_bind_members_and_keep_document_product_and_unknown_row_separate(monkeypatch):
    from tests.unit.subject_fixtures import subject_case,as_doc
    from app.answering.evidence_attribution import evidence_labels
    binding,rows,_,_=subject_case(monkeypatch)
    p=policy();p['documents'][0]['original_sha256']=binding.original_sha256;p['reviewed_subjects']=binding.model_dump(mode='json');p['corpus_snapshot_sha256']=binding.corpus_snapshot_sha256
    labels=evidence_labels([as_doc(r) for r in rows],p)
    assert labels[0]['reviewed_subject']['subject']=='合成扩展台甲'
    assert all(l['reviewed_subject']['subject']=='合成扩展台乙' for l in labels[1:])
    assert all(l['page_status']=='unknown' and l['physical_pages']==[] for l in labels)
    assert labels[-1]['reviewed_subject']['table_physical_page']==14
    assert all(l['products']==['合成网关'] for l in labels)
    assert rows[0]['text']==rows[1]['text'] and rows[0]['chunk_uid']!=rows[1]['chunk_uid']
    unrelated=document('machine-rj45')
    assert 'reviewed_subject' not in evidence_labels([unrelated],p)[0]


@pytest.mark.parametrize('field',['original_bytes','cache_bytes','frozen_manifest_bytes','proof_ref','review_ref'])
def test_proof_source_drift_rejected_at_compile(monkeypatch,field):
    from tests.unit.subject_fixtures import subject_case
    from app.answering.reviewed_subjects import compile_binding
    _,_,kw,_=subject_case(monkeypatch);kw=deepcopy(kw)
    if field.endswith('_bytes'):kw[field]+=b' '
    else:kw[field]['sha256']='e'*64
    with pytest.raises(ValueError):compile_binding(**kw)


@pytest.mark.parametrize('field',['document_id','revision_id','text','ordinal','metadata','chunk_uid'])
def test_frozen_row_mapping_cannot_be_rebound_by_text(monkeypatch,field):
    from tests.unit.subject_fixtures import subject_case
    from app.answering.reviewed_subjects import compile_binding
    _,_,kw,_=subject_case(monkeypatch);kw=deepcopy(kw);row=kw['frozen_rows'][-1]
    row[field]={'section_id':'changed'} if field=='metadata' else 99 if field=='ordinal' else 'changed'
    with pytest.raises((ValueError,KeyError)):compile_binding(**kw)


@pytest.mark.parametrize('change',[{'text':'被改写'}, {'revision_id':'foreign'}, {'ordinal':99}, {'metadata':{}}, {'document_id':'foreign'},
    {'source_refs':[dict(document_id='d',revision_id='r',kind='pdf',page=14)]}])
def test_runtime_relation_rejects_changed_member_and_source(monkeypatch,change):
    from tests.unit.subject_fixtures import subject_case,as_doc
    from app.answering.reviewed_subjects import attach_subject
    binding,rows,_,_=subject_case(monkeypatch)
    with pytest.raises(ValueError):attach_subject(as_doc(rows[-1])|change,binding)


@pytest.mark.parametrize('drift',['scope','body','missing','proof','duplicate'])
def test_authorized_loading_is_exact_and_complete(monkeypatch,drift):
    from tests.unit.subject_fixtures import subject_case
    from app.answering.reviewed_subjects import authorize_members,checked_proof
    binding,rows,_,_=subject_case(monkeypatch)
    if drift=='scope':rows[0]['owner_id']='other'
    if drift=='body':rows[0]['text']='changed'
    if drift=='missing':rows=rows[1:]
    if drift=='proof':
        d=binding.model_dump(mode='json');d['proof']['sha256']='f'*64
        with pytest.raises(ValueError):checked_proof(d)
        return
    if drift=='duplicate':
        d=binding.model_dump(mode='json');d['members'].append(d['members'][0])
        with pytest.raises(ValueError):checked_proof(d)
        return
    with pytest.raises(ValueError):authorize_members(binding,rows,owner_id='o',kb_id='k')


def test_prompt_reference_map_has_subjects_without_changing_source_or_numbering(monkeypatch):
    from tests.unit.subject_fixtures import subject_case,as_doc
    from app.query_process.agent.nodes.node_answer_output import step_2_construct_prompt
    binding,rows,_,_=subject_case(monkeypatch)
    p=policy();p['documents'][0]['original_sha256']=binding.original_sha256;p['reviewed_subjects']=binding.model_dump(mode='json');p['corpus_snapshot_sha256']=binding.corpus_snapshot_sha256
    state=dict(original_query='合成接口比较',history=[],reranked_docs=[as_doc(r) for r in rows],evidence_attribution=p)
    before=deepcopy(state['reranked_docs']);prompt=step_2_construct_prompt(state)
    assert '合成扩展台乙' in prompt and 'table_only_not_row_location' in prompt
    assert state['reranked_docs']==before
    assert [r['reference_number'] for r in state['prompt_reference_map']]==[1,2,3,4]
    assert all(r['page_status']=='unknown' for r in state['prompt_reference_map'])
