"""资料发布前核对反馈审核、受影响题及发布回归的有序证明。"""
from app.knowledge.repository import ConflictError, fingerprint


def check_feedback_gate(repo, revision):
    binding = revision['feedback_gate']
    row = repo.db.support_feedback.find_one({'feedback_id': binding['feedback_id'], 'kb_id': repo.kb_id})
    if (not row or row.get('state') != 'confirmed' or
            row.get('draft', {}).get('target_revision_id') != revision['revision_id']):
        raise ConflictError('反馈修订绑定未完成，不能发布')
    proofs = row.get('draft', {}).get('quality_proofs', {})
    affected, full = proofs.get('affected'), proofs.get('full')
    if not affected or not full:
        raise ConflictError('反馈修订须先通过受影响题、再通过完整发布回归')
    expected = fingerprint(revision['validation'])
    if any(p.get('validation_sha256') != expected for p in (affected, full)):
        raise ConflictError('反馈回归不属于当前验证内容')
    if affected['completed_at'] >= full['created_at']:
        raise ConflictError('发布回归必须在受影响题通过后创建')
    if not set(binding['affected_question_ids']) <= set(affected['question_ids']):
        raise ConflictError('受影响题未全部验证')
    # 证明记录由认证服务从持久实验和人工质量门槛生成，不能接受客户端分数。
    from app.identity.models import Principal
    from .repository import EvaluationRepository
    from .reviews import ReviewService
    reviews = ReviewService(EvaluationRepository(repo.db))
    for proof in (affected, full):
        owner = repo.db.users.find_one({'user_id': proof['reviewer_id'], 'enabled': True,
                                      'role': {'$in': ['maintainer', 'admin']}, 'kb_ids': repo.kb_id})
        if owner is None:
            raise ConflictError('反馈质量审核权限已失效')
        user = Principal(**{key: owner[key] for key in Principal.model_fields})
        gate = reviews.gate(user, proof['experiment_id'], proof['calibration_id'], human_only=True)
        experiment = reviews.repo.get_experiment(user, proof['experiment_id'])
        if gate['status'] != 'passed' or experiment.get('result_attempt') != proof['result_attempt']:
            raise ConflictError('反馈回归结果或审核已改变，不能发布')
