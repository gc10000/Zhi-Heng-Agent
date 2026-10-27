"""仅按当前评测结果中精确登记的来源读取图片，不暴露存储对象路径。"""
import re

from app.api.errors import APIError
from app.knowledge.asset_api import asset_record, read_asset
from app.knowledge.repository import ScopeError


_SHA256 = re.compile(r'^[0-9a-f]{64}$')


def load_review_image(repo, user, knowledge_factory, eid, question_id, document_sha256, page, asset_sha256):
    """验证实验/题目/文档/页/图像五元绑定后，通过原授权资源API读取图像。"""
    if not _SHA256.fullmatch(document_sha256) or not _SHA256.fullmatch(asset_sha256) or page < 1:
        raise APIError(404, 'not_found', '审阅图片不存在或不在授权范围。')

    experiment = repo.get_experiment(user, eid)
    if experiment.get('state') != 'completed' or experiment.get('result_attempt') is None:
        raise APIError(404, 'not_found', '审阅图片不存在或不在授权范围。')
    result = repo.results.find_one({'experiment_id': eid, 'attempt': experiment['result_attempt'],
                                    'question_id': question_id})
    if result is None:
        raise APIError(404, 'not_found', '审阅图片不存在或不在授权范围。')
    if not any(citation.get('document_sha256') == document_sha256 and citation.get('page') == page and
               citation.get('asset_sha256') == asset_sha256
               for citation in (result.get('result') or {}).get('citations', [])):
        raise APIError(404, 'not_found', '审阅图片不存在或不在授权范围。')

    gateway = knowledge_factory()
    revisions = list(gateway.db.knowledge_revisions.find({
        'owner_id': gateway.owner_id,
        'kb_id': experiment['kb_id'],
        'original_sha256': document_sha256,
    }))
    revision_by_identity = {(row['document_id'], row['revision_id']): row for row in revisions}
    if not revision_by_identity:
        raise APIError(404, 'not_found', '审阅图片不存在或不在授权范围。')
    candidates = gateway.db.knowledge_assets.find({
        'sha256': asset_sha256,
        'media_type': {'$regex': '^image/'},
        'source_refs.page': page,
        'document_id': {'$in': [did for did, _ in revision_by_identity]},
        'revision_id': {'$in': [rid for _, rid in revision_by_identity]},
    })
    for candidate in candidates:
        expected_revision = revision_by_identity.get((candidate.get('document_id'), candidate.get('revision_id')))
        if expected_revision is None or expected_revision.get('original_sha256') != document_sha256:
            continue
        if not any(ref.get('page') == page and ref.get('document_id') == candidate.get('document_id') and
                   ref.get('revision_id') == candidate.get('revision_id')
                   for ref in candidate.get('source_refs', [])):
            continue
        try:
            row, revision = asset_record(gateway, user, candidate['asset_id'])
        except APIError as exc:
            if exc.status == 404:
                continue
            raise
        except ScopeError:
            continue
        if (row.get('document_id') != candidate.get('document_id') or
                row.get('revision_id') != candidate.get('revision_id') or
                row.get('sha256') != asset_sha256 or
                not str(row.get('media_type', '')).startswith('image/') or
                revision.get('kb_id') != experiment['kb_id'] or
                revision.get('original_sha256') != document_sha256 or
                not any(ref.get('page') == page and ref.get('document_id') == row.get('document_id') and
                        ref.get('revision_id') == row.get('revision_id')
                        for ref in row.get('source_refs', []))):
            continue
        return read_asset(gateway, row, revision), row['media_type']

    raise APIError(404, 'not_found', '审阅图片不存在或不在授权范围。')
