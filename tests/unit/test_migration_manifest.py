"""迁移计划纯离线：稳定源身份、缺失/碰撞先报告，不按文件名合并。"""
import pytest


def test_dry_run_keeps_same_names_and_flags_missing_and_collision():
    from app.knowledge.migration import plan_migration
    records=[{'source_id':'1','name':'同名','original_key':'a','original_sha256':'a'*64,'chunk_ids':['11']},
             {'source_id':'2','name':'同名','original_key':'b','original_sha256':'b'*64,'chunk_ids':['12']}]
    report=plan_migration(records,owner_id='o',kb_id='k')
    assert report['ready'] and report['writes']==0
    assert report['mapping'][0]['document_id']!=report['mapping'][1]['document_id']
    assert report['same_names']==['同名']
    broken=plan_migration(records+[dict(records[0],original_key='other')],owner_id='o',kb_id='k')
    assert not broken['ready'] and broken['collisions']
    missing=plan_migration([{'source_id':'missing','name':'x'}],owner_id='o',kb_id='k')
    assert not missing['ready'] and missing['missing']


def test_recovery_gate_rejects_missing_or_other_snapshot():
    from app.knowledge.migration import require_recovery
    with pytest.raises(ValueError):require_recovery({'snapshot_sha256':'x'},None)
    with pytest.raises(ValueError):require_recovery({'snapshot_sha256':'x'},{'verified':True,'snapshot_sha256':'different'})


def test_invalid_hash_is_not_ready_for_writes():
    from app.knowledge.migration import plan_migration
    report=plan_migration([{'source_id':'s','name':'x','original_key':'a','original_sha256':'not-sha256','chunk_ids':['1']}],owner_id='o',kb_id='k')
    assert not report['ready'] and report['missing']
