"""用真实临时Git证明授权引用可分两次提交，无SHA固定点。"""
import hashlib
import json
import subprocess
import pytest


def git(root, *args):
    return subprocess.run(['git', *args], cwd=root, check=True, capture_output=True).stdout.decode().strip()


def test_reference_loads_only_committed_pin_to_the_separate_authorization(tmp_path):
    from app.infrastructure.providers import m6_feedback_candidate_risk as risk
    git(tmp_path, 'init')
    git(tmp_path, 'config', 'user.email', 'synthetic@example.invalid')
    git(tmp_path, 'config', 'user.name', 'Synthetic reference test')
    git(tmp_path, 'config', 'core.autocrlf', 'false')
    auth = tmp_path / risk.AUTHORIZATION_PATH
    auth.parent.mkdir(parents=True)
    auth.write_text(json.dumps({'production_manifest_sha256': 'a'*64}), encoding='utf-8')
    git(tmp_path, 'add', risk.AUTHORIZATION_PATH)
    git(tmp_path, 'commit', '-m', 'synthetic authorization')
    ref = dict(commit=git(tmp_path, 'rev-parse', 'HEAD'), path=risk.AUTHORIZATION_PATH,
        sha256=hashlib.sha256(auth.read_bytes()).hexdigest())
    pin = tmp_path / risk.AUTHORIZATION_REFERENCE_PATH
    pin.write_text(json.dumps(ref), encoding='utf-8')
    with pytest.raises(ValueError):
        risk.load_authorization_reference(tmp_path)

    git(tmp_path, 'add', risk.AUTHORIZATION_REFERENCE_PATH)
    git(tmp_path, 'commit', '-m', 'synthetic pin')
    assert risk.load_authorization_reference(tmp_path) == ref
    pin.write_text(json.dumps(ref | {'sha256': 'b'*64}), encoding='utf-8')
    with pytest.raises(ValueError):
        risk.load_authorization_reference(tmp_path)


def test_windows_checkout_preserves_exact_new_reference_bytes(tmp_path):
    from pathlib import Path
    from app.infrastructure.providers import m6_feedback_candidate_risk as risk
    root = Path(__file__).resolve().parents[2]
    git(tmp_path, 'init')
    git(tmp_path, 'config', 'user.email', 'synthetic@example.invalid')
    git(tmp_path, 'config', 'user.name', 'Synthetic checkout test')
    git(tmp_path, 'config', 'core.autocrlf', 'true')
    (tmp_path/'.gitattributes').write_bytes((root/'.gitattributes').read_bytes())
    auth = tmp_path/risk.AUTHORIZATION_PATH
    auth.parent.mkdir(parents=True)
    auth.write_bytes(b'{}\n')
    git(tmp_path, 'add', '.gitattributes', risk.AUTHORIZATION_PATH)
    git(tmp_path, 'commit', '-m', 'authorization')
    ref = dict(commit=git(tmp_path,'rev-parse','HEAD'), path=risk.AUTHORIZATION_PATH,
        sha256=hashlib.sha256(auth.read_bytes()).hexdigest())
    pin = tmp_path/risk.AUTHORIZATION_REFERENCE_PATH
    pin.write_bytes((json.dumps(ref,indent=2)+'\n').encode())
    git(tmp_path,'add',risk.AUTHORIZATION_REFERENCE_PATH)
    git(tmp_path,'commit','-m','pin')
    pin.unlink()
    git(tmp_path,'checkout-index','--force',risk.AUTHORIZATION_REFERENCE_PATH)
    assert risk.load_authorization_reference(tmp_path)==ref
