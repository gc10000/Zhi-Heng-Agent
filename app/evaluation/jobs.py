"""Mongo持久派发及模型宿主执行；队列消息只携带实验ID。"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import threading
from uuid import UUID

from app.api.errors import APIError


def dispatch(repo, send, *, limit=50):
    now = datetime.now(timezone.utc)
    query = {'$or': [{'state': 'pending', '$or': [{'dispatch_pending': True}, {'next_dispatch_at': {'$lte': now}}]},
                    {'state': {'$in': ['running', 'cancel_requested']}, 'lease_until': {'$lte': now}}]}
    count = 0
    for row in repo.experiments.find(query).limit(limit):
        send(row['experiment_id'])
        repo.experiments.update_one({'experiment_id': row['experiment_id'], 'version': row['version']},
                                    {'$set': {'dispatch_pending': False, 'next_dispatch_at': now+timedelta(seconds=60)}})
        count += 1
    return count


def execute_job(repo, catalog, output_root, experiment_id, *, executor_factory=None, authorize_owner=None):
    """成功题以不可变尝试日志恢复，结果按attempt发布，迟到worker不可覆盖。"""
    UUID(experiment_id)
    row = repo.claim(experiment_id)
    if row is None:
        return
    attempt, token = row['attempt'], row['worker_token']
    stopped, lost = threading.Event(), threading.Event()
    def heartbeat():
        while not stopped.wait(10):
            try:
                if not repo.boundary(experiment_id, attempt, token):
                    lost.set()
                    return
            except Exception:
                lost.set()
                return
    thread = threading.Thread(target=heartbeat, daemon=True)
    thread.start()
    try:
        if authorize_owner:
            authorize_owner(row)
        resolved = catalog.resolve(row['eval_set_id'], row['eval_set_version'], row['config_id'],
                                   row['config_version'], kb_id=row['kb_id'])
        if any(row[key] != resolved[key] for key in ('dataset_sha256', 'manifest_sha256', 'config_sha256')):
            raise ValueError('冻结身份发生变化，拒绝执行')
        if row.get('quality_policy')!=resolved['config'].get('quality_policy'):
            raise ValueError('任务与冻结配置政策不一致')
        if row.get('quality_policy'):
            from .development_policy import DevelopmentPolicy
            from types import SimpleNamespace
            DevelopmentPolicy(repo).validate_candidate(SimpleNamespace(user_id=row['owner_id'],kb_ids=(row['kb_id'],)),row,resolved)
            resolved['config']=dict(resolved['config'],quality_execution_key=row['quality_execution_key'])
        if row.get('regression_source'):
            from .feedback_regression import RegressionService
            from types import SimpleNamespace
            RegressionService(repo,catalog).validate(SimpleNamespace(user_id=row['owner_id'],kb_ids=(row['kb_id'],)),
                row['regression_source'],resolved)
            RegressionService(repo,catalog).validate_calibration(SimpleNamespace(user_id=row['owner_id'],kb_ids=(row['kb_id'],)),
                resolved,row.get('baseline_experiment_id'),row.get('regression_calibration_id'))
            # 登记配置文件hash保持原身份；运行配置另含来源及执行身份，参与日志和检查点hash。
            resolved['config'] = dict(resolved['config'],regression_source=row['regression_source'],
                                      regression_execution_key=row['regression_execution_key'])
        from .runner import run_experiment
        from .validate_dataset import validate_dataset
        from .query_adapter import RealQueryExecutor
        factory = executor_factory or RealQueryExecutor
        output = Path(output_root).resolve() / experiment_id
        with factory(resolved['config']) as executor:
            if executor_factory is None and resolved['config'].get('metric_schema_version') == 1:
                # 控制账本与config.target.database可分离；连接能力仅在进程内传递。
                executor.control_db = repo.db
                executor.execution = {k: row[k] for k in ('experiment_id', 'attempt', 'worker_token', 'config_sha256')}
                if row.get('continuation'):
                    executor.continuation = dict(experiment_id=experiment_id, source=row['continuation'])
                elif attempt > 1:
                    executor.retry_key = ':'.join((row['client_request_id'], experiment_id, str(attempt)))
            def execute(question):
                if authorize_owner:
                    authorize_owner(row)
                if row.get('quality_policy'):
                    DevelopmentPolicy(repo).validate_candidate(SimpleNamespace(user_id=row['owner_id'],kb_ids=(row['kb_id'],)),row,resolved)
                if row.get('regression_source'):
                    RegressionService(repo,catalog).validate(SimpleNamespace(user_id=row['owner_id'],kb_ids=(row['kb_id'],)),
                        row['regression_source'],resolved)
                return executor(question)
            report = run_experiment(resolved['dataset_path'], resolved['manifest_path'],
                resolved['config'], output, execute,
                should_cancel=lambda: lost.is_set() or repo.cancel_requested(experiment_id, attempt, token),
                verify_checkpoint=executor.verify_completed_checkpoint if row.get('regression_source') or row.get('quality_policy') or
                    resolved['config'].get('parameters',{}).get('retrieval_combination',{}).get('enabled') else None)
        questions = [q for q in validate_dataset(resolved['dataset_path'], manifest=resolved['manifest_path'])
                     if q['split'] == 'dev']
        results = [json.loads(line) for line in (output/'results.jsonl').read_text(encoding='utf-8').splitlines()]
        if report['status'] == 'incomplete':
            failed = [r for r in results if r['status'] == 'failed']
            report['retryable'] = bool(failed) and all(r.get('error', {}).get('retryable') is True for r in failed)
        repo.complete(experiment_id, attempt, token, report=report, questions=questions, results=results)
    except Exception as exc:
        from app.infrastructure.providers.policy import classify
        code, retryable = classify(exc)
        if code == 'provider_unknown_error':
            code, retryable = 'evaluation_execution_failed', False
        repo.fail(experiment_id, attempt, token, error_code=code, retryable=retryable)
        logging.getLogger(__name__).error('评测执行失败，异常类型：%s', type(exc).__name__)
    finally:
        stopped.set()
        thread.join(timeout=2)


@contextmanager
def configured_repository():
    from app.settings import Settings
    from pymongo import MongoClient
    from .repository import EvaluationRepository
    settings = Settings.load()
    with MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000, tz_aware=True) as client:
        yield EvaluationRepository(client[settings.database])


def run_local_job(experiment_id):
    """仅模型宿主调用：沿用Windows已安装模型环境，不给Linux安装CUDA。"""
    from .catalog import EvaluationCatalog
    root, directory = os.getenv('M6_EVALUATION_WORK_DIR'), os.getenv('M6_EVALUATION_CATALOG')
    if not root or not directory:
        raise APIError(503, 'evaluation_unconfigured', '请配置M6_EVALUATION_WORK_DIR与M6_EVALUATION_CATALOG。')
    with configured_repository() as repo:
        def authorize(row):
            user = repo.db.users.find_one({'user_id': row['owner_id'], 'enabled': True,
                'role': {'$in': ['maintainer', 'admin']}, 'kb_ids': row['kb_id']})
            if user is None:
                raise APIError(403, 'authorization_revoked', '评测维护权限已撤回。')
        execute_job(repo, EvaluationCatalog(directory), root, experiment_id, authorize_owner=authorize)


def run_job(experiment_id):
    """Linux专用队列将实验ID交给固定受控宿主；不接受路径、prompt或目标配置。"""
    import requests
    UUID(experiment_id)
    base, token = os.getenv('MODEL_HOST_URL'), os.getenv('MODEL_HOST_TOKEN')
    if not base or not token:
        raise ValueError('请配置MODEL_HOST_URL与MODEL_HOST_TOKEN用于独立评测队列。')
    with requests.Session() as http:
        http.trust_env = False
        try:
            response = http.post(base.rstrip('/')+'/evaluation-jobs/'+experiment_id,
                                 headers={'X-Model-Token': token}, timeout=(10, 3600))
        except requests.RequestException as exc:
            raise RuntimeError('评测宿主连接失败，异常类型：'+type(exc).__name__) from None
        if not response.ok:
            raise RuntimeError('评测宿主拒绝请求，状态码：'+str(response.status_code))


def dispatch_configured():
    from app.infrastructure.queue.celery_app import celery_app
    with configured_repository() as repo:
        return dispatch(repo, lambda eid: celery_app.send_task('evaluation.execute', args=[eid],
            queue=os.getenv('M6_QUEUE_NAME', 'knowledge-evaluation')))
