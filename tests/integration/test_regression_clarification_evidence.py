"""随机隔离库内的澄清来源/补充原件审核；审核身份与模型均为合成夹具。"""
from copy import deepcopy
import pytest

from app.api.errors import APIError
from tests.integration.test_feedback_regression_lineage import lineage
from tests.unit.test_evaluation_dataset import independent_annotation

pytestmark = pytest.mark.integration


def clarification_case(lineage, separate):
    ledger, user, reviewer, feedback, question, target = lineage
    db = ledger.repo.db
    source_db = db.client[db.name + '_clarification_source'] if separate else db
    if separate:
        for name in ('runs', 'knowledge_documents', 'knowledge_revisions'):
            for row in db[name].find({}):
                source_db[name].insert_one({k:v for k,v in row.items() if k != '_id'})
    source_db.runs.update_one({'run_id':'source-run'}, {'$set':{
        'state':'awaiting_input', 'answer':'', 'candidates':[{'product_id':'synthetic-a'}],
        'resume_point':'product_selection'}})
    db.support_feedback.update_one({'feedback_id':'feedback'}, {'$set':{
        'source_database':source_db.name, 'draft.source_revisions':[]}})
    # 原始澄清没有引用；新增关联仅属于独立审核的标签证据，不补入旧Run或反馈。
    original = source_db.runs.find_one({'run_id':'source-run'})
    old_feedback = db.support_feedback.find_one({'feedback_id':'feedback'})
    draft = deepcopy(question)
    draft['annotation'] = dict(method='source_checked_assistant_draft', status='draft')
    refs = [dict(document_id='doc',revision_id='rev')]
    return ledger,user,reviewer,draft,target,refs,source_db,original,old_feedback


@pytest.mark.parametrize('separate',[False,True])
def test_clarification_reviewed_evidence_binds_and_revalidates(lineage, monkeypatch, separate):
    ledger,user,reviewer,q,target,refs,source_db,original,old = clarification_case(lineage,separate)
    monkeypatch.setattr('app.evaluation.feedback_regression.verify_review_artifact',lambda _:None)
    candidate = ledger.candidate(user,'feedback',q,refs)
    annotation = independent_annotation(q)
    with pytest.raises(APIError): ledger.review(reviewer,candidate['id'],annotation)
    audited = ledger.review(reviewer,candidate['id'],annotation,candidate['evidence_mapping_sha256'])
    assert ledger.review(reviewer,candidate['id'],annotation,candidate['evidence_mapping_sha256']) == audited
    bound = ledger.bind(user,'feedback',target | {'annotation_id':audited['id']})
    assert ledger.validate(user,ledger.reference(bound))['sha256'] == bound['sha256']
    assert bound['source']['source_revisions'] == []
    assert audited['evidence_revisions'][0]['original_sha256'] == 'a'*64
    assert source_db.runs.find_one({'run_id':'source-run'}) == original
    assert ledger.repo.db.support_feedback.find_one({'feedback_id':'feedback'}) == old
    source_db.knowledge_revisions.update_one({'revision_id':'rev'},{'$set':{'original_sha256':'b'*64}})
    with pytest.raises(APIError): ledger.validate(user,ledger.reference(bound))


@pytest.mark.parametrize('separate',[False,True])
@pytest.mark.parametrize('change',['missing','hash','self','revoked','wrong_revision','run_change'])
def test_clarification_evidence_refuses_unverified_mapping(lineage,monkeypatch,separate,change):
    ledger,user,reviewer,q,target,refs,source_db,_,_ = clarification_case(lineage,separate)
    monkeypatch.setattr('app.evaluation.feedback_regression.verify_review_artifact',lambda _:None)
    if change == 'wrong_revision':
        with pytest.raises(APIError): ledger.candidate(user,'feedback',q,[refs[0] | {'revision_id':'missing'}])
        return
    candidate = ledger.candidate(user,'feedback',q,None if change == 'missing' else refs)
    if change == 'revoked':
        source_db.knowledge_documents.update_one({'document_id':'doc'},{'$set':{'kb_id':'revoked'}})
    if change == 'run_change':
        source_db.runs.update_one({'run_id':'source-run'},{'$set':{'candidates':[{'product_id':'changed'}]}})
    with pytest.raises(APIError):
        ledger.review(user if change == 'self' else reviewer,candidate['id'],independent_annotation(q),
            '0'*64 if change == 'hash' else candidate.get('evidence_mapping_sha256'))
    assert ledger.repo.db.regression_annotations.count_documents({}) == 0
    assert ledger.repo.db.regression_bindings.count_documents({}) == 0
