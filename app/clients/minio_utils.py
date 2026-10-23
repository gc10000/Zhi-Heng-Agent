"""旧入口按需获取MinIO客户端；建桶和策略只能由显式管理操作处理。"""
import threading

minio_client = None
_lock = threading.Lock()


def get_minio_client():
    global minio_client
    with _lock:
        if minio_client is None:
            from minio import Minio
            from app.conf.minio_config import minio_config
            fields = {'MINIO_ENDPOINT': minio_config.endpoint, 'MINIO_ACCESS_KEY': minio_config.access_key,
                      'MINIO_SECRET_KEY': minio_config.secret_key}
            missing = [key for key, value in fields.items() if not value]
            if missing:
                raise ValueError('请在根目录.env配置' + '、'.join(missing) + '，用于旧导入对象存储。')
            minio_client = Minio(endpoint=minio_config.endpoint, access_key=minio_config.access_key,
                                 secret_key=minio_config.secret_key, secure=minio_config.minio_secure)
        return minio_client
