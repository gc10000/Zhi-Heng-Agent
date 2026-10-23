"""全新进程使用正常模型/线程配置验证真实查询，仅覆盖隔离数据与日志/离线下载保护。"""
import argparse
import contextlib
import faulthandler
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import time
import traceback

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), '必须使用新输出路径保留证据'
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    source = json.loads(args.source.read_text(encoding='utf-8'))
    scope = source['scope']
    assert all(scope[key].startswith('m0_test_') for key in ('mongo_database', 'chunks', 'items'))
    assert scope['object_prefix'].startswith('m0-test/')
    report = {'status': 'running', 'pid': os.getpid(), 'scope': scope,
              'source_report': str(args.source), 'normal_configuration': True,
              'prewarm_reranker': False, 'thread_overrides': {}, 'fake': False,
              'command': ['.venv/Scripts/python.exe', *sys.argv],
              'thread_environment': {key: os.getenv(key) for key in ('OMP_NUM_THREADS', 'MKL_NUM_THREADS', 'OPENBLAS_NUM_THREADS')}}
    os.environ.update(CHUNKS_COLLECTION=scope['chunks'], ITEM_NAME_COLLECTION=scope['items'],
                      MONGO_DB_NAME=scope['mongo_database'], LOG_CONSOLE_ENABLE='False', LOG_FILE_ENABLE='False',
                      HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    def save():
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    save()
    faulthandler.enable()
    from pymongo import MongoClient
    mongo = MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000)
    try:
        import torch
        report['torch_threads'] = {'intraop': torch.get_num_threads(), 'interop': torch.get_num_interop_threads()}
        from app.core.logger import logger
        def stage(message):
            record = message.record
            report['last_stage'] = f"{record['name']}:{record['function']}:{record['line']}"
            save()
        logger.add(stage, level='INFO')
        from app.query_process.api import query_service as api
        from app.utils import task_utils, sse_utils
        from app.lm import embedding_utils, reranker_utils
        assert embedding_utils._bge_m3_ef is None and reranker_utils._reranker_model is None
        report['models_initially_unloaded'] = True
        graph = api.get_query_app()
        class DiagnosticGraph:
            def invoke(self, state):
                try:
                    result = graph.invoke(state)
                    report['used_chunk_ids'] = result.get('used_chunk_ids', [])
                    return result
                except Exception as exc:
                    chain = []
                    current = exc
                    while current is not None:
                        chain.append({'type': type(current).__name__, 'http_status': getattr(current, 'status_code', None),
                                      'frames': [{'file': Path(f.filename).name, 'function': f.name, 'line': f.lineno}
                                                 for f in traceback.extract_tb(current.__traceback__)]})
                        current = current.__cause__
                    report['graph_exception_chain'] = chain
                    save()
                    raise
        api.query_app = DiagnosticGraph()
        sid = 'm0-cold-' + str(time.time_ns())
        report['session_id'] = sid
        question = 'H3CLA2608室内无线网关如何验证设备与无线控制器已经连通？请说明命令和正常状态。'
        queue = sse_utils.create_sse_queue(sid)
        history = mongo[scope['mongo_database']]['chat_message']
        assert history.count_documents({'session_id': sid}) == 0
        started = time.perf_counter()
        # 不保存旧节点 print 内容；图/模型/仓储均实际调用，不替换结果。
        with contextlib.redirect_stdout(io.StringIO()):
            api.run_query_graph(sid, question, True)
        report['elapsed_seconds'] = round(time.perf_counter() - started, 3)
        events = list(queue.queue)
        answer = task_utils.get_task_result(sid, 'answer')
        report['assistant_saved_count'] = history.count_documents({'session_id': sid, 'role': 'assistant'})
        report['history_count'] = history.count_documents({'session_id': sid})
        report['events'] = [event['event'] for event in events]
        report['answer_sha256'] = hashlib.sha256(answer.encode()).hexdigest()
        report['models_loaded'] = {'embedding': embedding_utils._bge_m3_ef is not None,
                                   'reranker': reranker_utils._reranker_model is not None}
        report['devices'] = {'embedding_configured': os.getenv('BGE_DEVICE'),
                             'reranker_configured': os.getenv('BGE_RERANKER_DEVICE'),
                             'reranker_actual': getattr(reranker_utils._reranker_model, 'target_devices', None)}
        finals = [event for event in events if event['event'] == 'final']
        checks = {'completed': task_utils.get_task_status(sid) == 'completed', 'one_final': len(finals) == 1,
                  'no_error': not any(event['event'] == 'error' for event in events),
                  'assistant_saved_once': report['assistant_saved_count'] == 1, 'history_saved_twice': report['history_count'] == 2,
                  'expected_facts': all(f.casefold() in answer.casefold() for f in ('display wlan ap', 'R/M')),
                  'models_loaded': all(report['models_loaded'].values()),
                  'final_answer_equal': len(finals) == 1 and finals[0]['data']['answer'] == answer,
                  'used_real_evidence': bool(report.get('used_chunk_ids'))}
        report['checks'] = checks
        assert all(checks.values()), '正常冷启动验收未通过'
        report.update(status='passed', process_exit_code=0)
        save()
        print(json.dumps({'status': 'passed', 'checks': checks, 'elapsed_seconds': report['elapsed_seconds']}))
        return 0
    except Exception as exc:
        report.update(status='failed', process_exit_code=1, error_type=type(exc).__name__)
        save()
        print(json.dumps({'status': 'failed', 'error_type': type(exc).__name__}))
        return 1
    finally:
        mongo.close()


if __name__ == '__main__':
    raise SystemExit(main())
