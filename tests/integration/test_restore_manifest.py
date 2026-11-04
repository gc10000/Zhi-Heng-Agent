"""真实隔离Mongo/MinIO/Milvus恢复；向量为合成数据，零模型调用。"""
import os
from uuid import uuid4

import pytest

pytestmark = pytest.mark.integration


def test_restore_roundtrip_read_original_index_registry_permissions_and_switch(tmp_path):
    from dotenv import load_dotenv
    assert os.getenv('M7_TEST_ENV'), '必须显式提供本轮隔离host.env'
    load_dotenv(os.environ['M7_TEST_ENV'], override=True)
    from scripts.operations.connections import connections
    from scripts.operations.bootstrap_preview import seed
    from scripts.operations.snapshot import Namespace, backup, restore, mongo_dump, canonical
    from app.knowledge.index import V2Index
    from app.knowledge.originals import OriginalStore
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.publishing import RevisionPublisher
    from app.identity.service import IdentityService, MongoIdentityStore

    suffix = uuid4().hex[:6]
    source = Namespace('m1_test_m4_bak_' + suffix, 'zh-preview-bak-' + suffix, 'm1_test_m4_bak_' + suffix + '_v2', 'knowledge/')
    target = Namespace('m1_test_m4_res_' + suffix, 'zh-restore-' + suffix, 'm1_test_m4_res_' + suffix + '_v2', 'knowledge/')
    with connections() as (mongo, objects, vectors):
        seeded = seed(mongo, objects, vectors, source)
        from app.conversations.repository import ConversationRepository
        from app.runs.repository import RunRepository
        RunRepository(mongo[source.database], ConversationRepository(mongo[source.database]))
        before = canonical(mongo_dump(mongo[source.database]))
        receipt = backup(tmp_path / 'snapshot', source, mongo, objects, vectors, source_commit='synthetic-delivery-test')
        done = restore(tmp_path / 'snapshot', target, mongo, objects, vectors, expected_sha256=receipt['manifest_sha256'])
        assert done['state'] == 'completed' and done['source_mutated'] is False
        assert canonical(mongo_dump(mongo[source.database])) == before
        # 恢复后必须能构造实际应用仓储；复合索引顺序不能被canonical JSON字典排序改变。
        RunRepository(mongo[target.database], ConversationRepository(mongo[target.database]))
        assert mongo[target.database].login_sessions.count_documents({}) == 0
        store = MongoIdentityStore(mongo[target.database])
        identity = IdentityService(store)
        token, user = identity.login(os.environ['M7_PREVIEW_USERNAME'], os.environ['M7_PREVIEW_PASSWORD'], 'synthetic-restore')
        assert identity.authenticate(token).role == 'admin' and user.kb_ids == ('preview-kb',)
        repo = KnowledgeRepository(mongo[target.database], owner_id=os.environ['M2_KNOWLEDGE_OWNER_ID'], kb_id='preview-kb')
        original = OriginalStore(objects, bucket=target.bucket, prefix=target.prefix)
        revision = repo.get_revision(seeded['revision_id'])
        assert original.read(revision).startswith('# 知衡'.encode())
        index = V2Index(vectors, target.collection)
        published = RevisionPublisher(repo, index, read_original=original.read)
        assert published.inspect(revision) == revision['validation']
        hits = index.search(repo, '自制演练', embedder=lambda _: {'dense': [[1.0] + [0.0] * 1023], 'sparse': [{1: 1.0}]}, limit=2)
        assert hits and all(hit['entity']['revision_id'] == revision['revision_id'] for hit in hits)
        # 两个独立目标均可读；仅切换部署绑定，没有回写或删除源活动指针。
        source_original = OriginalStore(objects, bucket=source.bucket, prefix=source.prefix)
        assert source_original.read(mongo[source.database].knowledge_revisions.find_one({'revision_id': revision['revision_id']})) == original.read(revision)
        with pytest.raises(ValueError, match='目标已存在'):
            restore(tmp_path / 'snapshot', target, mongo, objects, vectors, expected_sha256=receipt['manifest_sha256'])
        assert canonical(mongo_dump(mongo[source.database])) == before
