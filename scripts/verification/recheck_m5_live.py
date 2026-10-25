"""只读核对M5真实新进程产物、导出、来源与原隔离数据不变，不调用模型。"""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--flow', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    if args.report.exists():
        parser.error('须新报告，不能覆盖原始证据')
    config = json.loads(args.config.read_text('utf-8'))
    flow = json.loads(args.flow.read_text('utf-8'))
    if not config['database'].startswith('m1_test_m5_live_') or not flow['passed']:
        parser.error('只接受已完成的独立M5真实流程')
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    from pymongo import MongoClient
    from pymilvus import MilvusClient
    from app.knowledge.index import V2Index
    from app.knowledge.repository import KnowledgeRepository
    from app.support.export import export_markdown
    from scripts.verification.m5_environment import digest
    checks = {}
    with MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000) as mongo:
        db, source = mongo[config['database']], mongo[config['source_database']]
        checks['source_mongo_unchanged'] = all(digest(list(source[name].find(item['query']))) == item['sha256'] for name, item in config['source_snapshots'].items())
        source_runs = list(source.runs.find({'run_id': {'$in': config['source_runs']}}))
        checks['historical_supplier_artifacts_preserved'] = all(db.runs.find_one({'run_id':r['run_id']})['answer'] == r['answer'] for r in source_runs)
        support = db.conversations.find_one({'conversation_id': config['conversation_id']})['support']
        checks['persistent_handoff_not_resolved'] = support['state'] == 'handoff' and support['reason'] == 'all_steps_ineffective'
        checks['reports_user_sourced_append_only'] = bool(support['operations']) and all(
            operation['status'] == 'ineffective' and operation['reports'] and all(r['source']=='user_report' and r['recorded_at'] for r in operation['reports']) for operation in support['operations'])
        run = db.runs.find_one({'run_id': flow['new_runs'][-1]})
        checks['new_formal_run_completed_with_exact_answer'] = run['state']=='completed' and run['answer']==flow['answer'] and bool(run.get('prompt_budget'))
        checks['future_run_frozen_user_results'] = run['support_snapshot']['context_version']==support['context_version'] and all(step['status']=='ineffective' for step in run['support_snapshot']['operations'])
        checks['one_completed_new_query_two_setup_failures_preserved'] = len(flow['new_runs'])==3 and len(flow['setup_failed_runs'])==2 and all(
            (r:=db.runs.find_one({'run_id':rid}))['state']=='failed' and r['error']['stage']=='product' and not r.get('prompt_budget') for rid in flow['setup_failed_runs'])
        messages = list(db.messages.find({'conversation_id':config['conversation_id']}).sort('ordinal',1))
        checks['new_answer_message_and_citations_exact'] = all(
            message['text']==run['answer'] and message['citations']==run['citations'] for message in messages if message['run_id']==run['run_id'] and message['role']=='assistant') and len([m for m in messages if m['run_id']==run['run_id']])==2
        events = list(db.run_events.find({'run_id':run['run_id']}).sort('seq',1))
        checks['unique_terminal_and_stream_answer'] = [e['type'] for e in events if e['type'] in {'run.completed','run.failed','run.cancelled','run.interrupted'}]==['run.completed'] and ''.join(e['payload']['text'] for e in events if e['type']=='answer.delta')==run['answer']
        case = db.support_cases.find_one({'case_id':flow['case_id']})
        checks['confirmation_and_user_edits_preserved'] = case['status']=='confirmed' and case['confirmed_at'] is not None and case['edits'][-1]['source']=='user_edit' and '未知' in case['fields']['summary']
        checks['case_has_original_operations_and_unknown_fields'] = case['operations']==support['operations'] and case['fields']['environment']=='未知' and case['fields']['error_code']=='未知'
        exported_path = args.flow.with_suffix('.export.md')
        checks['download_exact_authorized_confirmed_snapshot'] = exported_path.read_text('utf-8')==export_markdown(case)['markdown']
        feedback = db.support_feedback.find_one({'feedback_id':flow['feedback_id']})
        checks['feedback_pending_and_run_bound'] = feedback['state']=='pending_review' and feedback['run_id']==run['run_id'] and feedback['category']=='operation'
        checks['draft_does_not_publish_knowledge'] = digest(list(db.knowledge_documents.find({})))==config['source_snapshots']['knowledge_documents']['sha256']
        scope = config['source_scope']
        milvus = MilvusClient(uri=os.environ['MILVUS_URL'])
        try:
            index = V2Index(milvus,scope['M2_MILVUS_COLLECTION'])
            repo = KnowledgeRepository(db,owner_id=scope['M2_KNOWLEDGE_OWNER_ID'],kb_id=config['kb_id'])
            indexed = {}
            for revision_id in {c['revision_id'] for c in case['citations']}:
                for row in index.revision_rows(repo, revision_id):
                    indexed[(row['document_id'],row['revision_id'],row['chunk_uid'])] = row
            checks['case_citations_match_real_index_and_sources'] = all(
                (row:=indexed.get((c['document_id'],c['revision_id'],c['chunk_uid']))) and row['text']==c['text'] and row['metadata']['source_refs']==c['source_refs'] for c in case['citations'])
        finally:
            milvus.close()
    # 原件真实HTTP路径：不输出Cookie/URL/配置值；仅核对字节hash。
    import requests
    with requests.Session() as http:
        http.trust_env=False
        response=http.post(config['base_url']+'/api/v1/auth/login',headers={'Origin':config['frontend_url']},json={'username':config['username'],'password':config['password']},timeout=10)
        response.raise_for_status()
        citation=run['citations'][0]
        response=http.get(config['base_url']+'/api/v1/runs/'+run['run_id']+'/citations/'+citation['citation_id'],timeout=10)
        response.raise_for_status(); descriptor=response.json()['original']
        response=http.get(config['base_url']+descriptor['url'],timeout=15);response.raise_for_status()
        with MongoClient(os.environ['MONGO_URL']) as mongo:
            revision=mongo[config['database']].knowledge_revisions.find_one({'revision_id':citation['revision_id']})
        checks['original_real_http_sha256'] = sha256(response.content).hexdigest()==revision['original_sha256']
    report={'passed':all(checks.values()),'mode':'real_m5_api_browser_artifacts_read_only','checks':checks,
        'new_formal_queries':len(flow['new_runs']),'setup_failed_before_retrieval':len(flow['setup_failed_runs']),
        'logical_answer_generations':1,'exact_sdk_http_calls':None,'exact_cost':None,'recheck_provider_calls':0,
        'human_quality_rating':None,'assistant_sample_review':'本次新答案明确承认用户已报无效步骤，未再次作为新操作建议，明确资料不足并转交；仅此样例，不是整体正确率。',
        'raw_evidence':[{'path':p.relative_to(ROOT).as_posix(),'sha256':sha256(p.read_bytes()).hexdigest()} for p in (args.config.resolve(),args.flow.resolve(),exported_path.resolve())]}
    args.report.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'passed':report['passed'],'checks':checks,'logical_answer_generations':1,'recheck_provider_calls':0}))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
