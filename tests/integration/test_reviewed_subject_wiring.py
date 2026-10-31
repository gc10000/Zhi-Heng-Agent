"""受审对象经正式配置/授权/Run/检查点的随机隔离集成，只有合成来源。"""
from copy import deepcopy
from types import SimpleNamespace
import pytest
from app.knowledge.repository import fingerprint
from tests.integration.test_evaluation_run_adapter import evaluation_context
from tests.integration import test_candidate_evidence_quality_fix as prior

pytestmark=pytest.mark.integration


def relation_config(ctx,monkeypatch,base=None):
    from tests.unit.subject_fixtures import subject_case
    from app.answering.reviewed_subjects import compile_binding
    from app.retrieval.combination import rows_digest,payload
    from app.retrieval.source_terms import collect_network_terms
    from app.evaluation.corpus import corpus_snapshot
    from app.knowledge.index import V2Index
    (base or prior.attribution_config)(ctx)
    cfg,_,res,_,_,scoped=ctx;t=cfg['target'];g=res['knowledge']()
    cable=deepcopy(g.index().revision_rows(scoped,cfg['corpus']['documents'][0]['revision_id'])[0])
    _,rows,kw,_=subject_case(monkeypatch,did=cable['document_id'],rid=cable['revision_id'],owner=t['owner_id'],kb=t['kb_id'],pid=cable['metadata']['product_ids'][0])
    for row in rows:row.update(dense_vector=[1.,0.],sparse_vector={1:.5})
    cable['ordinal']=len(rows);rows.append(cable)
    class Index:
        collection=t['collection'];payload=staticmethod(V2Index.payload)
        def revision_rows(self,*a,**kw):return deepcopy(rows)
        def prerequisite_rows(self,*a,**kw):return deepcopy(rows)
        def search(self,*a,**kw):return [dict(entity=deepcopy(r)) for r in rows]
    g.index_factory=Index
    original_sha=kw['corpus_snapshot']['documents'][0]['original_sha256']
    scoped.revisions.update_one({'revision_id':cable['revision_id']},{'$set':{'original_sha256':original_sha}})
    cfg['corpus']['documents'][0]['original_sha256']=original_sha
    g.originals=SimpleNamespace(read=lambda _:kw['original_bytes'])
    snapshot=corpus_snapshot(g,t,cfg['corpus']['documents']);cfg['corpus']['snapshot']=snapshot
    binding=compile_binding(**(kw|dict(frozen_rows=rows,corpus_snapshot=snapshot,corpus_snapshot_sha256=fingerprint(snapshot))))
    combo=cfg['parameters']['retrieval_combination'];combo.update(corpus_snapshot_sha256=fingerprint(snapshot),
        corpus_rows_sha256=rows_digest(rows),terms=collect_network_terms(rows,revision_ids=[cable['revision_id']],product_ids=cable['metadata']['product_ids']),
        reviewed_sources=[dict(document_id=cable['document_id'],revision_id=cable['revision_id'],chunk_uid=cable['chunk_uid'],
            row_sha256=rows_digest([cable]),proof_sha256='b'*64)])
    p=cfg['parameters']['evidence_attribution'];p.update(corpus_snapshot_sha256=fingerprint(snapshot),
        documents=[{k:d[k] for k in ('document_id','revision_id','original_sha256')} for d in snapshot['documents']],
        reviewed_subjects=binding.model_dump(mode='json'))
    return p


@pytest.mark.parametrize('separate',[False,True])
def test_full_formal_identity_and_completed_reuse(evaluation_context,tmp_path,monkeypatch,separate):
    original=prior.attribution_config
    monkeypatch.setattr(prior,'attribution_config',lambda ctx:relation_config(ctx,monkeypatch,original))
    prior.test_formal_attribution_identity_checkpoint_completed_reuse(evaluation_context,tmp_path,monkeypatch,separate)
    row=evaluation_context[2]['db'].runs.find_one({})
    assert any(r.get('reviewed_subject',{}).get('subject')=='合成扩展台乙' for r in row['prompt_reference_map'])


@pytest.mark.parametrize('point',['before_create','after_create','after_link'])
def test_create_and_link_crash_windows(evaluation_context,tmp_path,monkeypatch,point):
    from tests.integration import test_combination_adapter as combo
    monkeypatch.setattr(combo,'configure',lambda ctx:relation_config(ctx,monkeypatch))
    combo.test_crash_before_completion_reuses_fixed_request(evaluation_context,tmp_path,monkeypatch,point)


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('drift',[False,True])
def test_input_drift_before_first_outcome_snapshot(evaluation_context,tmp_path,monkeypatch,separate,drift):
    original=prior.attribution_config
    monkeypatch.setattr(prior,'attribution_config',lambda ctx:relation_config(ctx,monkeypatch,original))
    prior.test_completed_attribution_input_rechecked_before_first_snapshot(evaluation_context,tmp_path,monkeypatch,separate,drift)


@pytest.mark.parametrize('drift',[False,True])
def test_success_checkpoint_output_map_cannot_drift(evaluation_context,tmp_path,monkeypatch,drift):
    original=prior.attribution_config
    monkeypatch.setattr(prior,'attribution_config',lambda ctx:relation_config(ctx,monkeypatch,original))
    prior.test_saved_attribution_checkpoint_rechecks_map_without_generation(evaluation_context,tmp_path,monkeypatch,drift)


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('drift',[False,True])
def test_subject_proof_explicit_continuation(evaluation_context,tmp_path,monkeypatch,separate,drift):
    from tests.integration.diagnostic_recovery import continuation_case
    relation_config(evaluation_context,monkeypatch)
    continuation_case(evaluation_context,tmp_path,monkeypatch,separate=separate,drift=drift,field='evidence_attribution_sha256')
