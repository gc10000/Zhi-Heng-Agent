"""统一API配置仅在启动阶段读取，不在模块导入时读取私有配置。"""
import os
from dataclasses import dataclass


class ConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class Settings:
    mongo_url: str
    database: str
    origins: tuple[str, ...] = ('http://localhost:8000',)
    cookie_secure: bool = True
    session_seconds: int = 28800
    run_lease_seconds: int = 60
    input_wait_seconds: int = 86400
    run_pending_seconds: int = 300
    knowledge_owner_id: str | None = None
    object_bucket: str | None = None
    object_prefix: str | None = None
    milvus_collection: str | None = None
    upload_max_bytes: int = 100_000_000

    def provider_capabilities(self):
        """仅说明本机配置，既不请求模型列表也不做付费探针。"""
        from app.infrastructure.providers.policy import capabilities
        return capabilities()

    @classmethod
    def load(cls):
        from dotenv import load_dotenv
        load_dotenv()
        missing = [key for key in ('MONGO_URL', 'M2_DB_NAME') if not os.getenv(key, '').strip()]
        if missing:
            raise ConfigurationError('缺少配置变量：' + '、'.join(missing) + '；请填写根目录.env，用于统一API运行账本。')
        origins = tuple(x.strip().rstrip('/') for x in os.getenv('API_ALLOWED_ORIGINS', 'http://localhost:8000').split(',') if x.strip())
        if not origins or '*' in origins:
            raise ConfigurationError('API_ALLOWED_ORIGINS必须填写明确的同源地址，不能使用通配符。')
        secure = os.getenv('API_COOKIE_SECURE', 'true').lower()
        if secure not in {'true', 'false'}:
            raise ConfigurationError('API_COOKIE_SECURE必须为true或false。')
        values = {}
        for name, default, field in [('RUN_LEASE_SECONDS', 60, 'run_lease_seconds'),
                                     ('RUN_INPUT_WAIT_SECONDS', 86400, 'input_wait_seconds'),
                                     ('RUN_PENDING_SECONDS', 300, 'run_pending_seconds'),
                                     ('UPLOAD_MAX_BYTES', 100_000_000, 'upload_max_bytes')]:
            try:
                values[field] = int(os.getenv(name, str(default)))
                if values[field] < 1:
                    raise ValueError()
            except ValueError:
                raise ConfigurationError(name + '必须为正整数秒。') from None
        return cls(os.environ['MONGO_URL'], os.environ['M2_DB_NAME'], origins, secure == 'true',
            knowledge_owner_id=os.getenv('M2_KNOWLEDGE_OWNER_ID') or None,
            object_bucket=os.getenv('M2_OBJECT_BUCKET') or None, object_prefix=os.getenv('M2_OBJECT_PREFIX') or None,
            milvus_collection=os.getenv('M2_MILVUS_COLLECTION') or None, **values)
