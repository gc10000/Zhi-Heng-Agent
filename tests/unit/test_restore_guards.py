"""恢复在任何写入前验证完整清单、独立目标及输入路径。"""
import json
from pathlib import Path

import pytest


def test_restore_rejects_same_namespace_and_non_test_target():
    from scripts.operations.snapshot import Namespace, validate_target
    source = Namespace('m1_test_m4_src_ab', 'zh-preview-ab', 'm1_test_m4_src_ab_v2', 'knowledge/')
    with pytest.raises(ValueError):
        validate_target(source, source)
    with pytest.raises(ValueError):
        Namespace('production', 'zh-restore-ab', 'm1_test_m4_dst_ab_v2', 'knowledge/')


@pytest.mark.parametrize('file', ['../outside', '/etc/passwd', 'objects/../../outside', 'objects\\x', 'file://outside'])
def test_restore_rejects_manifest_path_escape_before_io(tmp_path, file):
    from scripts.operations.snapshot import validate_files
    with pytest.raises(ValueError):
        validate_files(tmp_path, {'files': {file: '0' * 64}})


def test_restore_detects_tampered_payload(tmp_path):
    from scripts.operations.snapshot import validate_files
    (tmp_path / 'vectors.json').write_text('tampered')
    with pytest.raises(ValueError):
        validate_files(tmp_path, {'files': {'vectors.json': '0' * 64}})


def test_restore_rejects_symlink_escape(tmp_path):
    from scripts.operations.snapshot import validate_files
    outside = tmp_path.parent / 'external'
    outside.write_text('outside')
    link = tmp_path / 'linked'
    try:
        link.symlink_to(outside)
    except OSError:
        pytest.skip('当前Windows账号无创建符号链接权限；Linux镜像另验')
    with pytest.raises(ValueError):
        validate_files(tmp_path, {'files': {'linked': '0' * 64}})


def test_restore_keeps_source_immutable_and_rebinds_index_namespace():
    from scripts.operations.snapshot import Namespace, remap_mongo
    source = Namespace('m1_test_m4_src_ab', 'zh-preview-ab', 'm1_test_m4_src_ab_v2', 'knowledge/')
    target = Namespace('m1_test_m4_dst_ab', 'zh-restore-ab', 'm1_test_m4_dst_ab_v2', 'knowledge/')
    doc = {'revision_id': 'r', 'stages': {'indexed': {'collection': source.collection, 'payload_hashes': {'c': 'h'}}}}
    changed = remap_mongo('knowledge_revisions', doc, source, target)
    assert changed['stages']['indexed']['collection'] == target.collection
    assert doc['stages']['indexed']['collection'] == source.collection
    assert changed['stages']['indexed']['payload_hashes'] == {'c': 'h'}
