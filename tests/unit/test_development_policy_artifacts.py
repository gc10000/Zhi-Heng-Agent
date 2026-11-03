"""批准政策按原字节冻结，Windows新检出也必须可验证。"""
import hashlib
from pathlib import Path
import subprocess

import pytest

from app.api.errors import APIError
from app.evaluation import development_policy as policy


ROOT = Path(__file__).resolve().parents[2]


def git(directory, *args):
    return subprocess.run(
        ['git', *args], cwd=directory, check=True, capture_output=True,
    ).stdout


def approved_bytes(relative):
    return git(ROOT, 'show', 'HEAD:' + relative)


def test_checked_out_policy_keeps_approved_identity():
    payload = policy.policy_payload()
    assert payload['documents'] == policy.APPROVED_DOCUMENTS
    assert payload['policy_id'] == 'assistant-development-v1'


def test_windows_fresh_checkout_preserves_approved_bytes(tmp_path, monkeypatch):
    source = tmp_path / 'source'
    source.mkdir()
    git(source, 'init', '--quiet')
    (source / '.gitattributes').write_bytes((ROOT / '.gitattributes').read_bytes())
    for relative in policy.APPROVED_DOCUMENTS:
        path = source / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(approved_bytes(relative))
    git(source, '-c', 'core.autocrlf=false', 'add', '--', '.gitattributes', 'docs')
    checkout = tmp_path / 'windows-checkout'
    git(source, '-c', 'core.autocrlf=true', 'checkout-index',
        '--prefix=' + checkout.as_posix() + '/', '-a')
    for relative, expected in policy.APPROVED_DOCUMENTS.items():
        assert hashlib.sha256((checkout / relative).read_bytes()).hexdigest() == expected
    monkeypatch.setattr(policy, 'ROOT', checkout)
    assert policy.policy_payload()['documents'] == policy.APPROVED_DOCUMENTS


@pytest.mark.parametrize('relative', list(policy.APPROVED_DOCUMENTS))
def test_changed_policy_content_still_rejected(tmp_path, monkeypatch, relative):
    for path in policy.APPROVED_DOCUMENTS:
        target = tmp_path / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(approved_bytes(path))
    target = tmp_path / relative
    target.write_bytes(target.read_bytes() + '\n实际内容改变'.encode('utf8'))
    monkeypatch.setattr(policy, 'ROOT', tmp_path)
    with pytest.raises(APIError) as error:
        policy.policy_payload()
    assert error.value.status == 409
    assert error.value.code == 'development_policy_invalid'
