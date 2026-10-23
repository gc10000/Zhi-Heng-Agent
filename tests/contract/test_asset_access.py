"""资产入口及旧MinIO工具不能在import期间改策略。"""
import importlib
import sys
import pytest
from tests.contract.test_auth import auth_client


def test_asset_route_requires_login(auth_client):
    client, _, _ = auth_client
    assert client.get('/api/v1/assets/unknown').status_code == 401


def test_old_storage_import_does_not_construct_or_change_policy(monkeypatch):
    import minio
    calls = []
    class Storage:
        def __init__(self, *args, **kwargs):
            calls.append('construct')
        def bucket_exists(self, *args):
            calls.append('bucket_check')
            return True
        def set_bucket_policy(self, *args):
            calls.append('policy')
    monkeypatch.setattr(minio, 'Minio', Storage)
    name = 'app.clients.minio_utils'
    previous = sys.modules.pop(name, None)
    try:
        importlib.import_module(name)
        assert calls == []
    finally:
        sys.modules.pop(name, None)
        if previous is not None:
            sys.modules[name] = previous


@pytest.mark.parametrize('header,expected', [('bytes=0-2', (0, 2)), ('bytes=3-', (3, 9)),
    ('bytes=-3', (7, 9)), ('bytes=8-99', (8, 9)), ('bytes=-99', (0, 9))])
def test_valid_pdf_ranges(header, expected):
    from app.knowledge.asset_api import byte_range
    assert byte_range(header, 10) == expected


@pytest.mark.parametrize('header', ['bytes=10-', 'bytes=4-2', 'bytes=-0', 'bytes=-', 'bytes=0-1,4-5', 'items=0-1', 'bytes=+1-2'])
def test_invalid_pdf_ranges(header):
    from app.knowledge.asset_api import byte_range
    with pytest.raises(ValueError):
        byte_range(header, 10)


def test_only_declared_assets_can_be_rendered_as_images():
    from app.knowledge.citation_api import controlled_markdown
    result = controlled_markdown('![a](asset://allowed) ![b](https://evil.invalid/x) ![c](asset://other)', {'allowed'})
    assert '/api/v1/assets/allowed' in result
    assert 'evil.invalid' not in result and 'asset://other' not in result
