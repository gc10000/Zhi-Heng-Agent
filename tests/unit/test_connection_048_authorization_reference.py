"""授权引用独立于app指纹，仍须来自已提交Git且限定本批文件。"""
import json
from types import SimpleNamespace

import pytest

from app.infrastructure.providers import connection_comparison_048_risk as risk


def test_missing_reference_is_disabled_without_git_io(tmp_path, monkeypatch):
    monkeypatch.setattr('subprocess.run', lambda *a, **kw: pytest.fail('缺引用不能调用Git'))
    assert risk.load_authorization_reference(tmp_path) is None


@pytest.mark.parametrize('case', ['valid', 'uncommitted', 'wrong_path', 'malformed'])
def test_reference_requires_committed_exact_bytes_and_new_authorization_path(tmp_path, monkeypatch, case):
    ref = dict(commit='a'*40, path='docs/development/reviews/M6-connection-comparison-048-authorization-r1.json', sha256='b'*64)
    if case == 'wrong_path': ref['path'] = 'docs/development/reviews/M6-comparison-answer-048-authorization-r8.json'
    pin = tmp_path / 'docs/development/reviews/M6-connection-comparison-048-authorization-reference-r1.json'
    pin.parent.mkdir(parents=True)
    payload = json.dumps(ref).encode() if case != 'malformed' else b'{}'
    pin.write_bytes(payload)
    calls = []
    def run(args, **kwargs):
        calls.append(args)
        return SimpleNamespace(returncode=0, stdout=payload if case != 'uncommitted' else b'other')
    monkeypatch.setattr('subprocess.run', run)
    if case == 'valid':
        assert risk.load_authorization_reference(tmp_path) == ref
        assert calls == [['git', 'show', 'HEAD:docs/development/reviews/M6-connection-comparison-048-authorization-reference-r1.json']]
    else:
        with pytest.raises(ValueError): risk.load_authorization_reference(tmp_path)
