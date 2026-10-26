"""只读复核显式M6隔离小样、正式运行及人工待审状态；不执行模型或代填评分。"""
import argparse
import json
import os
from pathlib import Path
import traceback


ROOT = Path(__file__).resolve().parents[2]


def verify(session_path, identity_path):
    from pymongo import MongoClient
    import requests
    from app.evaluation.readonly import open_frozen_corpus
    from app.evaluation.validate_dataset import file_sha, fingerprint, validate_dataset
    from app.evaluation.runner import select_questions, reproducibility_metadata
    from scripts.verification.m5_environment import digest

    session = json.loads(session_path.read_text('utf-8'))
    identity = json.loads(identity_path.read_text('utf-8'))
    if (not session['target']['database'].startswith('m1_test_m4_m6_review_') or
            not session['source_database'].startswith('m1_test_m4_')):
        raise ValueError('仅接受独立M6审阅目标及M4隔离来源')
    directory = Path(session['catalog']).parent
    config_path, dataset, split = directory/'control.json', directory/'support-v2-r2.jsonl', directory/'support-v2-r2-manifest.json'
    config = json.loads(config_path.read_text('utf-8'))
    if config['target'] != session['target'] or file_sha(config_path) != session['config_sha256']:
        raise ValueError('本机审阅目标或配置指纹改变')
    rows = select_questions(validate_dataset(dataset, manifest=split), config)
    eid = identity['experiment_id']
    output = Path(session['work_dir'])/eid
    if (output/'.runner.lock').exists():
        raise ValueError('实验仍有执行占用，不生成完成报告')
    manifest_path = output/'manifest.json'
    manifest = json.loads(manifest_path.read_text('utf-8'))
    records = [json.loads(line) for line in (output/'results.jsonl').read_text('utf-8').splitlines()]
    attempts = [json.loads(line) for line in (output/'attempts.jsonl').read_text('utf-8').splitlines()]
    checks = {}
    checks['frozen_dev_subset_and_config'] = (config['split'] == 'dev' and config['phase'] == 'development' and
        manifest['config'] == config and manifest['config_sha256'] == fingerprint(config) and
        manifest['selected_ids'] == [q['id'] for q in rows] == session['selected_ids'] and
        [r['id'] for r in records] == session['selected_ids'])
    expected = reproducibility_metadata(config, dataset_sha256=file_sha(dataset),
        split_manifest_sha256=file_sha(split), config_sha256=fingerprint(config))
    checks['reproducibility_identity'] = (manifest.get('reproducibility') == expected and
        manifest.get('reproducibility_sha256') == fingerprint(expected))
    latest = {r['id']: r for r in attempts}
    checks['completed_attempts_and_results_exact'] = (manifest['status'] == 'completed' and manifest['failed'] == 0 and
        latest == {r['id']: r for r in records} and all(r['status'] == 'completed' for r in records))
    actual_sources, conversation_links, run_ids = set(), [], []
    http_originals = http_images = 0
    with open_frozen_corpus(config) as gateway:
        checks['actual_original_vectors_assets_products_unchanged'] = gateway.verify() == session['source_corpus_sha256']
        with MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000, tz_aware=True) as mongo:
            db, source = mongo[session['target']['database']], mongo[session['source_database']]
            checks['source_mongo_unchanged'] = all(digest(list(source[name].find(item['query']))) == item['sha256']
                for name, item in session['source_snapshots'].items())
            experiment = db.evaluation_experiments.find_one({'experiment_id': eid})
            checks['linux_attempt_and_published_result_pointer'] = (experiment['state'] == 'completed' and
                experiment['attempt'] == experiment['result_attempt'] == 1 and experiment['selected_questions'] == len(rows))
            slot = db.evaluation_slots.find_one({'_id': experiment['owner_id']})
            checks['own_budget_released'] = slot is not None and slot['active_experiment_id'] is None
            stored_results = {r['question_id']: r for r in db.evaluation_results.find({
                'experiment_id': eid, 'attempt': experiment['result_attempt']})}
            messages_ok, terminal_ok, results_ok, telemetry_ok = True, True, True, True
            with requests.Session() as http:
                http.trust_env = False
                base, origin = identity['base_url'], session['frontend_url']
                login = http.post(base+'/api/v1/auth/login', headers={'Origin': origin},
                    json={'username': session['username'], 'password': session['password']}, timeout=10)
                login.raise_for_status()
                page = http.get(base+'/api/v1/experiments/'+eid+'/results', timeout=10)
                page.raise_for_status()
                checks['real_api_question_results'] = {r['question_id']: r['result'] for r in page.json()['items']} == {
                    qid: r['result'] for qid, r in stored_results.items()}
                for question, record in zip(rows, records):
                    result = record['result']
                    run = db.runs.find_one({'run_id': result['run_id'], 'owner_id': experiment['owner_id']})
                    if run is None:
                        raise ValueError('缺少正式运行，不能以本机结果冒称真实链路')
                    run_ids.append(run['run_id'])
                    conversation_links.append({'question_id': question['id'],
                        'url': origin+'/chat/'+run['conversation_id']})
                    clean = stored_results[question['id']]
                    results_ok &= (run['state'] == result['state'] and run['state'] in {'completed', 'awaiting_input'} and run.get('answer', '') == result['answer'] and
                        run['question'] == question['question'] and clean['result']['answer'] == result['answer'] and
                        clean['metrics'] == record['metrics'])
                    messages = list(db.messages.find({'conversation_id': run['conversation_id']}).sort('ordinal', 1))
                    expected_messages = question['history'] + [{'role': 'user', 'text': question['question']}]
                    if run['state'] == 'completed':
                        expected_messages.append({'role': 'assistant', 'text': run['answer']})
                    messages_ok &= ([{'role': m['role'], 'text': m['text']} for m in messages] == expected_messages)
                    terminal = list(db.run_events.find({'run_id': run['run_id'], 'type': {'$in': [
                        'run.completed', 'run.failed', 'run.interrupted', 'run.cancelled']}}))
                    terminal_ok &= (len(terminal) == 1 and terminal[0]['type'] == 'run.completed') if run['state'] == 'completed' else (
                        not terminal and db.run_events.count_documents({'run_id': run['run_id'], 'type': 'product.candidates'}) == 1)
                    telemetry = http.get(base+'/api/v1/runs/'+run['run_id']+'/telemetry', timeout=10)
                    telemetry.raise_for_status()
                    telemetry_ok &= telemetry.json()['timing_coverage'] == 'persistent'
                    if run['state'] == 'completed':
                        telemetry_ok &= (telemetry.json()['stage_seconds'] == result['stage_timings'] and
                            telemetry.json()['token_usage'] == result['token_usage'])
                    else:
                        telemetry_ok &= telemetry.json()['total_seconds'] is None and result['behavior'] == 'clarify'
                    normalized = set()
                    for citation in run['citations']:
                        indexed = gateway.index().revision_rows(gateway.repo(config['target']['kb_id']), citation['revision_id'])
                        hit = next(r for r in indexed if r['chunk_uid'] == citation['chunk_uid'])
                        if citation['text'] != hit['text'] or citation['source_refs'] != hit['metadata']['source_refs']:
                            raise ValueError('持久引用与真实索引正文/来源不一致')
                        descriptor = http.get(base+'/api/v1/runs/'+run['run_id']+'/citations/'+citation['citation_id'], timeout=10)
                        descriptor.raise_for_status()
                        original = descriptor.json()['original']
                        if original['asset_id'] not in actual_sources:
                            response = http.get(base+original['url'], timeout=30)
                            response.raise_for_status()
                            from hashlib import sha256
                            revision = gateway.repo(config['target']['kb_id']).get_revision(citation['revision_id'])
                            if sha256(response.content).hexdigest() != revision['original_sha256']:
                                raise ValueError('真实HTTP原件hash不符')
                            actual_sources.add(original['asset_id']); http_originals += 1
                        doc = next(d for d in config['corpus']['documents'] if d['document_id'] == citation['document_id'])
                        normalized.update((doc['original_sha256'], ref['page'], None) for ref in citation['source_refs'] if ref.get('page'))
                        for aid, url in descriptor.json()['asset_urls'].items():
                            asset = db.knowledge_assets.find_one({'asset_id': aid, 'revision_id': citation['revision_id']})
                            normalized.update((doc['original_sha256'], ref['page'], asset['sha256']) for ref in asset['source_refs'] if ref.get('page'))
                            if aid not in actual_sources:
                                response = http.get(base+url, timeout=30); response.raise_for_status()
                                if sha256(response.content).hexdigest() != asset['sha256']:
                                    raise ValueError('真实HTTP配图hash不符')
                                from io import BytesIO
                                from PIL import Image
                                with Image.open(BytesIO(response.content)) as image: image.verify()
                                with Image.open(BytesIO(response.content)) as image: image.load()
                                actual_sources.add(aid); http_images += 1
                    results_ok &= normalized == {(r['document_sha256'], r['page'], r.get('asset_sha256')) for r in result['citations']}
                checks.update(formal_run_results_and_index_sources=results_ok, persistent_messages_exact=messages_ok,
                    unique_completed_or_clarification_event=terminal_ok, real_telemetry_matches_question_results=telemetry_ok,
                    http_original_hashes=http_originals > 0, http_image_hashes_full_decode=http_images > 0)
                reviews = http.get(base+'/api/v1/experiments/'+eid+'/reviews', timeout=10)
                reviews.raise_for_status()
                human_count = sum(r['reviewer_kind'] == 'human' for r in reviews.json()['items'])
                checks['real_review_subjects_bound'] = {s['question_id'] for s in reviews.json()['subjects']} == set(stored_results)
            human_calibrations = db.evaluation_calibrations.count_documents({'experiment_id': eid})
    raw_paths = [session_path, identity_path, config_path, dataset, split] + sorted(p for p in output.rglob('*') if p.is_file())
    return {'passed': all(checks.values()), 'mode': 'real_m6_fixed_dev_baseline_read_only', 'checks': checks,
        'questions': len(rows), 'run_ids': run_ids, 'conversation_links': conversation_links,
        'logical_provider_calls': {key: sum(r['result'].get('logical_provider_calls', {}).get(key, 0) for r in records)
            for key in ('invoke_started', 'stream_started')},
        'read_only_recheck_model_calls': 0, 'exact_sdk_http_calls': None, 'exact_cost': None,
        'human_review_records': human_count, 'human_calibrations': human_calibrations,
        'human_quality_passed': None, 'heldout_runs': 0,
        'http_originals': http_originals, 'http_images_fully_decoded': http_images,
        'scope_notice': '仅固定开发题小样与技术关联复核；不代表人工质量通过、全开发集回归、反馈闭环或阶段验收。',
        'raw_evidence': [{'path': p.relative_to(ROOT).as_posix(), 'sha256': file_sha(p)} for p in raw_paths]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session', type=Path, required=True)
    parser.add_argument('--identity', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    for path in (args.session, args.identity, args.report):
        if not path.resolve().is_relative_to(ROOT/'output'):
            parser.error('本机私有会话、身份和报告须位于output内')
    if args.report.exists():
        parser.error('须选择新报告，保留原始证据')
    from dotenv import load_dotenv
    load_dotenv(ROOT/'.env')
    os.environ.update(MODEL_HOST_URL='', MODEL_HOST_TOKEN='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
                      LOG_CONSOLE_ENABLE='False', LOG_FILE_ENABLE='False')
    try:
        report = verify(args.session.resolve(), args.identity.resolve())
    except Exception as exc:
        report = {'passed': False, 'error_type': type(exc).__name__, 'locations': [
            {'file': Path(f.filename).name, 'line': f.lineno} for f in traceback.extract_tb(exc.__traceback__)]}
    with args.report.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    print(json.dumps({k: v for k, v in report.items() if k not in {'raw_evidence', 'run_ids', 'conversation_links'}}, ensure_ascii=False))
    return 0 if report['passed'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
