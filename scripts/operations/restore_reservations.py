"""同一隔离存储绑定的恢复目标共享预留；无TTL，不释放失败或未知预留。"""
from contextlib import contextmanager
from dataclasses import asdict
import os
import re
from uuid import uuid4

from pymongo.errors import DuplicateKeyError
from app.knowledge.repository import fingerprint


def control_database(source, target):
    name = os.getenv('M7_RESTORE_CONTROL_DATABASE')
    if not name:
        # 兼容既有随机预览配置。控制身份只来自共享项目，绝不能按源或目标派生。
        project = os.getenv('M7_PROJECT_NAME', '')
        if not re.fullmatch(r'zh-m7-[a-f0-9]{6}', project):
            raise ValueError('恢复缺少共享控制库身份')
        name = 'm1_test_m4_rc_' + project.removeprefix('zh-m7-')
    if (not re.fullmatch(r'm1_test_m4_[a-z0-9_]{1,45}', name)
            or name in {source.database, target.database}):
        raise ValueError('恢复共享控制库必须独立于源和目标测试库')
    return name


@contextmanager
def reserve_targets(mongo, source, target, manifest_sha256):
    """固定存储绑定必须共用此库。部分占用保留，冲突方不能写入任一目标。"""
    name = control_database(source, target)
    db = mongo[name]
    attempt = uuid4().hex
    attempts = db.m7_restore_attempts
    attempts.insert_one(dict(_id=attempt, state='reserving', manifest_sha256=manifest_sha256,
                             source=asdict(source), target=asdict(target)))
    try:
        for kind in ('database', 'bucket', 'collection'):
            resource = getattr(target, kind)
            try:
                db.m7_restore_resource_claims.insert_one(dict(
                    _id=fingerprint([kind, resource]), kind=kind, resource=resource, attempt=attempt,
                    manifest_sha256=manifest_sha256))
            except DuplicateKeyError:
                raise ValueError('恢复目标已预留，拒绝覆盖或自动继续') from None
        attempts.update_one({'_id': attempt}, {'$set': {'state': 'started'}})
        yield dict(database=name, attempt=attempt)
    except BaseException:
        attempts.update_one({'_id': attempt}, {'$set': {'state': 'failed'}})
        raise
    else:
        attempts.update_one({'_id': attempt}, {'$set': {'state': 'completed'}})
