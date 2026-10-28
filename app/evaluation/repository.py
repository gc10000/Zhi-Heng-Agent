"""评测目录与任务的私有Mongo账本；网页只能读取白名单快照。"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from pymongo import ReturnDocument
from pymongo.errors import DuplicateKeyError

from app.api.errors import APIError
from app.knowledge.repository import fingerprint


ACTIVE = {'pending', 'running', 'cancel_requested'}


def corpus_binding(resolved):
    """只保存受控配置授予的候选身份，客户端不得提交发布证明。"""
    config = resolved.get('config') or {}
    candidates = config.get('corpus', {}).get('candidate_revisions', [])
    if not candidates:
        return None
    return dict(database=config['target']['database'],
        is_full_dev=not config.get('question_ids'),
        candidate_revisions=[dict(document_id=r['document_id'], revision_id=r['revision_id'],
            validation_sha256=fingerprint(r['validation'])) for r in candidates])


def public_set(row):
    return {key: deepcopy(row[key]) for key in (
        'eval_set_id', 'version', 'kb_id', 'dataset_sha256', 'manifest_sha256',
        'question_count', 'dev_count', 'review_eligible_count', 'configs', 'created_at') if key in row}


def public_experiment(row):
    return {key: deepcopy(row[key]) for key in (
        'experiment_id', 'client_request_id', 'kb_id', 'eval_set_id', 'eval_set_version',
        'dataset_sha256', 'config_id', 'config_version', 'config_sha256', 'baseline_experiment_id',
        'state', 'attempt', 'version', 'retryable', 'error', 'summary', 'comparison',
        'selected_questions', 'completed', 'failed', 'created_at', 'updated_at', 'continuation') if key in row}


class EvaluationRepository:
    def __init__(self, db):
        self.db = db
        self.sets, self.experiments = db.evaluation_sets, db.evaluation_experiments
        self.results, self.slots = db.evaluation_results, db.evaluation_slots
        self.sets.create_index([('owner_id', 1), ('kb_id', 1), ('eval_set_id', 1), ('version', 1)], unique=True)
        self.experiments.create_index('experiment_id', unique=True)
        self.experiments.create_index([('owner_id', 1), ('kb_id', 1), ('client_request_id', 1)], unique=True)
        self.experiments.create_index([('state', 1), ('dispatch_pending', 1)])
        self.results.create_index([('experiment_id', 1), ('attempt', 1), ('question_id', 1)], unique=True)

    @staticmethod
    def _scope(user, kb_id):
        return {'owner_id': user.user_id, 'kb_id': kb_id}

    def register_set(self, user, descriptor):
        key = self._scope(user, descriptor['kb_id']) | {
            'eval_set_id': descriptor['id'], 'version': descriptor['version']}
        saved = self.sets.find_one(key)
        identity = {name: descriptor[name] for name in (
            'dataset_sha256', 'manifest_sha256', 'question_count', 'dev_count',
            'review_eligible_count', 'configs')}
        if saved is not None:
            if any(saved.get(name) != value for name, value in identity.items()):
                raise APIError(409, 'eval_set_version_conflict', '相同题集版本已绑定其他冻结内容。')
            return public_set(saved)
        row = key | identity | {'created_at': datetime.now(timezone.utc).isoformat()}
        try:
            self.sets.insert_one(row)
        except DuplicateKeyError:
            return self.register_set(user, descriptor)
        return public_set(row)

    def list_sets(self, user, kb_id):
        rows = self.sets.find(self._scope(user, kb_id)).sort([('eval_set_id', 1), ('version', -1)])
        return {'items': [public_set(row) for row in rows], 'next_cursor': None}

    def get_set(self, user, kb_id, eval_set_id, version):
        row = self.sets.find_one(self._scope(user, kb_id) | {'eval_set_id': eval_set_id, 'version': version})
        if row is None:
            raise APIError(404, 'not_found', '评测题集不存在或不在授权范围。')
        return row

    def _reserve(self, owner_id, experiment_id):
        try:
            self.slots.update_one({'_id': owner_id}, {'$setOnInsert': {'active_experiment_id': None}}, upsert=True)
        except DuplicateKeyError:
            pass
        now = datetime.now(timezone.utc)
        # 排队没有执行期限：不能因排队久就给同一所有者第二份预算。
        # 终态后清理窗口中断时，只回收经账本确认已终结的自身占用。
        slot = self.slots.find_one({'_id': owner_id})
        prior = slot.get('active_experiment_id')
        if prior:
            previous = self.experiments.find_one({'experiment_id': prior})
            deadline = slot.get('reservation_until')
            if deadline is not None and deadline.tzinfo is None:
                deadline = deadline.replace(tzinfo=timezone.utc)
            if ((previous and previous['state'] not in ACTIVE) or
                    (previous is None and deadline is not None and deadline <= now)):
                self.release_slot(owner_id, prior)
        result = self.slots.update_one({'_id': owner_id, 'active_experiment_id': None},
            {'$set': {'active_experiment_id': experiment_id, 'reservation_until': now+timedelta(seconds=60)}})
        if not result.matched_count:
            raise APIError(409, 'evaluation_queue_full', '当前用户已有评测占用独立队列预算。')

    def release_slot(self, owner_id, experiment_id):
        self.slots.update_one({'_id': owner_id, 'active_experiment_id': experiment_id},
                              {'$set': {'active_experiment_id': None}, '$unset': {'lease_until': ''}})

    def create(self, user, data, *, descriptor, resolved, baseline=None):
        # 新可选字段省略/显式null等价，兼容旧创建请求的幂等身份。
        if data.get('continuation') is None:
            data = {k: v for k, v in data.items() if k != 'continuation'}
        key = self._scope(user, data['kb_id']) | {'client_request_id': data['client_request_id']}
        identity = fingerprint({k: data[k] for k in data})
        prior = self.experiments.find_one(key)
        if prior:
            if prior['request_sha256'] != identity:
                raise APIError(409, 'idempotency_conflict', '相同请求标识已绑定其他实验参数。')
            return public_experiment(prior)
        continuation = None
        if data.get('continuation'):
            source = data['continuation']
            parent = self.get_experiment(user, source['source_experiment_id'])
            if (parent['state'] not in {'failed', 'cancelled', 'incomplete'} or
                    parent['attempt'] != source['source_attempt'] or
                    parent['version'] != source['source_version'] or
                    parent['kb_id'] != data['kb_id'] or
                    any(parent.get(k) != descriptor[k] for k in ('dataset_sha256', 'manifest_sha256')) or
                    parent['config_sha256'] != resolved['config_sha256'] or
                    not isinstance(source.get('reason'), str) or not source['reason'].strip()):
                raise APIError(409, 'continuation_source_invalid', '后续实验须绑定终态源任务的当前代际和相同冻结题集、配置。')
            continuation = deepcopy(source) | dict(source_state=parent['state'],
                source_retryable=parent['retryable'], source_error=deepcopy(parent.get('error')),
                source_config_sha256=parent['config_sha256'], source_request_sha256=parent['request_sha256'])
        experiment_id = str(uuid4())
        if baseline is not None and (baseline.get('eval_set_id') != data['eval_set_id'] or
                                     baseline.get('eval_set_version') != data['eval_set_version'] or
                                     baseline.get('kb_id') != data['kb_id'] or
                                     baseline.get('dataset_sha256') != descriptor['dataset_sha256'] or
                                     baseline.get('state') != 'completed'):
            raise APIError(409, 'baseline_incompatible', '基线必须是同题集版本的已完成实验。')
        self._reserve(user.user_id, experiment_id)
        now = datetime.now(timezone.utc).isoformat()
        row = self._scope(user, data['kb_id']) | {
            'experiment_id': experiment_id, 'client_request_id': data['client_request_id'],
            'request_sha256': identity, 'eval_set_id': data['eval_set_id'],
            'eval_set_version': data['eval_set_version'], 'dataset_sha256': descriptor['dataset_sha256'],
            'manifest_sha256': descriptor['manifest_sha256'], 'config_id': data['config_id'],
            'config_version': data['config_version'], 'config_sha256': resolved['config_sha256'],
            'baseline_experiment_id': data.get('baseline_experiment_id'),
            'continuation': continuation,
            'corpus_binding': corpus_binding(resolved),
            'selected_questions': resolved['selected_questions'], 'eligible_questions': resolved['eligible_questions'],
            'state': 'pending', 'attempt': 0, 'version': 0, 'retryable': False, 'dispatch_pending': True,
            'output_key': experiment_id, 'created_at': now, 'updated_at': now,
        }
        try:
            self.experiments.insert_one(row)
        except DuplicateKeyError:
            self.release_slot(user.user_id, experiment_id)
            return self.create(user, data, descriptor=descriptor, resolved=resolved, baseline=baseline)
        if not self.slots.find_one({'_id': user.user_id, 'active_experiment_id': experiment_id}):
            self.experiments.update_one({'experiment_id': experiment_id, 'state': 'pending'},
                {'$set': {'state': 'failed', 'retryable': False, 'dispatch_pending': False,
                          'error': {'code': 'evaluation_reservation_lost'}}})
            return public_experiment(self.experiments.find_one({'experiment_id': experiment_id}))
        return public_experiment(row)

    def list_experiments(self, user, kb_id):
        query = self._scope(user, kb_id)
        rows = self.experiments.find(query).sort('created_at', -1).limit(100)
        return {'items': [public_experiment(row) for row in rows], 'next_cursor': None}

    def get_experiment(self, user, experiment_id):
        row = self.experiments.find_one({'experiment_id': experiment_id, 'owner_id': user.user_id,
                                         'kb_id': {'$in': list(user.kb_ids)}})
        if row is None:
            raise APIError(404, 'not_found', '评测任务不存在或不在授权范围。')
        return row

    def cancel(self, user, experiment_id, expected_version):
        row = self.get_experiment(user, experiment_id)
        if row['state'] in {'cancelled', 'completed', 'failed', 'incomplete'}:
            return public_experiment(row)
        target = 'cancelled' if row['state'] == 'pending' else 'cancel_requested'
        result = self.experiments.update_one({'experiment_id': experiment_id, 'owner_id': user.user_id,
            'version': expected_version, 'state': row['state']},
            {'$set': {'state': target, 'updated_at': datetime.now(timezone.utc).isoformat(),
                      'dispatch_pending': False, 'cancel_intent': True}, '$inc': {'version': 1}})
        if not result.matched_count:
            raise APIError(409, 'version_conflict', '评测状态已改变，请刷新。')
        latest = self.get_experiment(user, experiment_id)
        if target == 'cancelled':
            self.release_slot(user.user_id, experiment_id)
        return public_experiment(latest)

    def retry(self, user, experiment_id, expected_version):
        row = self.get_experiment(user, experiment_id)
        if row['state'] != 'failed' or not row['retryable']:
            raise APIError(409, 'experiment_not_retryable', '此实验失败不可自动重试。')
        self._reserve(user.user_id, experiment_id)
        result = self.experiments.update_one({'experiment_id': experiment_id, 'owner_id': user.user_id,
            'version': expected_version, 'state': 'failed', 'retryable': True},
            {'$set': {'state': 'pending', 'dispatch_pending': True, 'retryable': False,
                      'updated_at': datetime.now(timezone.utc).isoformat()}, '$inc': {'version': 1}})
        if not result.matched_count:
            self.release_slot(user.user_id, experiment_id)
            raise APIError(409, 'version_conflict', '评测状态已改变，请刷新。')
        return public_experiment(self.get_experiment(user, experiment_id))

    def claim(self, experiment_id, *, lease_seconds=120):
        now = datetime.now(timezone.utc)
        if not self.slots.find_one({'active_experiment_id': experiment_id}):
            return None
        return self.experiments.find_one_and_update({'experiment_id': experiment_id, '$or': [
            {'state': 'pending'}, {'state': {'$in': ['running', 'cancel_requested']}, 'lease_until': {'$lte': now}}]},
            {'$set': {'state': 'running', 'worker_token': uuid4().hex,
                      'lease_until': now + timedelta(seconds=lease_seconds), 'updated_at': now.isoformat(),
                      'dispatch_pending': False}, '$inc': {'attempt': 1, 'version': 1}},
            return_document=ReturnDocument.AFTER)

    def boundary(self, experiment_id, attempt, worker_token, *, lease_seconds=120):
        row = self.experiments.find_one({'experiment_id': experiment_id, 'attempt': attempt,
                                         'worker_token': worker_token})
        if row is None or row['state'] not in {'running', 'cancel_requested'}:
            return False
        now = datetime.now(timezone.utc)
        result = self.experiments.update_one({'experiment_id': experiment_id, 'attempt': attempt,
            'worker_token': worker_token, 'state': {'$in': ['running', 'cancel_requested']}, 'lease_until': {'$gt': now}},
            {'$set': {'lease_until': now + timedelta(seconds=lease_seconds)}})
        return bool(result.matched_count)

    def cancel_requested(self, experiment_id, attempt, worker_token):
        row = self.experiments.find_one({'experiment_id': experiment_id, 'attempt': attempt,
                                         'worker_token': worker_token})
        return row is None or row.get('cancel_intent') or row['state'] in {'cancel_requested', 'cancelled'}

    def save_results(self, experiment_id, attempt, questions, results):
        by_id = {row['id']: row for row in results}
        public_keys = {'answer', 'citations', 'behavior', 'route', 'retrieval_candidates',
                       'stage_metrics', 'stage_timings', 'logical_provider_calls', 'token_usage', 'image_selection_version',
                       'logical_provider_calls_scope', 'execution_logical_provider_calls'}
        for question in questions:
            record = by_id.get(question['id'])
            if record is None:
                continue
            result = record.get('result') or {}
            clean = {key: deepcopy(value) for key, value in result.items() if key in public_keys}
            row = {'experiment_id': experiment_id, 'attempt': attempt, 'question_id': question['id'],
                   'category': question['category'], 'question': question['question'],
                   'status': record['status'], 'metrics': deepcopy(record.get('metrics', {})),
                   'failure_stage': record.get('failure_stage'), 'error': deepcopy(record.get('error')),
                   'result': clean}
            self.results.replace_one({'experiment_id': experiment_id, 'attempt': attempt,
                                      'question_id': question['id']}, row, upsert=True)

    def results_page(self, experiment_id, *, attempt=None, cursor=None, limit=50):
        if attempt is None:
            experiment = self.experiments.find_one({'experiment_id': experiment_id}) or {}
            attempt = experiment.get('result_attempt')
        if attempt is None:
            return {'items': [], 'next_cursor': None}
        query = {'experiment_id': experiment_id, 'attempt': attempt}
        if cursor:
            query['question_id'] = {'$gt': cursor}
        rows = list(self.results.find(query).sort('question_id', 1).limit(limit + 1))
        items = [{k: deepcopy(v) for k, v in row.items() if k not in {'_id', 'experiment_id', 'attempt'}}
                 for row in rows[:limit]]
        return {'items': items, 'next_cursor': rows[limit - 1]['question_id'] if len(rows) > limit else None}

    def complete(self, experiment_id, attempt, worker_token, *, report, questions, results):
        row = self.experiments.find_one({'experiment_id': experiment_id, 'attempt': attempt,
            'worker_token': worker_token, 'lease_until': {'$gt': datetime.now(timezone.utc)},
            'state': {'$in': ['running', 'cancel_requested']}})
        if row is None:
            return None
        # 每次attempt独立结果，发布指针CAS通过前对API不可见。
        self.save_results(experiment_id, attempt, questions, results)
        state = 'cancelled' if report['status'] == 'cancelled' or row.get('cancel_intent') or row['state'] == 'cancel_requested' else report['status']
        if state not in {'completed', 'incomplete', 'cancelled'}:
            state = 'incomplete'
        if state == 'incomplete':
            state = 'failed'
        retryable = state == 'failed' and report.get('retryable') is True
        result = self.experiments.update_one({'experiment_id': experiment_id, 'attempt': attempt,
            'worker_token': worker_token, 'state': {'$in': ['running', 'cancel_requested']},
            'lease_until': {'$gt': datetime.now(timezone.utc)}},
            {'$set': {'state': state, 'summary': deepcopy(report.get('summary')),
                      'completed': report.get('completed', 0), 'failed': report.get('failed', 0),
                      'result_attempt': attempt,
                      'retryable': retryable,
                      'error': {'code': 'evaluation_questions_failed'} if state == 'failed' else None,
                      'updated_at': datetime.now(timezone.utc).isoformat()},
             '$unset': {'worker_token': '', 'lease_until': ''}, '$inc': {'version': 1}})
        if result.matched_count:
            self.release_slot(row['owner_id'], experiment_id)
            return self.experiments.find_one({'experiment_id': experiment_id})
        return None

    def fail(self, experiment_id, attempt, worker_token, *, error_code, retryable):
        row = self.experiments.find_one({'experiment_id': experiment_id, 'attempt': attempt,
                                         'worker_token': worker_token})
        if row is None:
            return None
        result = self.experiments.update_one({'experiment_id': experiment_id, 'attempt': attempt,
            'worker_token': worker_token, 'state': {'$in': ['running', 'cancel_requested']},
            'lease_until': {'$gt': datetime.now(timezone.utc)}},
            {'$set': {'state': 'failed', 'error': {'code': error_code}, 'retryable': retryable,
                      'updated_at': datetime.now(timezone.utc).isoformat()},
             '$unset': {'worker_token': '', 'lease_until': ''}, '$inc': {'version': 1}})
        if result.matched_count:
            self.release_slot(row['owner_id'], experiment_id)
            return self.experiments.find_one({'experiment_id': experiment_id})
        return None
