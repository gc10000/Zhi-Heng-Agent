"""恢复竞争只操作新建合成目标，失败资源保留，零模型调用。"""
import os
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration


@pytest.mark.parametrize('shared', ['database', 'bucket', 'collection'])
def test_competing_restore_reserves_each_target_before_writing(tmp_path, shared):
    from scripts.operations.connections import environment, connections
    assert os.getenv('M7_TEST_ENV'), '必须显式提供隔离host.env'
    environment(os.environ['M7_TEST_ENV'])
    from scripts.operations.bootstrap_preview import seed
    from scripts.operations.snapshot import Namespace, backup, restore, vector_dump, canonical

    suffix = uuid4().hex[:6]
    def scope(tag):
        name = 'm1_test_m4_rr_' + suffix + '_' + tag
        return Namespace(name, 'zh-restore-rr-' + suffix + '-' + tag, name + '_v2', 'knowledge/')
    source, first, other = scope('src'), scope('first'), scope('other')
    competing = Namespace(**(vars(other) | {shared: getattr(first, shared)}))
    paused, release = Event(), Event()
    with connections() as (mongo, objects, vectors):
        seed(mongo, objects, vectors, source)
        receipt = backup(tmp_path/'snapshot', source, mongo, objects, vectors, source_commit='synthetic-reservation-test')
        class PausedObjects:
            def __getattr__(self, name):
                return getattr(objects, name)
            def make_bucket(self, bucket):
                objects.make_bucket(bucket)
                paused.set()
                if not release.wait(45):
                    raise TimeoutError('合成并发调度超时')

        with ThreadPoolExecutor(max_workers=1) as pool:
            winner = pool.submit(restore, tmp_path/'snapshot', first, mongo, PausedObjects(), vectors,
                                 expected_sha256=receipt['manifest_sha256'])
            assert paused.wait(20)
            try:
                with pytest.raises(ValueError, match='目标已存在|目标已预留'):
                    restore(tmp_path/'snapshot', competing, mongo, objects, vectors,
                            expected_sha256=receipt['manifest_sha256'])
                if shared != 'database':
                    assert not mongo[competing.database].list_collection_names()
                if shared != 'bucket':
                    assert not objects.bucket_exists(competing.bucket)
                if shared != 'collection':
                    assert not vectors.has_collection(competing.collection)
            finally:
                release.set()
            assert winner.result(timeout=45)['state'] == 'completed'
        assert canonical(vector_dump(vectors, first.collection)) == canonical(vector_dump(vectors, source.collection))


def test_restore_keeps_claims_after_write_failure(tmp_path):
    from scripts.operations.connections import environment, connections
    assert os.getenv('M7_TEST_ENV'), '必须显式提供隔离host.env'
    environment(os.environ['M7_TEST_ENV'])
    from scripts.operations.bootstrap_preview import seed
    from scripts.operations.snapshot import Namespace, backup, restore

    suffix = uuid4().hex[:6]
    def scope(tag, collection=None):
        name = 'm1_test_m4_rf_' + suffix + '_' + tag
        return Namespace(name, 'zh-restore-rf-' + suffix + '-' + tag, collection or name + '_v2', 'knowledge/')
    source, failed = scope('src'), scope('failed')
    with connections() as (mongo, objects, vectors):
        seed(mongo, objects, vectors, source)
        receipt = backup(tmp_path/'snapshot', source, mongo, objects, vectors, source_commit='synthetic-failure-test')
        class FailedObjects:
            def __getattr__(self, name):
                return getattr(objects, name)
            def make_bucket(self, bucket):
                raise TimeoutError('合成写入失败，目标资源尚不存在')
        with pytest.raises(TimeoutError):
            restore(tmp_path/'snapshot', failed, mongo, FailedObjects(), vectors,
                    expected_sha256=receipt['manifest_sha256'])
        other = scope('other', failed.collection)
        with pytest.raises(ValueError, match='目标已预留'):
            restore(tmp_path/'snapshot', other, mongo, objects, vectors,
                    expected_sha256=receipt['manifest_sha256'])
        assert not mongo[other.database].list_collection_names()
        assert not objects.bucket_exists(other.bucket)
        assert not vectors.has_collection(other.collection)
