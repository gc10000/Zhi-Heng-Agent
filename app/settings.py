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
                                     ('RUN_PENDING_SECONDS', 300, 'run_pending_seconds')]:
            try:
                values[field] = int(os.getenv(name, str(default)))
                if values[field] < 1:
                    raise ValueError()
            except ValueError:
                raise ConfigurationError(name + '必须为正整数秒。') from None
        return cls(os.environ['MONGO_URL'], os.environ['M2_DB_NAME'], origins, secure == 'true', **values)
