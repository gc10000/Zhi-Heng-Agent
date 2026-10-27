"""正式运行→评测投影→审阅/校准；模型注入、独立Mongo，非真实人工评分。"""
from types import SimpleNamespace
import pytest
from tests.integration.test_evaluation_reviews import review_client,subject,payload,post
from tests.integration.test_evaluation_run_adapter import evaluation_context
from app.evaluation.query_adapter import RealQueryExecutor

pytestmark=pytest.mark.integration
BOUNDARIES=[('list','1. 接线说明 [1]\n\n    ![图](asset://diagram)'),
            ('escaped-ticks','\\`![图](asset://diagram)\\` [1]')]


@pytest.fixture(params=BOUNDARIES,ids=lambda x:x[0])
def rendered_result(evaluation_context,review_client,request):
    client,headers,repo,_=review_client
    cfg,factory,resources,_,question,_=evaluation_context
    g=resources['knowledge']();entity=g.index_factory().search()[0]['entity']
    entity['metadata']['asset_ids']=['diagram']
    g.db.knowledge_assets.insert_one(dict(asset_id='diagram',document_id=entity['document_id'],
        revision_id=entity['revision_id'],sha256='b'*64,source_refs=[dict(kind='pdf',page=2)]))
    class Model:
        def stream(self,prompt,**kwargs):
            for char in request.param[1]:yield SimpleNamespace(content=char)
    resources['query_runner'].llm_factory=Model
    with RealQueryExecutor(cfg,resource_factory=factory) as execute:result=execute(question)
    repo.save_results('baseline',1,[question|{'category':'parameter'}],[dict(id='q1',status='completed',result=result)])
    return client,headers,repo,resources,result


def test_visible_image_propagates_through_run_adapter_history_and_final(rendered_result):
    client,headers,repo,resources,result=rendered_result
    row=resources['runs'].runs.find_one({'run_id':result['run_id']})
    assert row['state']=='completed'
    assert row['citations'][0]['answer_asset_ids']==['diagram']
    assert row['completion_snapshot']['citations']==row['citations']
    message=resources['conversations'].messages.find_one({'run_id':row['run_id'],'role':'assistant'})
    assert message['citations']==row['citations']
    event=resources['events'].events.find_one({'run_id':row['run_id'],'type':'run.completed'}) if 'events' in resources else resources['db'].run_events.find_one({'run_id':row['run_id'],'type':'run.completed'})
    assert event['payload']['citations']==row['citations']
    assert [c['image_usage'] for c in result['citations'] if c.get('asset_sha256')]==['answer']


def test_visible_image_cannot_be_reviewed_or_calibrated_as_na(rendered_result):
    client,headers,repo,_,result=rendered_result
    for n in (1,2):
        response=post(client,headers,payload(subject(client),'na-'+str(n),n))
        assert response.status_code==422,response.text
    assert repo.db.evaluation_reviews.count_documents({})==0
    response=client.post('/api/v1/experiments/baseline/calibrations',headers=headers,
        json=dict(client_request_id='na-cal',rationale='合成含图结果不能免审'))
    assert response.status_code==409
    assert repo.db.evaluation_calibrations.count_documents({})==0
    # 正常图片评分允许进入校准，不将所有校准一律禁用。
    for n in (1,2):
        data=payload(subject(client),'image-'+str(n),n);data['scores']['image_relevance']=0
        assert post(client,headers,data).status_code==201
    response=client.post('/api/v1/experiments/baseline/calibrations',headers=headers,
        json=dict(client_request_id='image-cal',rationale='合成图片已评为无关，保留0分'))
    assert response.status_code==201 and response.json()['baseline']['values']['q1']['image_relevance']==0


def test_old_context_metadata_cannot_suppress_actual_answer_image(review_client):
    client,headers,repo,_=review_client
    repo.results.update_one({'experiment_id':'baseline'},{'$set':{'result.answer':'![图](/api/v1/assets/diagram)',
        'result.image_selection_version':1,'result.citations':[dict(document_sha256='a'*64,page=2,
        asset_sha256='b'*64,image_usage='context')]}})
    assert post(client,headers,payload(subject(client))).status_code==422


def test_historical_na_reviews_do_not_allow_calibration_for_a_visible_image(review_client):
    """合成旧写入窗口，不修改任何用户审阅；读取投影必须重新核对实际正文。"""
    client,headers,repo,_=review_client
    repo.results.update_one({'experiment_id':'baseline'},{'$set':{'result.answer':'![图](/api/v1/assets/diagram)',
        'result.image_selection_version':1,'result.citations':[dict(document_sha256='a'*64,page=2,
        asset_sha256='b'*64,image_usage='context')]}})
    owner=client.get('/api/v1/me').json()['user']['user_id']
    for n in (1,2):
        repo.db.evaluation_reviews.insert_one(dict(experiment_id='baseline',owner_id=owner,
            reviewer_id=owner,review_id='historical-'+str(n),**payload(subject(client),'old-'+str(n),n)))
    response=client.post('/api/v1/experiments/baseline/calibrations',headers=headers,
        json=dict(client_request_id='old-na-cal',rationale='旧误标N/A不能冻结为null'))
    assert response.status_code==409,response.text
    assert repo.db.evaluation_calibrations.count_documents({})==0
