"""在已准备的独立小样上续验，不重建集合或复制对象。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.verification.image_acceptance import bind_assets, verify_image_answer, http_image_fetcher


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--cpu-threads', type=int, default=1)
    parser.add_argument('--prewarm-reranker', action='store_true')
    parser.add_argument('--only', choices=['image'], help='沿用原会话，仅续验失败图片题，保留已通过问题')
    args = parser.parse_args()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    report = json.loads(args.source.read_text(encoding='utf-8'))
    expectation = json.loads((ROOT / 'evals/datasets/m0-image-expectation.json').read_text(encoding='utf-8'))
    report['image_expectation'] = expectation
    previous_questions = report.get('questions', [])
    if args.only:
        report.setdefault('previous_attempts', []).extend(q for q in previous_questions if q['kind'] == args.only)
        previous_questions = [q for q in previous_questions if q['kind'] != args.only]
    else:
        previous_questions = []
    report.update(status='running', questions=previous_questions, resumed_from=str(args.source),
                  validation_cpu_threads=args.cpu_threads, prewarm_reranker=args.prewarm_reranker)
    report.pop('graph_exception_chain', None)
    report.pop('failure_phase', None)
    report.pop('image_verification', None)
    if not args.prewarm_reranker:
        report.pop('reranker_target_devices', None)
    report.pop('error_type', None)
    report.pop('process_exit_code', None)
    scope = report['scope']
    assert all(scope[key].startswith('m0_test_') for key in ('mongo_database', 'chunks', 'items'))
    assert scope['object_prefix'].startswith('m0-test/')
    os.environ.update(CHUNKS_COLLECTION=scope['chunks'], ITEM_NAME_COLLECTION=scope['items'],
                      MONGO_DB_NAME=scope['mongo_database'], LOG_CONSOLE_ENABLE='False', LOG_FILE_ENABLE='False',
                      HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      OMP_NUM_THREADS=str(args.cpu_threads), MKL_NUM_THREADS=str(args.cpu_threads))
    def save():
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    save()
    import faulthandler
    faulthandler.enable()
    import torch
    torch.set_num_threads(args.cpu_threads)
    torch.set_num_interop_threads(args.cpu_threads)
    from pymilvus import MilvusClient
    from pymongo import MongoClient
    import urllib3
    milvus = MilvusClient(uri=os.environ['MILVUS_URL'], timeout=10)
    mongo = MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000)
    from app.core.logger import logger
    # 输出位置元信息定位原生崩溃，不回显消息、prompt 或 URL。
    def stage(message):
        record = message.record
        report['last_stage'] = f"{record['name']}:{record['function']}:{record['line']}"
        save()
    logger.add(stage, level='INFO')
    if args.prewarm_reranker:
        from app.lm.reranker_utils import get_reranker_model
        print('prewarming=reranker', flush=True)
        model = get_reranker_model()
        report['reranker_target_devices'] = model.target_devices
        report['prewarm_reranker'] = True
        save()
    from app.query_process.api import query_service as api
    # 包装真实图的调用边界，仅采集异常类型和代码位置，不改返回值、不回显异常正文。
    real_graph = api.get_query_app()
    class DiagnosticGraph:
        def invoke(self, state):
            try:
                return real_graph.invoke(state)
            except Exception as exc:
                chain = []
                while exc is not None:
                    chain.append({'type': type(exc).__name__, 'http_status': getattr(exc, 'status_code', None),
                                  'frames': [{'file': Path(f.filename).name, 'function': f.name, 'line': f.lineno}
                                             for f in traceback.extract_tb(exc.__traceback__)]})
                    exc = exc.__cause__
                report['graph_exception_chain'] = chain
                save()
                raise
    api.query_app = DiagnosticGraph()
    from app.utils import task_utils, sse_utils
    from app.clients.mongo_history_utils import get_recent_messages
    try:
        rows = milvus.query(scope['chunks'], filter='', output_fields=['item_name'], limit=10, consistency_level='Strong')
        assert len(rows) == 4
        product = rows[0]['item_name']
        scheme = 'https' if os.getenv('MINIO_SECURE', '').lower() == 'true' else 'http'
        assets = bind_assets(report['objects'], f'{scheme}://{os.environ["MINIO_ENDPOINT"]}',
                             os.environ['MINIO_BUCKET_NAME'], scope['object_prefix'])
        sid = report['session_id'] if args.only else 'm0-live-resume-' + str(time.time_ns())
        report['session_id'] = sid
        q = sse_utils.create_sse_queue(sid)
        questions = [
            ('known', product + '如何验证设备与无线控制器已经连通？请说明命令和正常状态。', ['display wlan ap', 'R/M']),
            ('followup', '刚才提到的 R/M 分别表示什么？', ['Run', 'Master']),
            ('image', product + '通过什么网络连接无线控制器？请附上连接拓扑示意图。', ['3G', '4G']),
        ]
        if args.only:
            questions = [question for question in questions if question[0] == args.only]
        history_store = mongo[scope['mongo_database']]['chat_message']
        baseline_count = history_store.count_documents({'session_id': sid})
        assistant_count = history_store.count_documents({'session_id': sid, 'role': 'assistant'})
        report['history_count_before'] = baseline_count
        for kind, question, facts in questions:
            while not q.empty():
                q.get_nowait()
            started = time.perf_counter()
            print('starting=' + kind, flush=True)
            api.run_query_graph(sid, question, True)
            elapsed = round(time.perf_counter() - started, 3)
            events = list(q.queue)
            status = task_utils.get_task_status(sid)
            answer = task_utils.get_task_result(sid, 'answer')
            finals = [e for e in events if e['event'] == 'final']
            images = finals[0]['data'].get('image_urls', []) if finals else []
            checks = {'completed': status == 'completed', 'one_final': len(finals) == 1,
                      'no_error': not any(e['event'] == 'error' for e in events),
                      'expected_facts': all(f.casefold() in answer.casefold() for f in facts),
                      'assistant_saved': history_store.count_documents({'session_id': sid, 'role': 'assistant'}) == assistant_count + 1}
            if kind == 'image':
                verification = verify_image_answer(answer, finals[0]['data'].get('answer', '') if finals else '',
                                                   images, assets, expectation['sha256'], scope['object_prefix'],
                                                   http_image_fetcher(urllib3.PoolManager(timeout=10, retries=False)))
                checks.update(verification['checks'])
                report['image_verification'] = verification
            report['questions'].append({'kind': kind, 'question': question, 'status': status,
                                        'elapsed_seconds': elapsed, 'checks': checks,
                                        'answer': re.sub(r'https?://\S+', '[隔离图片对象，详见 objects]', answer),
                                        'answer_sha256': hashlib.sha256(answer.encode()).hexdigest(),
                                        'image_count': len(images), 'events': [e['event'] for e in events]})
            save()
            print(json.dumps({'kind': kind, 'status': status, 'checks': checks, 'elapsed_seconds': elapsed}, ensure_ascii=True), flush=True)
            assert all(checks.values()), '真实小样未通过，见报告'
            assistant_count += 1
        report['history_count'] = history_store.count_documents({'session_id': sid})
        assert report['history_count'] == baseline_count + 2 * len(questions)
        report['recent_history_count'] = len(get_recent_messages(sid, 10))
        report['status'] = 'passed'
        report['process_exit_code'] = 0
        save()
        return 0
    except Exception as exc:
        report['status'] = 'failed'
        report['error_type'] = type(exc).__name__
        report['process_exit_code'] = 1
        save()
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__}, ensure_ascii=True), flush=True)
        return 1
    finally:
        milvus.close()
        mongo.close()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except Exception as exc:
        # 预检失败也落盘；不打印 SDK 异常正文，避免连接串或请求体进入证据。
        output = Path(sys.argv[sys.argv.index('--output') + 1])
        report = json.loads(output.read_text(encoding='utf-8')) if output.exists() else {}
        report.update(status='failed', error_type=type(exc).__name__, process_exit_code=1,
                      failure_phase='客户端预检或初始化')
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__}))
        raise SystemExit(1)
