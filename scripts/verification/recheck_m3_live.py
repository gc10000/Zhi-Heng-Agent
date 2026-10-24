"""只读复核M3正式页面留下的隔离产物，不建索引、不调用模型。"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True, help='仅本机临时账号文件，不打印')
    parser.add_argument('--flow', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('必须新输出，禁止覆盖历史证据')
    config = json.loads(args.config.read_text(encoding='utf-8'))
    flow = json.loads(args.flow.read_text(encoding='utf-8'))
    if not config['database'].startswith('m1_test_') or not flow.get('passed'):
        parser.error('只接受已完成的隔离UI验收')
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    from pymongo import MongoClient
    from minio import Minio
    checks = {}
    with MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000) as mongo:
        db = mongo[config['database']]
        runs = [db.runs.find_one({'run_id': rid}) for rid in flow['runs']]
        checks['two_completed_answers'] = all(r['state'] == 'completed' and r['answer'] == flow['answer' + str(i)] for i, r in enumerate(runs))
        messages = list(db.messages.find({'conversation_id': runs[0]['conversation_id']}).sort('ordinal', 1))
        checks['ordered_persistent_history'] = ([m['role'] for m in messages] == ['user', 'assistant', 'user', 'assistant']
            and [messages[1]['text'], messages[3]['text']] == [r['answer'] for r in runs])
        # 实际生成入口的history接线另有M2回归；此处复核已持久跨轮语义，不伪造模型输入采样。
        checks['grounded_parameters_and_followup'] = '24' in runs[0]['answer'] and '2' in runs[0]['answer'] and '断电' in runs[1]['answer']
        checks['citations_exact_initial_revision'] = all(r['citations'] and all(c['revision_id'] == config['uploaded']['revision_id'] and c['source_refs'] for c in r['citations']) for r in runs)
        checks['single_terminal_and_ordered_events'] = True
        for run in runs:
            events = list(db.run_events.find({'run_id': run['run_id']}).sort('seq', 1))
            checks['single_terminal_and_ordered_events'] &= ([e['type'] for e in events if e['type'] in {'run.completed', 'run.failed', 'run.cancelled', 'run.interrupted'}] == ['run.completed']
                and all(a['seq'] < b['seq'] for a, b in zip(events, events[1:])))
        uploaded = flow['upload']
        job = db.import_jobs.find_one({'job_id': uploaded['job_id']})
        doc = db.knowledge_documents.find_one({'document_id': uploaded['document_id']})
        rev = db.knowledge_revisions.find_one({'revision_id': uploaded['revision_id']})
        checks['ui_import_published'] = job['state'] == 'completed' and doc['active_revision_id'] == rev['revision_id'] and rev['status'] == 'published'
        checks['ui_import_product_scope'] = config['product_ids'][0] in doc['product_ids']
        objects = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'], secret_key=os.environ['MINIO_SECRET_KEY'], secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
        checks['originals_hash_match'] = True
        for rid in [config['uploaded']['revision_id'], uploaded['revision_id']]:
            revision = db.knowledge_revisions.find_one({'revision_id': rid})
            response = objects.get_object(config['M2_OBJECT_BUCKET'], revision['object_key'])
            try:
                checks['originals_hash_match'] &= sha256(response.read()).hexdigest() == revision['original_sha256']
            finally:
                response.close(); response.release_conn()
    report = {'passed': all(checks.values()), 'mode': 'existing_m3_ui_artifacts_read_only', 'provider_calls': 0, 'checks': checks,
              'source_flow_sha256': sha256(args.flow.read_bytes()).hexdigest(), 'message_count': len(messages)}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
