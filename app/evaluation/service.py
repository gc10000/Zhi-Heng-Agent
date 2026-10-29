"""登记目录和所有者账本的应用服务；不在HTTP请求执行模型。"""
from app.api.errors import APIError
from .repository import public_experiment


class EvaluationService:
    def __init__(self, repository, catalog):
        self.repo, self.catalog = repository, catalog

    def catalog_options(self, kb_id):
        try:
            return {'items': self.catalog.list_datasets(kb_id), 'next_cursor': None}
        except (ValueError, OSError, KeyError):
            raise APIError(503, 'evaluation_catalog_invalid', '服务端评测目录缺失或冻结校验失败，请维护者核对配置。') from None

    def register_set(self, user, data):
        row = next((r for r in self.catalog_options(data['kb_id'])['items']
                    if r['id'] == data['eval_set_id'] and r['version'] == data['version']), None)
        if row is None:
            raise APIError(404, 'not_found', '题集版本不存在或不在授权范围。')
        return self.repo.register_set(user, row)

    def list_sets(self, user, kb_id):
        return self.repo.list_sets(user, kb_id)

    def list_experiments(self, user, kb_id):
        return self.repo.list_experiments(user, kb_id)

    def create_experiment(self, user, data):
        data = dict(data)
        if data.get('regression_source') is None:
            data.pop('regression_source', None)
        if data.get('regression_calibration_id') is None:
            data.pop('regression_calibration_id', None)
        descriptor = self.repo.get_set(user, data['kb_id'], data['eval_set_id'], data['eval_set_version'])
        try:
            resolved = self.catalog.resolve(data['eval_set_id'], data['eval_set_version'],
                data['config_id'], data['config_version'], kb_id=data['kb_id'])
        except (ValueError, OSError, KeyError):
            raise APIError(409, 'evaluation_frozen_identity_invalid', '登记配置与冻结题集不匹配，请核对版本。') from None
        if any(descriptor[k] != resolved[k] for k in ('dataset_sha256', 'manifest_sha256')):
            raise APIError(409, 'evaluation_frozen_identity_invalid', '题集登记后发生变化，请登记新版本。')
        if data.get('regression_source'):
            from .feedback_regression import RegressionService
            ledger = RegressionService(self.repo,self.catalog)
            ledger.validate(user,data['regression_source'],resolved)
            ledger.validate_calibration(user,resolved,data.get('baseline_experiment_id'),data.get('regression_calibration_id'))
        elif data.get('regression_calibration_id'):
            raise APIError(409,'regression_source_required','回归预校准须与反馈来源一同绑定。')
        baseline = self.repo.get_experiment(user, data['baseline_experiment_id']) if data.get('baseline_experiment_id') else None
        return self.repo.create(user, data, descriptor=descriptor, resolved=resolved, baseline=baseline)

    def get_experiment(self, user, eid):
        return public_experiment(self.repo.get_experiment(user, eid))

    def results_page(self, user, eid, **kwargs):
        row = self.repo.get_experiment(user, eid)
        page = self.repo.results_page(eid, attempt=row.get('result_attempt'), **kwargs)
        baseline_id = row.get('baseline_experiment_id')
        if baseline_id:
            baseline = self.repo.get_experiment(user, baseline_id)
            for item in page['items']:
                old = self.repo.results.find_one({'experiment_id': baseline_id,
                    'attempt': baseline.get('result_attempt'), 'question_id': item['question_id']})
                old_result = (old or {}).get('result', {})
                item['baseline'] = {'status': old.get('status') if old else None,
                    'answer': old_result.get('answer'), 'citations': old_result.get('citations'),
                    'metrics': old.get('metrics') if old else None}
                item['difference'] = {'answer_changed': item['result'].get('answer') != old_result.get('answer') if old else None,
                    'status_changed': item['status'] != old['status'] if old else None}
        return page

    def cancel(self, user, eid, version):
        return self.repo.cancel(user, eid, version)

    def retry(self, user, eid, version):
        return self.repo.retry(user, eid, version)
