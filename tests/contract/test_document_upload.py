"""上传和目录必须进入统一身份边界。"""
from tests.contract.test_auth import auth_client
import pytest


def test_document_upload_requires_login(auth_client):
    client, _, _ = auth_client
    result = client.post('/api/v1/documents', data={'kb_id': 'kb', 'client_request_id': 'one'},
                         files={'file': ('manual.md', b'# manual', 'text/markdown')})
    assert result.status_code == 401


@pytest.mark.parametrize('name,media,data,status', [
    ('../manual.md', 'text/markdown', b'# ok', 422),
    ('C:\\manual.md', 'text/markdown', b'# ok', 422),
    ('folder/manual.md', 'text/markdown', b'# ok', 422),
    ('manual.exe', 'application/octet-stream', b'x', 415),
    ('manual.pdf', 'text/markdown', b'# text', 415),
    ('manual.pdf', 'application/pdf', b'# text', 422),
    ('manual.md', 'text/markdown', b'\x00x', 422),
    ('manual.md', 'text/markdown', b'', 422),
    ('manual.md', 'text/markdown', b'x' * 11, 413),
])
def test_upload_filename_format_and_size_boundaries(name, media, data, status):
    from app.knowledge.upload import validate_upload
    from app.api.errors import APIError
    with pytest.raises(APIError) as rejected:
        validate_upload(name, media, data, 10)
    assert rejected.value.status == status


def test_missing_knowledge_configuration_does_not_connect_clients():
    from app.knowledge.resources import KnowledgeResources
    from app.settings import Settings
    from app.api.errors import APIError
    with pytest.raises(APIError) as missing:
        KnowledgeResources(None, Settings('unused', 'unused')).get()
    assert missing.value.status == 503 and 'M2_KNOWLEDGE_OWNER_ID' in missing.value.message
