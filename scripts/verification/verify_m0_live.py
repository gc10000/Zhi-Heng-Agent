"""M0 显式真实小样：复制四个旧切片及配图到独立命名空间，保留证据不清理。

会调用真实文本模型/BGE/重排及本机存储；绝不导入旧 MinIO 自动策略封装。
"""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.parse import unquote, urlsplit, quote
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.verification.image_acceptance import bind_assets, verify_image_answer, http_image_fetcher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-live', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    required = ('MILVUS_URL', 'CHUNKS_COLLECTION', 'ITEM_NAME_COLLECTION', 'MONGO_URL', 'MONGO_DB_NAME',
                'MINIO_ENDPOINT', 'MINIO_ACCESS_KEY', 'MINIO_SECRET_KEY', 'MINIO_BUCKET_NAME',
                'OPENAI_BASE_URL', 'OPENAI_API_KEY', 'LLM_DEFAULT_MODEL', 'BGE_M3_PATH', 'BGE_RERANKER_LARGE')
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        print(json.dumps({'missing': missing, 'fill_in': '.env', 'impact': 'M0-09 真实小样'}, ensure_ascii=True))
        return 2
    os.environ.update(LOG_CONSOLE_ENABLE='False', LOG_FILE_ENABLE='False', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    # 下载被禁用，必须已有本地权重。
    for name in ('BGE_M3_PATH', 'BGE_RERANKER_LARGE'):
        if not Path(os.environ[name]).is_dir():
            print(json.dumps({'missing_local_model': name, 'impact': 'M0-09'}, ensure_ascii=True))
            return 2
    source_chunks, source_items = os.environ['CHUNKS_COLLECTION'], os.environ['ITEM_NAME_COLLECTION']
    original_db = os.environ['MONGO_DB_NAME']
    suffix = time.strftime('%Y%m%d_%H%M%S') + '_' + uuid.uuid4().hex[:6]
    chunks, items = f'm0_test_{suffix}_chunks', f'm0_test_{suffix}_items'
    database = f'm0_test_{suffix}'
    prefix = f'm0-test/{suffix}/'
    assert chunks.startswith('m0_test_') and chunks != source_chunks
    assert items.startswith('m0_test_') and items != source_items
    assert database.startswith('m0_test_') and database != original_db
    assert prefix.startswith('m0-test/')
    report = {'status': 'running', 'started_at': time.strftime('%Y-%m-%dT%H:%M:%S%z'),
              'scope': {'mongo_database': database, 'chunks': chunks, 'items': items, 'object_prefix': prefix},
              'source_document': 'H3C-LA2608-用户手册-联调节选', 'questions': [], 'objects': [],
              'external': {'mcp': '缺配置，不计为已验证', 'kg': '原占位节点，不计为知识能力'},
              'fake': False, 'cleanup': '未执行删除；保留独立数据供审查'}
    expectation = json.loads((ROOT / 'evals/datasets/m0-image-expectation.json').read_text(encoding='utf-8'))
    report['image_expectation'] = expectation
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    save()
    from pymilvus import MilvusClient, DataType
    from pymongo import MongoClient
    from minio import Minio
    import urllib3
    client = MilvusClient(uri=os.environ['MILVUS_URL'], timeout=10)
    mongo = MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000)
    storage = Minio(os.environ['MINIO_ENDPOINT'], os.environ['MINIO_ACCESS_KEY'], os.environ['MINIO_SECRET_KEY'],
                    secure=os.getenv('MINIO_SECURE', '').lower() == 'true',
                    http_client=urllib3.PoolManager(timeout=10, retries=False))
    bucket = os.environ['MINIO_BUCKET_NAME']
    try:
        assert not client.has_collection(chunks) and not client.has_collection(items)
        source = client.query(collection_name=source_chunks,
                              filter='file_title == "H3C-LA2608-用户手册-联调节选"',
                              output_fields=['*'], limit=10, consistency_level='Strong')
        assert len(source) == 4, '小样来源数量改变，需要复核'
        product = source[0]['item_name']
        product_rows = client.query(collection_name=source_items, filter='item_name == ' + json.dumps(product),
                                    output_fields=['*'], limit=10, consistency_level='Strong')
        assert product_rows, '缺少真实产品向量'
        report['source_chunk_ids'] = [str(row['chunk_id']) for row in source]
        report['source_hashes'] = {str(row['chunk_id']): hashlib.sha256(row['content'].encode()).hexdigest() for row in source}
        report['source_read_only'] = True
        # 所有配置覆盖必须发生在首次应用导入前，dotenv 默认不覆盖进程变量。
        os.environ.update(CHUNKS_COLLECTION=chunks, ITEM_NAME_COLLECTION=items, MONGO_DB_NAME=database)
        from app.import_process.agent.nodes.node_import_milvus import create_collection
        create_collection(client, chunks, len(source[0]['dense_vector']))
        schema = client.create_schema(auto_id=True, enable_dynamic_field=True)
        schema.add_field('pk', DataType.INT64, is_primary=True, auto_id=True)
        schema.add_field('item_name', DataType.VARCHAR, max_length=65535)
        schema.add_field('file_title', DataType.VARCHAR, max_length=65535)
        schema.add_field('dense_vector', DataType.FLOAT_VECTOR, dim=1024)
        schema.add_field('sparse_vector', DataType.SPARSE_FLOAT_VECTOR)
        indexes = client.prepare_index_params()
        indexes.add_index('dense_vector', index_type='FLAT', metric_type='COSINE')
        indexes.add_index('sparse_vector', index_type='SPARSE_INVERTED_INDEX', metric_type='IP')
        client.create_collection(items, schema=schema, index_params=indexes)
        row = product_rows[0]
        client.insert(items, [{key: row[key] for key in ('item_name', 'file_title', 'dense_vector', 'sparse_vector')}])
        copied_urls = {}
        scheme = 'https' if os.getenv('MINIO_SECURE', '').lower() == 'true' else 'http'
        for row in source:
            for url in re.findall(r'!\[.*?\]\((.*?)\)', row['content']):
                if url in copied_urls:
                    continue
                parsed = urlsplit(url)
                assert parsed.netloc == os.environ['MINIO_ENDPOINT'] and not parsed.query, '图片源需要人工复核，不记录 URL'
                path = unquote(parsed.path).lstrip('/')
                assert path.startswith(bucket + '/'), '不读取未知桶'
                source_key = path[len(bucket) + 1:]
                response = storage.get_object(bucket, source_key)
                try:
                    data = response.read()
                    content_type = response.headers.get('Content-Type', 'image/png')
                finally:
                    response.close()
                    response.release_conn()
                key = prefix + hashlib.sha256(data).hexdigest() + Path(source_key).suffix
                assert key.startswith(prefix)
                storage.put_object(bucket, key, io.BytesIO(data), len(data), content_type=content_type)
                copied_urls[url] = f'{scheme}://{os.environ["MINIO_ENDPOINT"]}/{bucket}/{quote(key)}'
                report['objects'].append({'key': key, 'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)})
        data = []
        for row in source:
            copy = {key: row[key] for key in ('content', 'title', 'parent_title', 'part', 'file_title', 'item_name', 'dense_vector', 'sparse_vector')}
            for old_url, new_url in copied_urls.items():
                copy['content'] = copy['content'].replace(old_url, new_url)
            data.append(copy)
        inserted = client.insert(chunks, data)
        report['copied_chunk_ids'] = [str(i) for i in inserted['ids']]
        client.flush(chunks)
        client.flush(items)
        client.load_collection(chunks)
        client.load_collection(items)
        report['models'] = {'llm': os.environ['LLM_DEFAULT_MODEL'], 'embedding': '本地 BGE-M3', 'reranker': '本地 bge-reranker-large',
                            'embedding_device': os.getenv('BGE_DEVICE'), 'reranker_device': os.getenv('BGE_RERANKER_DEVICE')}
        report['prompt_sha256'] = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (ROOT / 'prompts').glob('*.prompt')}
        assets = bind_assets(report['objects'], f'{scheme}://{os.environ["MINIO_ENDPOINT"]}', bucket, prefix)
        save()
        from app.query_process.api import query_service as api
        from app.utils import task_utils, sse_utils
        sid = 'm0-live-' + suffix
        queue = sse_utils.create_sse_queue(sid)
        questions = [
            ('known', product + '如何验证设备与无线控制器已经连通？请说明命令和正常状态。', ['display wlan ap', 'R/M']),
            ('followup', '刚才提到的 R/M 分别表示什么？', ['Run', 'Master']),
            ('image', product + '通过什么网络连接无线控制器？请附上连接拓扑示意图。', ['3G', '4G']),
        ]
        for kind, question, expected in questions:
            while not queue.empty():
                queue.get_nowait()
            started = time.perf_counter()
            api.run_query_graph(sid, question, True)
            elapsed = time.perf_counter() - started
            events = list(queue.queue)
            answer = task_utils.get_task_result(sid, 'answer')
            status = task_utils.get_task_status(sid)
            finals = [e for e in events if e['event'] == 'final']
            images = finals[0]['data'].get('image_urls', []) if finals else []
            checks = {'completed': status == 'completed', 'one_final': len(finals) == 1,
                      'no_error': not any(e['event'] == 'error' for e in events),
                      'expected_facts': all(s.casefold() in answer.casefold() for s in expected),
                      'assistant_saved': mongo[database]['chat_message'].count_documents({'session_id': sid, 'role': 'assistant'}) == len(report['questions']) + 1}
            if kind == 'image':
                verification = verify_image_answer(answer, finals[0]['data'].get('answer', '') if finals else '',
                                                   images, assets, expectation['sha256'], prefix,
                                                   http_image_fetcher(urllib3.PoolManager(timeout=10, retries=False)))
                checks.update(verification['checks'])
                report['image_verification'] = verification
            # 不存完整 prompt/签名链接；正文里的独立图片 URL 转成对象占位标记。
            safe_answer = re.sub(r'https?://\S+', '[隔离图片对象，详见 objects]', answer)
            entry = {'kind': kind, 'question': question, 'status': status, 'elapsed_seconds': round(elapsed, 3),
                     'answer': safe_answer, 'checks': checks, 'events': [e['event'] for e in events],
                     'image_count': len(images)}
            report['questions'].append(entry)
            save()
            print(json.dumps({'kind': kind, 'status': status, 'elapsed_seconds': entry['elapsed_seconds'], 'checks': checks}, ensure_ascii=True), flush=True)
            assert all(checks.values()), '真实小样验收未通过，详情见证据文件'
        from app.clients.mongo_history_utils import get_recent_messages
        report['history_count'] = len(get_recent_messages(sid, 10))
        assert report['history_count'] == 6
        report['status'] = 'passed'
        save()
        return 0
    except Exception as exc:
        report['status'] = 'failed'
        report['error_type'] = type(exc).__name__
        save()
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__, 'evidence': str(args.output)}, ensure_ascii=True))
        return 1
    finally:
        client.close()
        mongo.close()


if __name__ == '__main__':
    raise SystemExit(main())
