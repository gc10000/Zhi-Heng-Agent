"""隔离HTTP/Mongo反馈转草稿；不把合成反馈当真实用户验收。"""
import pytest
pytestmark = pytest.mark.integration


@pytest.fixture
def triage(support_client):
    client, headers, resources, user, cid, rid, citation = support_client
    response = client.post('/api/v1/feedback', headers=headers, json=dict(run_id=rid,
        citation_ids=[citation['citation_id']], category='operation', note='合成反馈：缺少检查前提', client_request_id='triage'))
    assert response.status_code == 201
    resources['db'].users.update_one({'user_id':user.user_id}, {'$set':{'role':'maintainer'}})
    return client, headers, resources, response.json(), citation


def review_data(**changes):
    return dict(expected_version=0, decision='confirm', destination='regression',
        rationale='核对原件后确认需要补充', proposed_question='合成回归：检查前提是什么？',
        proposed_expectation='须先确认设备已断电', client_request_id='review') | changes


def test_confirm_creates_traceable_draft_only_and_is_idempotent(triage):
    client, headers, resources, feedback, citation = triage
    before = list(resources['db'].knowledge_documents.find({}))
    url = '/api/v1/feedback/'+feedback['feedback_id']+'/review'
    response = client.post(url, headers=headers, json=review_data())
    assert response.status_code == 200
    row = response.json()
    assert row['state'] == 'confirmed'
    assert row['draft']['annotation_status'] == 'draft'
    assert row['draft']['run_id'] == feedback['run_id']
    assert row['draft']['source_revisions'] == [dict(document_id=citation['document_id'], revision_id=citation['revision_id'])]
    assert client.post(url, headers=headers, json=review_data()).json() == row
    assert list(resources['db'].knowledge_documents.find({})) == before
    assert client.post(url, headers=headers, json=review_data(rationale='换意见')).status_code == 409


def test_reject_and_stale_version_are_explicit(triage):
    client, headers, resources, feedback, citation = triage
    url='/api/v1/feedback/'+feedback['feedback_id']+'/review'
    assert client.post(url, headers=headers, json=review_data(expected_version=99)).status_code == 409
    response=client.post(url, headers=headers, json=review_data(decision='reject', destination=None,
        proposed_question=None, proposed_expectation=None))
    assert response.status_code == 200
    assert response.json()['state'] == 'rejected' and response.json().get('draft') is None


def test_current_authorization_is_checked_before_listing_or_writing(triage):
    client, headers, resources, feedback, citation = triage
    resources['db'].knowledge_documents.update_one({'document_id':citation['document_id']},{'$set':{'kb_id':'revoked'}})
    assert client.get('/api/v1/feedback?kb_id=k').status_code == 404
    assert client.post('/api/v1/feedback/'+feedback['feedback_id']+'/review', headers=headers,json=review_data()).status_code == 404
    row=resources['db'].support_feedback.find_one({'feedback_id':feedback['feedback_id']})
    assert row['state']=='pending_review' and 'draft' not in row


def test_revision_draft_never_becomes_published_knowledge(triage):
    client, headers, resources, feedback, citation = triage
    response=client.post('/api/v1/feedback/'+feedback['feedback_id']+'/review',headers=headers,
        json=review_data(destination='revision'))
    assert response.status_code==200
    assert response.json()['draft']['publication_state']=='requires_affected_then_full_regression'
    assert resources['db'].knowledge_revisions.count_documents({}) == 1


def test_bound_feedback_revision_cannot_publish_without_ordered_quality_proofs(triage):
    client, headers, resources, feedback, citation = triage
    url='/api/v1/feedback/'+feedback['feedback_id']
    assert client.post(url+'/review',headers=headers,json=review_data(destination='revision')).status_code==200
    gateway=resources['knowledge']()
    repo=gateway.repo('k')
    revision=repo.create_revision(citation['document_id'],'feedback-revision',original_sha256='d'*64,object_key='isolated/new.md')
    response=client.post(url+'/bind-revision',headers=headers,json=dict(expected_version=1,
        document_id=citation['document_id'],revision_id=revision.revision_id,affected_question_ids=['q1']))
    assert response.status_code==200
    assert response.json()['draft']['target_revision_id']==revision.revision_id
    from app.knowledge.publishing import RevisionPublisher
    from app.knowledge.repository import ConflictError
    publisher=RevisionPublisher(repo,None,read_original=None)
    repo.revisions.update_one({'revision_id':revision.revision_id},{'$set':{'status':'validated','validation':{'fixture':'valid'}}})
    publisher.inspect=lambda r:{'fixture':'valid'}
    with pytest.raises(ConflictError,match='反馈|回归'):
        publisher.publish(revision.revision_id,expected_active=citation['revision_id'])
    assert repo.get_document(citation['document_id'])['active_revision_id']==citation['revision_id']
    rejected=client.post(url+'/quality-proof',headers=headers,json=dict(expected_version=2,
        stage='full',experiment_id='unknown',calibration_id='unverified'))
    assert rejected.status_code==409


def test_verified_proofs_publish_only_exact_revision_and_stale_answer_blocks(triage):
    """人工角色为合成测试注入，验证门禁协议，不代表真实人工审核。"""
    from datetime import datetime, timezone
    from app.evaluation.repository import EvaluationRepository
    from app.evaluation.service import EvaluationService
    from app.knowledge.repository import fingerprint, ConflictError
    from app.knowledge.publishing import RevisionPublisher
    from tests.integration.test_evaluation_reviews import payload
    client, headers, resources, feedback, citation = triage
    url='/api/v1/feedback/'+feedback['feedback_id']
    assert client.post(url+'/review',headers=headers,json=review_data(destination='revision')).status_code==200
    repo=resources['knowledge']().repo('k')
    rev=repo.create_revision(citation['document_id'],'candidate',original_sha256='d'*64,object_key='isolated/candidate.md')
    validation={'fixture':'validated','attempt':0}
    repo.revisions.update_one({'revision_id':rev.revision_id},{'$set':{'status':'validated','validation':validation}})
    publisher=RevisionPublisher(repo,None,read_original=None)
    publisher.inspect=lambda revision:validation
    gateway=resources['knowledge']()
    gateway.publisher=lambda kb:publisher
    assert client.post(url+'/bind-revision',headers=headers,json=dict(expected_version=1,
        document_id=citation['document_id'],revision_id=rev.revision_id,affected_question_ids=['q1'])).status_code==200
    evaluations=EvaluationRepository(resources['db'])
    resources['evaluations']=EvaluationService(evaluations,None)
    owner=client.get('/api/v1/me').json()['user']['user_id']
    def reviewed(eid,created,*,candidate=False):
        evaluations.experiments.insert_one(dict(experiment_id=eid,owner_id=owner,kb_id='k',
            client_request_id=eid,state='completed',result_attempt=1,selected_questions=1,
            dataset_sha256='a'*64,manifest_sha256='b'*64,created_at=created,
            corpus_binding=dict(database=repo.db.name,is_full_dev=True,candidate_revisions=[dict(
                document_id=rev.document_id,revision_id=rev.revision_id,validation_sha256=fingerprint(validation))]) if candidate else None))
        evaluations.save_results(eid,1,[dict(id='q1',question='合成测试',category='parameter')],
            [dict(id='q1',status='completed',result=dict(answer='合成答案',citations=[]))])
        sha=fingerprint(client.get('/api/v1/experiments/'+eid+'/results').json()['items'][0])
        for n in (1,2):
            assert client.post('/api/v1/experiments/'+eid+'/reviews',headers=headers,
                json=payload(sha,eid+str(n),n)).status_code==201
    reviewed('base','2020-01-01T00:00:00+00:00')
    cal=client.post('/api/v1/experiments/base/calibrations',headers=headers,
        json=dict(client_request_id='cal',rationale='合成校准测试')).json()['calibration_id']
    reviewed('affected',datetime.now(timezone.utc).isoformat(),candidate=True)
    proof=dict(expected_version=2,stage='affected',experiment_id='affected',calibration_id=cal)
    response=client.post(url+'/quality-proof',headers=headers,json=proof)
    assert response.status_code==200,response.text
    assert client.post(url+'/quality-proof',headers=headers,json=proof).json()==response.json()
    reviewed('full',datetime.now(timezone.utc).isoformat(),candidate=True)
    response=client.post(url+'/quality-proof',headers=headers,json=dict(expected_version=3,
        stage='full',experiment_id='full',calibration_id=cal))
    assert response.status_code==200,response.text
    evaluations.results.update_one({'experiment_id':'full'},{'$set':{'result.answer':'未审新答案'}})
    with pytest.raises(ConflictError): publisher.publish(rev.revision_id,expected_active=citation['revision_id'])
    evaluations.results.update_one({'experiment_id':'full'},{'$set':{'result.answer':'合成答案'}})
    publisher.publish(rev.revision_id,expected_active=citation['revision_id'])
    assert repo.get_document(rev.document_id)['active_revision_id']==rev.revision_id
