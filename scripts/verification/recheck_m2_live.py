"""只读复核已有M2真实API产物，不创建客户端索引、不调用模型。"""
import argparse
import json
import os
from pathlib import Path
from hashlib import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bucket', help='原报告对应桶；未指定时使用MINIO_BUCKET_NAME')
    args = parser.parse_args()
    if args.output.exists():
        parser.error('保留旧报告，请选择不存在的新输出路径')
    source = json.loads(args.report.read_text(encoding='utf-8'))
    if not source['passed'] or not source['database'].startswith('m1_test_'):
        parser.error('只接受已通过的隔离真实报告')
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parents[2] / '.env')
    from pymongo import MongoClient
    from minio import Minio
    checks = {}
    with MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000) as client:
        db = client[source['database']]
        run = db.runs.find_one({'run_id': source['run_id']})
        job = db.import_jobs.find_one({'job_id': source['job_id']})
        document = db.knowledge_documents.find_one({'document_id': source['document_id']})
        revision = db.knowledge_revisions.find_one({'revision_id': source['revision_id']})
        checks['run_completed'] = run['state'] == 'completed'
        checks['answer_hash'] = sha256(run['answer'].encode()).hexdigest() == source['answer_sha256']
        checks['job_completed'] = job['state'] == 'completed'
        checks['revision_active'] = document['active_revision_id'] == source['revision_id']
        checks['revision_published'] = revision['status'] == 'published'
        asset = db.original_assets.find_one({'revision_id': source['revision_id']})
        if asset is None:
            asset = db.knowledge_original_assets.find_one({'revision_id': source['revision_id']})
        objects = Minio(os.environ['MINIO_ENDPOINT'], access_key=os.environ['MINIO_ACCESS_KEY'],
            secret_key=os.environ['MINIO_SECRET_KEY'], secure=os.getenv('MINIO_SECURE', '').lower() == 'true')
        response = objects.get_object(args.bucket or asset.get('bucket') or os.environ['MINIO_BUCKET_NAME'], revision['object_key'])
        try:
            checks['original_hash'] = sha256(response.read()).hexdigest() == revision['original_sha256']
        finally:
            response.close()
            response.release_conn()
        messages = list(db.messages.find({'run_id': run['run_id']}).sort('ordinal', 1))
        checks['message_snapshot'] = (len(messages) == 2 and [m['role'] for m in messages] == ['user', 'assistant']
            and messages[1]['text'] == run['answer'] and messages[1]['citations'] == run['citations'])
        checks['citations_sources'] = bool(run['citations']) and all(c['revision_id'] == revision['revision_id']
            and c['document_id'] == document['document_id'] and c['source_refs'] for c in run['citations'])
        events = list(db.run_events.find({'run_id': run['run_id']}).sort('seq', 1))
        checks['single_terminal'] = [e['type'] for e in events if e['type'] in {'run.completed', 'run.failed', 'run.cancelled', 'run.interrupted'}] == ['run.completed']
        checks['delta_snapshot_equal'] = ''.join(e['payload']['text'] for e in events if e['type'] == 'answer.delta') == run['answer']
        checks['event_order'] = bool(events) and [e['type'] for e in events] == source['event_types'] and all(a['seq'] < b['seq'] for a, b in zip(events, events[1:]))
    report = {'passed': all(checks.values()), 'mode': 'existing_live_artifacts_read_only', 'provider_calls': 0,
        'checks': checks, 'source_report_sha256': sha256(args.report.read_bytes()).hexdigest(), 'event_count': len(events)}
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
