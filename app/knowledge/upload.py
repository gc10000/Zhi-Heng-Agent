"""上传内容与名称分开；名称不能参与本机路径或对象键。"""
import json
from pathlib import Path, PureWindowsPath
from tempfile import TemporaryDirectory
from uuid import uuid4
from pydantic import BaseModel, ConfigDict, Field
from app.api.errors import APIError
from app.identity.api import require_kb, require_writer
from app.ingestion.parsers.router import detect_format
from app.knowledge.models import content_hash
from app.knowledge.repository import ConflictError, fingerprint

MIME = {'pdf': {'application/pdf'}, 'md': {'text/markdown', 'text/plain'},
        'xlsx': {'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'}}


def validate_upload(name, media_type, data, max_bytes):
    if not name or len(name) > 255 or name in {'.', '..'} or any(c in name for c in '/\\:\x00\r\n') or PureWindowsPath(name).is_absolute():
        raise APIError(422, 'invalid_filename', '文件名不能包含路径或控制字符。')
    kind = Path(name).suffix.lower().lstrip('.')
    if kind not in MIME or media_type.split(';', 1)[0].lower() not in MIME[kind]:
        raise APIError(415, 'unsupported_media', '仅支持声明类型匹配的PDF、Markdown和XLSX。')
    if len(data) > max_bytes:
        raise APIError(413, 'upload_too_large', '原件超过上传大小限制。')
    if not data:
        raise APIError(422, 'empty_file', '原件不能为空。')
    with TemporaryDirectory(prefix='support-upload-') as temp:
        path = Path(temp) / ('original.' + kind)
        path.write_bytes(data)
        try:
            detect_format(path)
        except ValueError:
            raise APIError(422, 'invalid_document', '原件内容与声明格式不符或已损坏。') from None
    return kind


def product_list(value):
    try:
        products = json.loads(value)
        if not isinstance(products, list) or len(products) > 50 or any(not isinstance(v, str) or not v for v in products):
            raise ValueError()
        return products
    except (ValueError, TypeError):
        raise APIError(422, 'invalid_products', 'product_ids必须是最多50个非空字符串的JSON列表。') from None


class UploadService:
    def __init__(self, gateway):
        self.gateway = gateway
        self.uploads = gateway.db.document_uploads
        self.uploads.create_index([('owner_id', 1), ('kb_id', 1), ('client_request_id', 1)], unique=True)

    def upload(self, user, *, kb_id, client_request_id, name, media_type, data, product_ids,
               document_id=None, purpose='unknown'):
        require_writer(user)
        require_kb(user, kb_id)
        if not client_request_id or len(client_request_id) > 128 or purpose not in {'unknown', 'technical', 'project_plan'}:
            raise APIError(422, 'invalid_upload', '请求标识或资料用途格式错误。')
        kind = validate_upload(name, media_type, data, self.gateway.max_upload_bytes)
        for pid in product_ids:
            self.gateway.product(user, pid, kb_id)
        repo = self.gateway.repo(kb_id)
        original = repo.get_document(document_id) if document_id else None
        signature = fingerprint({'name': name, 'sha256': content_hash(data), 'product_ids': product_ids,
                                 'document_id': document_id, 'purpose': purpose, 'format': kind})
        key = {'owner_id': user.user_id, 'kb_id': kb_id, 'client_request_id': client_request_id}
        request_id = fingerprint(key)
        saved = repo._insert_once(self.uploads, key,
            key | {'request_fingerprint': signature, 'object_key': self.gateway.originals.prefix + 'uploads/' + uuid4().hex,
                   'state': 'preparing', 'request_id': request_id,
                   'expected_active': original['active_revision_id'] if original else None})
        if saved['state'] == 'accepted':
            return {k: saved[k] for k in ('document_id', 'revision_id', 'job_id', 'original_asset_id') if k in saved}
        document = repo.register_document(request_id, name=name, product_ids=product_ids, purpose=purpose) if original is None else None
        did = original['document_id'] if original else document.document_id
        revision = repo.create_revision(did, request_id, original_sha256=content_hash(data), object_key=saved['object_key'])
        self.gateway.originals.put(saved['object_key'], data, media_type=media_type)
        from app.knowledge.asset_api import original_asset
        aid = original_asset(self.gateway, repo.get_revision(revision.revision_id), media_type=media_type, name=name)
        job = self.gateway.jobs.register(user, repo.get_revision(revision.revision_id), original_name=name,
                                         original_format=kind, expected_active=saved['expected_active'])
        result = {'document_id': did, 'revision_id': revision.revision_id, 'job_id': job['job_id'], 'original_asset_id': aid}
        self.uploads.update_one(key | {'request_fingerprint': signature}, {'$set': result | {'state': 'accepted'}})
        return result
