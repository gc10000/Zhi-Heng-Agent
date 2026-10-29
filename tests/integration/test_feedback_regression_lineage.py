"""随机隔离库：合成标签/模型/双轮仅验证协议，绝非真实质量记录。"""
import copy
import json
from types import SimpleNamespace
import pytest

from app.evaluation.feedback_regression import RegressionService
from app.evaluation.catalog import EvaluationCatalog
from app.evaluation.repository import EvaluationRepository
from app.evaluation.service import EvaluationService
from app.api.errors import APIError
from tests.unit.test_evaluation_catalog import create_catalog
from tests.unit.test_evaluation_dataset import independent_annotation

pytestmark = pytest.mark.integration


@pytest.fixture
def lineage(mongo_db, tmp_path):
    _, path, dataset, manifest = create_catalog(tmp_path)
    rows = [json.loads(line) for line in dataset.read_text(encoding='utf-8').splitlines()]
    rows[0]['annotation'] = independent_annotation(rows[0])
    from tests.unit.test_evaluation_dataset import freeze
    from app.evaluation.validate_dataset import file_sha
    _, _, _ = freeze(dataset.parent, rows)
    cfg = path.parent/'configs/dev.yaml'
    cfg.write_text(cfg.read_text(encoding='utf-8').replace(
        next(line.split(': ')[1] for line in cfg.read_text().splitlines() if line.startswith('dataset_sha256:')),
        file_sha(dataset)).replace(next(line.split(': ')[1] for line in cfg.read_text().splitlines()
        if line.startswith('split_manifest_sha256:')), file_sha(manifest)), encoding='utf-8')
    repo = EvaluationRepository(mongo_db)
    catalog = EvaluationCatalog(path)
    user = SimpleNamespace(user_id='creator', role='maintainer', kb_ids=('kb-test',))
    reviewer = SimpleNamespace(user_id='control_assistant', role='maintainer', kb_ids=('kb-test',))
    run = dict(run_id='source-run', owner_id='creator', kb_id='kb-test', state='completed',
               answer='明确标识的合成旧答案', citations=[], revision_snapshot=[])
    mongo_db.runs.insert_one(run)
    mongo_db.knowledge_documents.insert_one(dict(document_id='doc',owner_id='knowledge',kb_id='kb-test'))
    mongo_db.knowledge_revisions.insert_one(dict(document_id='doc',revision_id='rev',owner_id='knowledge',
        kb_id='kb-test',original_sha256='a'*64))
    feedback = dict(feedback_id='feedback', run_id='source-run', owner_id='creator', kb_id='kb-test',
        state='confirmed', version=1, reviewer_id='creator', draft=dict(kind='regression', question=rows[0]['question'],
        proposed_expectation='24 V', source_revisions=[dict(document_id='doc',revision_id='rev')]))
    mongo_db.support_feedback.insert_one(feedback)
    service = RegressionService(repo, catalog)
    target = dict(dataset_id='support-dev', dataset_version='r1', config_id='control', config_version='v1', question_id='q0')
    return service, user, reviewer, feedback, rows[0], target


def test_exact_frozen_binding_is_immutable_and_consumed_by_request(lineage):
    service, user, _, feedback, question, target = lineage
    bound = service.bind(user, feedback['feedback_id'], target)
    assert service.bind(user, feedback['feedback_id'], target) == bound
    assert bound['question_sha256'] == service.digest(question)
    ev = EvaluationService(service.repo, service.catalog)
    ev.register_set(user, dict(kb_id='kb-test', eval_set_id='support-dev', version='r1'))
    data = dict(kb_id='kb-test', eval_set_id='support-dev', eval_set_version='r1', config_id='control',
                config_version='v1', client_request_id='create', regression_source=service.reference(bound))
    job = ev.create_experiment(user, data)
    saved = service.repo.get_experiment(user, job['experiment_id'])
    assert saved['regression_source'] == data['regression_source']
    assert ev.create_experiment(user, data) == job
    with pytest.raises(APIError):
        ev.create_experiment(user, data | {'regression_source': data['regression_source'] | {'sha256':'0'*64}})


def test_changed_label_requires_independent_review_and_derives_new_version(lineage,monkeypatch):
    service, user, reviewer, feedback, question, target = lineage
    changed = copy.deepcopy(question)
    changed['annotation'] = dict(method='source_checked_assistant_draft', status='draft')
    changed['expected']['key_points'] = ['合成修正后的完整行为']
    candidate = service.candidate(user, feedback['feedback_id'], changed)
    reviewed = independent_annotation(changed)
    with pytest.raises(APIError): service.review(user, candidate['id'], reviewed)
    with pytest.raises(APIError): service.review(reviewer,candidate['id'],reviewed)
    # 明确合成文档审核夹具；真实入口仍核对git artifact，单独覆盖拒绝路径。
    monkeypatch.setattr('app.evaluation.feedback_regression.verify_review_artifact',lambda annotation:None)
    audited = service.review(reviewer, candidate['id'], reviewed)
    assert service.review(reviewer, candidate['id'], reviewed) == audited
    bound = service.bind(user, feedback['feedback_id'], target | {'annotation_id':audited['id']})
    assert bound['dataset_version'] != 'r1'
    assert bound['parent']['dataset_version'] == 'r1'
    assert service.validate(user, service.reference(bound))['sha256'] == bound['sha256']


def test_http_binding_authorization_and_strict_proof_input(lineage,m2_client):
    service,_,_,feedback,question,target=lineage
    client,headers,resources=m2_client
    from app.identity.models import Principal
    user_data=client.get('/api/v1/me').json()['user']
    resources['db'].users.update_one({'user_id':user_data['user_id']},{'$set':{'role':'maintainer','kb_ids':['kb-test']}})
    from app.knowledge.gateway import KnowledgeGateway
    gateway=KnowledgeGateway(resources['db'],None,owner_id='knowledge')
    resources['knowledge']=lambda:gateway
    resources['evaluations']=EvaluationService(service.repo,service.catalog)
    response=client.post('/api/v1/feedback/feedback/regression-binding',headers=headers,json=target)
    assert response.status_code==201,response.text
    status=client.get('/api/v1/feedback/feedback/regression-status',headers=headers)
    assert status.status_code==200 and status.json()['binding_status']=='valid'
    assert status.json()['quality_passed'] is None
    assert client.post('/api/v1/feedback/feedback/regression-binding',headers=headers,json=target).json()==response.json()
    proof=dict(source=service.reference(response.json()),experiment_id='absent',calibration_id='absent',passed=True)
    assert client.post('/api/v1/feedback/feedback/regression-proof',headers=headers,json=proof).status_code==422
    resources['db'].knowledge_documents.update_one({'document_id':'doc'},{'$set':{'kb_id':'revoked'}})
    assert client.post('/api/v1/feedback/feedback/regression-binding',headers=headers,json=target).status_code==404
    assert client.get('/api/v1/feedback/feedback/regression-status',headers=headers).status_code==404


@pytest.mark.parametrize('point',['regression_candidates','regression_annotations','regression_bindings'])
def test_db_ack_loss_same_identity_recovers(lineage,monkeypatch,point):
    service,user,reviewer,feedback,question,target=lineage
    changed=copy.deepcopy(question)
    changed['expected']['key_points']=['合成变更']
    changed['annotation']=dict(method='source_checked_assistant_draft',status='draft')
    monkeypatch.setattr('app.evaluation.feedback_regression.verify_review_artifact',lambda _:None)
    real=service.store
    def lose_ack(collection,*args,**kwargs):
        value=real(collection,*args,**kwargs)
        if collection.name==point: raise SystemExit('合成写入成功、应答丢失')
        return value
    def recover(action):
        monkeypatch.setattr(service,'store',lose_ack)
        try: action()
        except SystemExit: pass
        monkeypatch.setattr(service,'store',real)
        return action()
    candidate=recover(lambda:service.candidate(user,'feedback',changed))
    reviewed=recover(lambda:service.review(reviewer,candidate['id'],independent_annotation(changed)))
    bound=recover(lambda:service.bind(user,'feedback',target | {'annotation_id':reviewed['id']}))
    assert service.validate(user,service.reference(bound))['sha256']==bound['sha256']
    for name in ('regression_candidates','regression_annotations','regression_bindings'):
        assert service.repo.db[name].count_documents({})==1


def test_same_question_with_different_feedback_expectation_is_not_exact_match(lineage):
    service,user,_,_,_,target=lineage
    service.repo.db.support_feedback.update_one({'feedback_id':'feedback'},
        {'$set':{'draft.proposed_expectation':'合成相反预期：应当拒绝回答'}})
    with pytest.raises(APIError): service.bind(user,'feedback',target)


def test_readonly_status_distinguishes_binding_from_quality(lineage):
    service,user,_,_,_,target=lineage
    assert service.status(user,'feedback')['binding_status']=='unbound'
    bound=service.bind(user,'feedback',target)
    before={n:service.repo.db[n].count_documents({}) for n in service.repo.db.list_collection_names()}
    value=service.status(user,'feedback')
    assert value['binding_status']=='valid' and value['source']==service.reference(bound)
    assert value['proof_status']=='absent' and value['quality_passed'] is None
    assert before=={n:service.repo.db[n].count_documents({}) for n in service.repo.db.list_collection_names()}
    service.repo.db.runs.update_one({'run_id':'source-run'},{'$set':{'answer':'changed'}})
    assert service.status(user,'feedback')['binding_status']=='invalid'


@pytest.mark.parametrize('change', ['heldout', 'draft', 'feedback', 'source_run', 'wrong_owner', 'wrong_hash'])
def test_untrusted_or_changed_sources_rejected(lineage, change):
    service, user, _, feedback, question, target = lineage
    if change in {'heldout', 'draft'}:
        with pytest.raises(APIError): service.bind(user, 'feedback', target | {'question_id':'q49' if change=='heldout' else 'q1'})
        return
    bound = service.bind(user, 'feedback', target)
    ref = service.reference(bound)
    if change=='feedback': service.repo.db.support_feedback.update_one({'feedback_id':'feedback'}, {'$inc':{'version':1}})
    if change=='source_run': service.repo.db.runs.update_one({'run_id':'source-run'}, {'$set':{'answer':'changed'}})
    if change=='wrong_owner': user = SimpleNamespace(user_id='other', role='maintainer', kb_ids=('kb-test',))
    if change=='wrong_hash': ref['sha256']='0'*64
    with pytest.raises(APIError): service.validate(user, ref)
