"""聊天是来源记录而非双轮人工；新版规则不可倒写旧校准。全为合成输入。"""
from concurrent.futures import ThreadPoolExecutor
import pytest
from tests.integration.test_evaluation_reviews import review_client, subject, payload, post, rounds

pytestmark = pytest.mark.integration


def observation(sha, key='chat-one'):
    return dict(question_id='q1', subject_sha256=sha, source_message_id=key,
        statement='1.答案正确完整\n2.引用充分\n3.兼容性判断不需要步骤\n4.两图无关',
        scores=dict(factuality=2, citation_support=2, actionability='not_applicable', image_relevance=0),
        rubric_version='question-purpose-v1', actionability_applicable=False,
        applicability_rationale='本题只判断兼容性，没有执行操作目标。')


def test_chat_observation_is_immutable_idempotent_and_not_human_review(review_client):
    client, headers, repo, _ = review_client
    data = observation(subject(client))
    url = '/api/v1/experiments/baseline/observations'
    first = client.post(url, headers=headers, json=data)
    assert first.status_code == 201, first.text
    row = first.json()
    assert row['source_channel'] == 'chat' and row['transcriber_kind'] == 'assistant'
    assert 'reviewer_id' not in row and 'round' not in row and 'human_attested' not in row
    assert client.post(url, headers=headers, json=data).json() == row
    changed = data | {'statement': '修改旧反馈'}
    assert client.post(url, headers=headers, json=changed).status_code == 409
    assert client.get(url).json()['items'] == [row]
    assert repo.db.evaluation_reviews.count_documents({}) == 0
    cal = client.post('/api/v1/experiments/baseline/calibrations', headers=headers,
                      json=dict(client_request_id='cal', rationale='测试聊天不可充当两轮'))
    assert cal.status_code == 409


def test_chat_observation_concurrency_and_message_reuse_protection(review_client):
    client, headers, repo, experiment = review_client
    data = observation(subject(client))
    url = '/api/v1/experiments/baseline/observations'
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(lambda _: client.post(url, headers=headers, json=data), range(4)))
    assert [r.status_code for r in results] == [201]*4
    assert len({r.json()['observation_id'] for r in results}) == 1
    experiment('candidate')
    other = data | {'subject_sha256': subject(client, 'candidate')}
    assert client.post('/api/v1/experiments/candidate/observations', headers=headers, json=other).status_code == 409
    assert repo.db.evaluation_observations.count_documents({}) == 1


@pytest.mark.parametrize('change,code', [
    ({'subject_sha256': 'f'*64},409), ({'statement':'   '},422),
    ({'human_attested':True},422), ({'round':2},422),
    ({'actionability_applicable':True},422)])
def test_chat_observation_rejects_stale_forged_or_inconsistent_input(review_client,change,code):
    client, headers, repo, _ = review_client
    response=client.post('/api/v1/experiments/baseline/observations',headers=headers,
                         json=observation(subject(client))|change)
    assert response.status_code == code, response.text
    assert repo.db.evaluation_observations.count_documents({}) == 0


def test_versioned_applicability_is_bound_to_calibration_and_not_comparable_to_legacy(review_client):
    client, headers, repo, experiment = review_client
    rounds(client,headers)
    cal=client.post('/api/v1/experiments/baseline/calibrations', headers=headers,
        json=dict(client_request_id='legacy',rationale='保留旧规则')).json()
    experiment('candidate')
    repo.experiments.update_one({'experiment_id':'candidate'},{'$set':{'created_at':'2099-01-01'}})
    for n in (1,2):
        data=payload(subject(client,'candidate'),'new-'+str(n),n)
        data.update(rubric_version='question-purpose-v1',actionability_applicable=False,
                    applicability_rationale='兼容性判断不要求操作。')
        data['scores']['actionability']='not_applicable'
        response=post(client,headers,data,'candidate')
        assert response.status_code == 201,response.text
    gate=client.get('/api/v1/experiments/candidate/release-gate',params={'calibration_id':cal['calibration_id']}).json()
    assert gate['status']=='pending'
    assert 'rubric_changed' in gate['reasons'] and 'applicability_changed' in gate['reasons']
    assert repo.db.evaluation_calibrations.find_one({'calibration_id':cal['calibration_id']})['baseline']==cal['baseline']


def test_context_only_images_allow_na_under_explicit_selection_protocol(review_client):
    client,headers,repo,_=review_client
    repo.results.update_one({'experiment_id':'baseline'},{'$set':{'result.image_selection_version':1,
        'result.citations':[dict(document_sha256='a'*64,page=4,asset_sha256='b'*64,image_usage='context')]}})
    data=payload(subject(client))
    assert post(client,headers,data).status_code==201


def test_new_rule_followup_cannot_change_applicability(review_client):
    from tests.integration.test_evaluation_reviews import followup, followup_data
    client,headers,_,_=review_client
    data=payload(subject(client))
    data.update(rubric_version='question-purpose-v1',actionability_applicable=True,
                applicability_rationale='本题要求按顺序接线，步骤适用。')
    data['scores']['actionability']='unknown'
    original=post(client,headers,data).json()
    resolution=followup_data(original)
    resolution['resolutions'].pop('image_relevance')
    response=followup(client,headers,original,resolution)
    assert response.status_code==422,response.text


def test_observation_reference_is_explicit_and_does_not_copy_or_promote_score(review_client):
    client,headers,repo,_=review_client
    url='/api/v1/experiments/baseline/observations'
    row=client.post(url,headers=headers,json=observation(subject(client))).json()
    data=payload(subject(client),kind='assistant')|{'observation_id':row['observation_id']}
    data['scores']['citation_support']=1
    response=post(client,headers,data)
    assert response.status_code==201,response.text
    assert response.json()['scores']['citation_support']==1
    assert response.json()['reviewer_kind']=='assistant'
    invalid=payload(subject(client),'other')|{'observation_id':'missing'}
    assert post(client,headers,invalid).status_code==409
    assert repo.db.evaluation_reviews.count_documents({'reviewer_kind':'human'})==0


def test_observations_authorization_and_csrf_precede_writes(review_client):
    client,headers,repo,_=review_client
    data=observation(subject(client));url='/api/v1/experiments/baseline/observations'
    assert client.post(url,json=data).status_code==403
    assert client.post('/api/v1/experiments/not-owned/observations',headers=headers,json=data).status_code==404
    repo.db.users.update_one({}, {'$set':{'role':'viewer'}})
    assert client.post(url,headers=headers,json=data).status_code==403
    assert client.get(url).status_code==403
    assert repo.db.evaluation_observations.count_documents({})==0


def test_new_rule_calibration_requires_consensus_and_binds_version(review_client):
    client,headers,repo,experiment=review_client
    for eid in ('baseline','new-baseline'):
        if eid!='baseline':experiment(eid)
        for n in (1,2):
            data=payload(subject(client,eid),eid+str(n),n)
            if eid!='baseline' or n==2:
                data.update(rubric_version='question-purpose-v1',actionability_applicable=True,
                            applicability_rationale='本合成题要求操作。')
            assert post(client,headers,data,eid).status_code==201
        r=client.post(f'/api/v1/experiments/{eid}/calibrations',headers=headers,
                      json=dict(client_request_id=eid,rationale='合成校准，不写真实数据'))
        if eid=='baseline':
            assert r.status_code==409
        else:
            assert r.status_code==201
            assert r.json()['baseline']['rubrics']=={'q1':['question-purpose-v1']}
            assert r.json()['baseline']['values']['q1']['actionability']==2


def test_historical_request_retry_and_quality_shape_remain_exact(review_client):
    from app.knowledge.repository import fingerprint
    from app.evaluation.reviews import ReviewService
    from app.identity.models import Principal
    client,headers,repo,_=review_client
    rounds(client,headers)
    original=repo.db.evaluation_reviews.find_one({'client_request_id':'1'})
    data=payload(subject(client),'1',1)
    assert original['request_sha256']==fingerprint({'experiment_id':'baseline',**data})
    assert post(client,headers,data).json()['review_id']==original['review_id']
    user=Principal(**client.get('/api/v1/me').json()['user'])
    _,quality=ReviewService(repo)._quality(user,'baseline')
    assert set(quality)=={'critical','incomplete','values','subjects','review_ids'}
