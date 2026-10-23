"""只读环境核查；仅输出配置名称和存在性，不输出连接串或凭据。"""
import argparse
import ast
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import re
import sys

ROOT = Path(__file__).resolve().parents[2]


def inspect_environment(live=False):
    from dotenv import dotenv_values
    values = {**dotenv_values(ROOT / '.env'), **os.environ}
    names = set(re.findall(r'^([A-Z][A-Z0-9_]*)=', (ROOT / '.env.example').read_text(encoding='utf-8'), re.M))
    for path in (ROOT / 'app').rglob('*.py'):
        names.update(re.findall(r'(?:getenv|environ.get)\([\"\x27]([A-Z][A-Z0-9_]*)', path.read_text(encoding='utf-8')))
    report = {
        'python': sys.version, 'platform': platform.platform(),
        'packages': {d.metadata['Name']: d.version for d in metadata.distributions()},
        'configuration': {n: bool(values.get(n)) for n in sorted(names)},
        'missing': sorted(n for n in names if not values.get(n)),
        'namespaces': {'mongo': 'm0_test_20261022', 'chunks': 'm0_test_20261022_chunks',
                       'items': 'm0_test_20261022_items', 'objects': 'm0-test/20261022/'},
        'inventory': {}, 'routes': [], 'writes': 0,
    }
    import torch
    report['hardware'] = {'torch': torch.__version__, 'cuda_build': torch.version.cuda,
                          'cuda_available': torch.cuda.is_available(),
                          'gpu': [torch.cuda.get_device_name(i) for i in range(torch.cuda.device_count())]}
    for path in (ROOT / 'app').rglob('*service.py'):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for dec in node.decorator_list:
                    if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute) and dec.args and isinstance(dec.args[0], ast.Constant):
                        report['routes'].append([str(path.relative_to(ROOT)), dec.func.attr, dec.args[0].value])
    if live:
        # 直接使用只读 SDK；不导入会自动建索引/改桶策略的应用封装。
        def mongo():
            from pymongo import MongoClient
            with MongoClient(values.get('MONGO_URL'), serverSelectionTimeoutMS=3000) as client:
                return client[values['MONGO_DB_NAME']].list_collection_names()
        def milvus():
            from pymilvus import MilvusClient
            client = MilvusClient(uri=values['MILVUS_URL'], timeout=3)
            try:
                return client.list_collections(timeout=3)
            finally:
                client.close()
        def minio():
            from minio import Minio
            import urllib3
            client = Minio(values['MINIO_ENDPOINT'], values['MINIO_ACCESS_KEY'], values['MINIO_SECRET_KEY'],
                           secure=values.get('MINIO_SECURE', '').lower() == 'true',
                           http_client=urllib3.PoolManager(timeout=3, retries=False))
            return [b.name for b in client.list_buckets()]
        for name, call in [('mongo', mongo), ('milvus', milvus), ('minio', minio)]:
            try:
                report['inventory'][name] = {'status': '已实测，只读', 'names': call()}
            except Exception as exc:
                report['inventory'][name] = {'status': '不可用', 'error_type': type(exc).__name__}
    else:
        report['inventory']['status'] = '未连接；需 --live-inventory 显式只读核对'
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--redact', action='store_true', help='始终脱敏，保留该参数供验收命令使用')
    parser.add_argument('--live-inventory', action='store_true', help='仅列出现有集合和桶，不写入')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = inspect_environment(args.live_inventory)
    payload = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding='utf-8')
    print(payload)
