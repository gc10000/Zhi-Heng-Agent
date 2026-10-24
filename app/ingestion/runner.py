"""对象原件驱动的持久导入，阶段重试复用解析/图片摘要/向量检查点。"""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from app.api.errors import APIError
from app.ingestion.dispatcher import validate_key
from app.ingestion.jobs import JobRepository
from app.ingestion.checkpoints import Checkpoints, CheckpointEmbedder
from app.ingestion.models import ParsedDocument
from app.ingestion.parsers.router import ParserRouter, detect_format
from app.ingestion.parsers.markdown import MarkdownParser
from app.ingestion.parsers.excel import ExcelParser
from app.ingestion.parsers.mineru import MineruParser, MinerUProvider, ProviderTimeout
from app.ingestion.stages.images import ImageSummaryService, VisionDescriber, SummaryBusy, process_images
from app.ingestion.stages.chunking import chunk_document, VERSION as CHUNKER_VERSION
from app.knowledge.assets import AssetStore, MongoSummaryCache
from app.knowledge.repository import KnowledgeRepository, ConflictError, fingerprint
from app.knowledge.publishing import RevisionPublisher
from app.knowledge.models import content_hash
from app.infrastructure.queue.model_client import HostEmbedder


def classify_error(exc):
    status = getattr(exc, 'status_code', None) or getattr(getattr(exc, 'response', None), 'status_code', None)
    if isinstance(exc, APIError) and exc.code == 'job_lease_lost':
        return 'lease_lost', False
    if status == 429:
        return 'provider_rate_limited', True
    if status in {401, 403}:
        return 'provider_authentication_failed', False
    if status and status >= 500:
        return 'provider_unavailable', True
    import requests
    import httpx
    from openai import APITimeoutError, APIConnectionError
    # SDK 超时继承连接异常，须先分类；公开信息仅保留错误码。
    if isinstance(exc, (TimeoutError, requests.Timeout, httpx.TimeoutException, APITimeoutError, ProviderTimeout, SummaryBusy)):
        return 'upstream_timeout', True
    if isinstance(exc, (ConnectionError, requests.ConnectionError, httpx.NetworkError, APIConnectionError)):
        return 'upstream_connection_failed', True
    return ('version_conflict', False) if isinstance(exc, ConflictError) else ('invalid_document_or_configuration', False)


class FencedDocuments:
    def __init__(self, collection, permit):
        self.collection, self.permit = collection, permit
    def __getattr__(self, name):
        return getattr(self.collection, name)
    def update_one(self, query, update, *args, **kwargs):
        if 'active_revision_id' in query:
            query = query | {'import_permit': self.permit, 'import_lease_until': {'$gt': datetime.now(timezone.utc)}}
        return self.collection.update_one(query, update, *args, **kwargs)


def import_permit(row):
    return {'job_id': row['job_id'], 'attempt': row['attempt'], 'token': row['lease_token']}


def claim_import_permit(repo, row):
    now = datetime.now(timezone.utc)
    permit = import_permit(row)
    # 单资料原子接管：跨任务仅接受过期许可；同任务不倒退attempt或替换同代token。
    result = repo.documents.update_one(repo.scope | {'document_id': row['document_id'], '$or': [
        {'import_permit': {'$exists': False}},
        {'import_permit': permit},
        {'import_permit.job_id': row['job_id'], 'import_permit.attempt': {'$lt': row['attempt']}},
        {'import_permit.job_id': {'$ne': row['job_id']}, 'import_lease_until': {'$lte': now}}]},
        {'$set': {'import_permit': permit, 'import_lease_until': row['lease_until']}})
    if not result.matched_count:
        raise ConflictError('资料正在由其他任务或新attempt处理')
    return permit


def renew_import_permit(db, row, lease_until):
    # 迟到心跳不复活已过期许可，更不能续约接管者的许可。
    return db.knowledge_documents.update_one({'document_id': row['document_id'],
        'import_permit': import_permit(row), 'import_lease_until': {'$gt': datetime.now(timezone.utc)}},
        {'$set': {'import_lease_until': lease_until}})


def release_import_permit(db, row):
    return db.knowledge_documents.update_one({'document_id': row['document_id'], 'import_permit': import_permit(row)},
        {'$unset': {'import_permit': '', 'import_lease_until': ''}})


class ImportRunner:
    def __init__(self, jobs, gateway, *, router, embedder, summary, model, prompt_version, work_dir):
        self.jobs, self.gateway, self.router, self.encode, self.summary = jobs, gateway, router, embedder, summary
        self.model, self.prompt_version, self.work_dir = model, prompt_version, Path(work_dir)
        self.summary.strict_errors = True

    def execute(self, row):
        validate_key(row['object_key'])
        if row['knowledge_owner_id'] != self.gateway.owner_id:
            raise ValueError('任务知识归属与worker配置不符')
        cp = Checkpoints(self.jobs, row, self.gateway.originals)
        cp.fence()
        repo = self.gateway.repo(row['kb_id'])
        revision = repo.get_revision(row['revision_id'])
        permit = claim_import_permit(repo, cp.fence())
        repo.documents = FencedDocuments(repo.documents, permit)
        originals = self.gateway.originals
        index = self.gateway.index()
        index.ensure_collection()
        assets = AssetStore(repo.db, originals.client, bucket=originals.bucket, prefix=originals.prefix + 'assets/')
        publisher = RevisionPublisher(repo, index, read_original=originals.read, asset_store=assets)
        if revision['status'] == 'published':
            cp.fence()
            return {'document_id': row['document_id'], 'revision_id': row['revision_id']}
        signature = fingerprint({'format': row['format'], 'parser': getattr(self.router.parsers[row['format']], 'version', '1'),
                                 'chunker': CHUNKER_VERSION, 'model': self.model, 'prompt': self.prompt_version, 'pipeline': 'm2-1'})
        reserved = repo.revisions.update_one(repo.scope | {'revision_id': row['revision_id'], '$or': [
            {'m2_pipeline_identity': {'$exists': False}}, {'m2_pipeline_identity': signature}]}, {'$set': {'m2_pipeline_identity': signature}})
        if not reserved.matched_count:
            raise ConflictError('处理配置变化，必须新建修订')
        if revision['status'] == 'validated':
            cp.fence()
            document = repo.get_document(row['document_id'])
            if document['active_revision_id'] == row['revision_id']:
                publisher.reconcile(row['document_id'])
            else:
                publisher.publish(row['revision_id'], expected_active=row['expected_active'])
            return {'document_id': row['document_id'], 'revision_id': row['revision_id']}
        attempt = repo.claim_attempt(row['revision_id'], expected_attempt=revision['attempt'])
        stage = row.get('checkpoints', {}).get('parsed')
        with TemporaryDirectory(prefix='support-import-') as temp:
            root = Path(temp)
            raw = originals.get(row['object_key'], row['sha256'])
            path = root / ('original.' + row['format'])
            path.write_bytes(raw)
            detect_format(path)
            if stage:
                parsed = ParsedDocument(**json.loads(originals.get(stage['object_key'], stage['sha256'])))
            else:
                cp.save('parsing', {'format': row['format']})
                parsed = self.router.parse(path, document_id=row['document_id'], revision_id=row['revision_id'])
                if parsed.original_sha256 != row['sha256']:
                    raise ValueError('解析结果原件hash不一致')
                image_sources = {i.image_id: originals.put_image_source(row['revision_id'], i.image_id, Path(i.local_path).read_bytes()) for i in parsed.images}
                stage = originals.put_parsed(row['revision_id'], parsed.model_dump_json().encode()) | {'images': image_sources}
                cp.fence()
                cp.save('parsed', stage)
            if parsed.document_id != row['document_id'] or parsed.revision_id != row['revision_id']:
                raise ValueError('解析缓存跨修订')
            if any(f in parsed.quality_flags for f in ('missing_image', 'external_image_unresolved')):
                raise ValueError('图片来源未解析，不能发布')
            restored = []
            for image in parsed.images:
                saved = stage['images'][image.image_id]
                target = root / (content_hash(image.image_id.encode()) + '.image')
                target.write_bytes(originals.get(saved['object_key'], saved['sha256']))
                restored.append(image.model_copy(update={'local_path': str(target)}))
            parsed = parsed.model_copy(update={'images': tuple(restored)})
            cp.save('images', {'count': len(parsed.images)})
            parsed, _ = process_images(parsed, assets, self.summary, model=self.model, prompt_version=self.prompt_version)
            cp.fence()
            cp.save('images_completed', {'count': len(parsed.images)})
            doc = repo.get_document(row['document_id'])
            chunks = chunk_document(parsed, default_product_ids=doc['product_ids'])
            encoder = CheckpointEmbedder(cp, self.encode, identity='bge-m3-existing')
            index.write_revision(repo, row['revision_id'], chunks, attempt=attempt, embedder=encoder)
            cp.save('indexed', repo.get_revision(row['revision_id'])['stages']['indexed'])
            cp.fence()
            repo.revisions.update_one(repo.scope | {'revision_id': row['revision_id'], 'attempt': attempt},
                {'$set': {'parser_version': parsed.parser_version, 'quality_flags': list(parsed.quality_flags)}})
            publisher.validate(row['revision_id'], attempt=attempt)
            cp.fence()
            publisher.publish(row['revision_id'], expected_active=row['expected_active'])
            cp.save('published', {'revision_id': row['revision_id']})
        return {'document_id': row['document_id'], 'revision_id': row['revision_id']}


def configured_runner(jobs, gateway):
    from redis import Redis
    from openai import OpenAI
    from app.infrastructure.rate_limits import RedisRateStore, SharedRateLimiter
    from urllib.parse import urlparse
    work = Path(os.getenv('M2_WORK_DIR', '/var/lib/knowledge-worker'))
    model = os.getenv('VL_MODEL', '')
    # 无图片的资料不要求视觉供应商配置，真正调用时SDK再明确报缺配置。
    def describe(data, context):
        if not os.getenv('OPENAI_API_KEY') or not os.getenv('OPENAI_BASE_URL') or not model:
            raise ValueError('缺OPENAI_API_KEY/OPENAI_BASE_URL/VL_MODEL，填写根目录.env用于图片摘要')
        client = OpenAI(api_key=os.environ['OPENAI_API_KEY'], base_url=os.environ['OPENAI_BASE_URL'])
        host = urlparse(os.environ['OPENAI_BASE_URL']).hostname or ''
        provider = os.getenv('LLM_PROVIDER', 'auto')
        dashscope = provider == 'dashscope' or (provider == 'auto' and (host == 'dashscope.aliyuncs.com' or host.endswith('.dashscope.aliyuncs.com')))
        if provider not in {'auto', 'dashscope', 'openai_compatible'}:
            raise ValueError('LLM_PROVIDER配置不支持')
        options = {'extra_body': {'enable_thinking': os.getenv('LLM_ENABLE_THINKING', 'false').lower() == 'true'}} if dashscope else {}
        return VisionDescriber(client, model, '请用中文准确描述设备技术图示，保留端口、型号与连接关系。', request_options=options)(data, context)
    summary = ImageSummaryService(MongoSummaryCache(jobs.db),
        SharedRateLimiter(RedisRateStore(Redis.from_url(os.environ['REDIS_URL'])), 'vision:' + model,
                          requests_per_minute=float(os.getenv('VISION_REQUESTS_PER_MINUTE', '30'))), describe)
    router = ParserRouter({'md': MarkdownParser(), 'xlsx': ExcelParser(),
                           'pdf': MineruParser(MinerUProvider(), work / 'mineru')})
    return ImportRunner(jobs, gateway, router=router, embedder=HostEmbedder(), summary=summary,
                        model=model or 'unconfigured', prompt_version='m2-vision-1', work_dir=work)


def run_import(job_id):
    from pymongo import MongoClient
    from app.settings import Settings
    from app.knowledge.resources import KnowledgeResources
    settings = Settings.load()
    lease, interval = int(os.getenv('JOB_LEASE_SECONDS', '60')), int(os.getenv('JOB_HEARTBEAT_SECONDS', '10'))
    if lease <= interval or interval < 1:
        raise ValueError('JOB_HEARTBEAT_SECONDS必须为正且小于JOB_LEASE_SECONDS')
    with MongoClient(settings.mongo_url, serverSelectionTimeoutMS=5000, tz_aware=True) as client:
        jobs = JobRepository(client[settings.database])
        row = jobs.claim(job_id, lease_seconds=lease)
        if row is None:
            return
        resources = KnowledgeResources(jobs.db, settings)
        stop = threading.Event()
        def heartbeat():
            while not stop.wait(interval):
                try:
                    jobs.renew(job_id, row['attempt'], row['lease_token'], lease_seconds=lease)
                    current = jobs.fence(job_id, row['attempt'], row['lease_token'])
                    renew_import_permit(jobs.db, row, current['lease_until'])
                except Exception:
                    return
        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()
        try:
            result = configured_runner(jobs, resources.get()).execute(row)
            jobs.save(job_id, row['attempt'], row['lease_token'], {'state': 'completed', 'stage': 'published', 'result': result})
        except Exception as exc:
            code, retryable = classify_error(exc)
            try:
                jobs.save(job_id, row['attempt'], row['lease_token'],
                    {'state': 'failed', 'retryable': retryable, 'error': {'code': code, 'stage': jobs.fence(job_id, row['attempt'], row['lease_token'])['stage']}})
            except APIError:
                pass
        finally:
            stop.set()
            thread.join(timeout=interval+1)
            release_import_permit(jobs.db, row)
            resources.close()
