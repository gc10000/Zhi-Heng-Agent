"""真实入口的隔离门禁不得在客户端构造后才执行。"""
from contextlib import contextmanager
import pytest
from app.evaluation.query_adapter import RealQueryExecutor


def config():
    return {'experiment_id': 'baseline', 'dataset_sha256': 'a'*64,
            'target': {'database': 'm1_test_m4_adapter', 'collection': 'm1_test_m4_adapter_v2',
                       'owner_id': 'm4-test-owner', 'kb_id': 'm4-test-kb',
                       'object_prefix': 'm4-test/adapter/', 'bucket': 'existing'},
            'corpus': {'documents': []}, 'strategy': 'm3-baseline'}


@pytest.mark.parametrize('field,value', [('database', 'course'), ('collection', 'course_v2'),
    ('owner_id', 'organization'), ('kb_id', 'course'), ('object_prefix', 'course/'),
    ('object_prefix', 'm4-test/a/../b/')])
def test_unsafe_target_rejected_before_any_resource_creation(field, value):
    cfg = config(); cfg['target'][field] = value
    def forbidden(*args): pytest.fail('隔离门禁必须先于资源构造')
    with pytest.raises(ValueError):
        with RealQueryExecutor(cfg, resource_factory=forbidden): pass


def test_resource_factory_receives_validated_isolation_target():
    calls = []
    @contextmanager
    def resources(cfg):
        calls.append(cfg['target']['database'])
        raise RuntimeError('仅验证进入真实入口前的门禁')
        yield
    with pytest.raises(RuntimeError):
        with RealQueryExecutor(config(), resource_factory=resources): pass
    assert calls == ['m1_test_m4_adapter']



def test_configured_m4_strategy_is_validated_then_reaches_resource_boundary():
    cfg=config();cfg.update(strategy='m4-configured',parameters=dict(retrieval=dict(fusion='rrf')))
    seen=[]
    @contextmanager
    def resources(actual):
        seen.append(actual)
        raise RuntimeError('validated-resource-boundary')
        yield
    with pytest.raises(RuntimeError,match='validated-resource-boundary'):
        with RealQueryExecutor(cfg,resource_factory=resources):pass
    assert seen[0]['parameters']['retrieval']['fusion']=='rrf'
