"""真实入口的隔离门禁不得在客户端构造后才执行。"""
from contextlib import contextmanager
import hashlib
import subprocess
import pytest
from app.evaluation.query_adapter import RealQueryExecutor, accepted_dataset_document_matches


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


def test_dataset_acceptance_accepts_git_clean_lf_crlf_checkout(tmp_path, monkeypatch):
    from app.evaluation import query_adapter

    path = tmp_path / 'review.md'
    path.write_bytes(b'accepted\r\nreview\r\n')
    expected = hashlib.sha256(b'accepted\nreview\n').hexdigest()

    def git(args, *, cwd, check, capture_output, timeout):
        if args == ['git', 'diff', '--quiet', 'HEAD', '--', 'review.md']:
            return subprocess.CompletedProcess(args, 0, stdout=b'', stderr=b'')
        if args == ['git', 'show', 'HEAD:review.md']:
            return subprocess.CompletedProcess(args, 0, stdout=b'accepted\nreview\n', stderr=b'')
        pytest.fail(f'unexpected git command: {args}')

    monkeypatch.setattr(query_adapter.subprocess, 'run', git)
    assert accepted_dataset_document_matches(path, expected, root=tmp_path)


def test_dataset_acceptance_rejects_git_dirty_review_even_if_normalized(tmp_path, monkeypatch):
    from app.evaluation import query_adapter

    path = tmp_path / 'review.md'
    path.write_bytes(b'accepted\r\nchanged\r\n')
    expected = hashlib.sha256(b'accepted\nreview\n').hexdigest()

    def git(args, *, cwd, check, capture_output, timeout):
        assert args == ['git', 'diff', '--quiet', 'HEAD', '--', 'review.md']
        return subprocess.CompletedProcess(args, 1, stdout=b'', stderr=b'')

    monkeypatch.setattr(query_adapter.subprocess, 'run', git)
    assert not accepted_dataset_document_matches(path, expected, root=tmp_path)
