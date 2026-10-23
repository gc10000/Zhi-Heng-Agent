"""只读复核已成功生成但验收器拒绝的图片响应；不再次调用模型或新增历史消息。"""
import argparse
import copy
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.verification.image_acceptance import bind_assets, verify_image_answer, http_image_fetcher


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
    report = json.loads(args.source.read_text(encoding='utf-8'))
    # 区分原图调用的验收失败与本次只读复核结果，保留两次命令的真实退出码。
    report['source_process_result'] = {key: report.get(key) for key in ('status', 'process_exit_code', 'error_type')}
    report.pop('error_type', None)
    scope = report['scope']
    assert scope['mongo_database'].startswith('m0_test_') and scope['object_prefix'].startswith('m0-test/')
    image = next(q for q in report['questions'] if q['kind'] == 'image')
    assert image['status'] == 'completed'
    assert all(value for key, value in image['checks'].items() if key != 'downloads_verified')
    assert image['checks']['body_final_text_equal'] and image['events'].count('final') == 1
    assert 'error' not in image['events']
    report.setdefault('previous_attempts', []).append(copy.deepcopy(image))
    from pymongo import MongoClient
    import urllib3
    mongo = MongoClient(os.environ['MONGO_URL'], serverSelectionTimeoutMS=5000)
    def save():
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    try:
        history = mongo[scope['mongo_database']]['chat_message']
        query = {'session_id': report['session_id']}
        count_before = history.count_documents(query)
        # 原响应正文没有落URL明文证据；从真实隔离历史匹配原response hash，绝不猜测文本。
        matches = [row for row in history.find({**query, 'role': 'assistant'})
                   if hashlib.sha256(row['text'].encode()).hexdigest() == image['answer_sha256']]
        assert len(matches) == 1, '必须唯一对应原完成响应'
        saved = matches[0]
        scheme = 'https' if os.getenv('MINIO_SECURE', '').lower() == 'true' else 'http'
        assets = bind_assets(report['objects'], f'{scheme}://{os.environ["MINIO_ENDPOINT"]}', os.environ['MINIO_BUCKET_NAME'], scope['object_prefix'])
        final_keys = {obj['key'] for obj in report['image_verification']['objects']}
        # 原检查下载集合是正文/final并集，正文为final子集，故并集就是实际final集合。
        # 明确与真实持久化图片列表核对，不把重建的事件冒充新final。
        expected_urls = {asset['origin'] + '/' + asset['bucket'] + '/' + asset['key'] for asset in assets if asset['key'] in final_keys}
        assert set(saved['image_urls']) == expected_urls and len(expected_urls) == image['image_count']
        verification = verify_image_answer(saved['text'], saved['text'], saved['image_urls'], assets,
                                           report['image_expectation']['sha256'], scope['object_prefix'],
                                           http_image_fetcher(urllib3.PoolManager(timeout=10, retries=False)))
        report['image_verification'] = verification
        image['checks'].update(verification['checks'])
        report['image_recheck'] = {'source_response_report': str(args.source), 'read_only': True,
                                   'provider_calls': 0, 'history_writes': 0,
                                   'matched_response_hash': image['answer_sha256'], 'matching_assistant_messages': len(matches),
                                   'final_evidence': '沿用原真实响应唯一final/正文相等/图集合检查，无新造final',
                                   'persisted_images_match_original_final': True}
        report['history_count'] = history.count_documents(query)
        assert report['history_count'] == count_before == report['history_count_before'] + 2
        assert all(image['checks'].values()), '图片复核失败'
        report.update(status='passed', process_exit_code=0, rechecked_from=str(args.source))
        save()
        print(json.dumps({'status': 'passed', 'provider_calls': 0, 'history_writes': 0, 'image_checks': image['checks']}))
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
