"""对冻结检索结果作独立只读分析，不重跑模型、不覆盖原实验报告。"""
import argparse
import copy
import json
from pathlib import Path
from .retrieval_grid import validate_grid, summarize_recall
from .runner import percentile
from .validate_dataset import file_sha, fingerprint


def analyze(source, dataset, manifest):
    source = Path(source)
    if (source / '.runner.lock').exists(): raise ValueError('实验仍占用，结束后才能生成最终分析')
    config_path = source / 'grid-config.json'
    config = json.loads(config_path.read_text('utf-8'))
    questions = validate_grid(config, dataset, manifest)
    ids = {q['id'] for q in questions}
    original = json.loads((source / 'grid-summary.json').read_text('utf-8'))
    if original['config_sha256'] != fingerprint(config): raise ValueError('原汇总配置不符')
    files = [Path(dataset), Path(manifest), config_path, source/'grid-summary.json']
    reports = []
    for variant in config['grid']:
        folder = source / variant['id']
        if (folder / '.runner.lock').exists(): raise ValueError('子实验仍占用')
        report_path, result_path, attempts_path = [folder/name for name in ('manifest.json','results.jsonl','attempts.jsonl')]
        saved = json.loads(report_path.read_text('utf-8'))
        per = copy.deepcopy(config); per.pop('grid')
        per.update(experiment_id=config['experiment_id']+'-'+variant['id'], parameters=variant['policy'])
        if saved['config'] != per or saved['config_sha256'] != fingerprint(per) or saved['split_manifest_sha256'] != file_sha(manifest):
            raise ValueError('子实验未绑定冻结配置')
        records = [json.loads(line) for line in result_path.read_text('utf-8').splitlines()]
        if len(records) != len(ids) or {r['id'] for r in records} != ids: raise ValueError('结果缺题或重复')
        latest = {}
        for line in attempts_path.read_text('utf-8').splitlines():
            row = json.loads(line)
            if row['id'] not in ids or row['config_sha256'] != fingerprint(per): raise ValueError('尝试身份/配置不符')
            latest[row['id']] = row
        if latest != {r['id']:r for r in records}: raise ValueError('结果与已提交尝试不符')
        completed = [r for r in records if r['status']=='completed']
        if saved.get('completed') != len(completed) or saved.get('failed') != len(records)-len(completed):
            raise ValueError('最终状态计数不符')
        timings = [r['result']['stage_timings']['estimated_pipeline_seconds'] for r in completed if r['result']['stage_timings']]
        categories = {}
        for category in sorted({q['category'] for q in questions}):
            subset = [q for q in questions if q['category']==category]
            categories[category] = dict(questions=len(subset), recall=summarize_recall(records,subset))
        reports.append(dict(id=variant['id'], policy=variant['policy'], selected=len(records), completed=len(completed),
            failed=len(records)-len(completed), recall=summarize_recall(records,questions), by_category=categories,
            clarified_ids=[r['id'] for r in completed if r['result']['route']=='clarify'],
            behavior_matches=sum(r['metrics']['behavior_matches'] for r in completed),
            p50_pipeline_seconds=percentile(timings,.5),p95_pipeline_seconds=percentile(timings,.95),
            timed_questions=len(timings),
            max_observed_rss_bytes=max((r['result'].get('resources',{}).get('rss_after_bytes',0) for r in completed),default=0),
            max_gpu_allocated_bytes=max((r['result'].get('resources',{}).get('gpu_allocated_bytes',0) for r in completed),default=0)))
        files.extend([report_path,result_path,attempts_path])
    if len(original['variants']) != len(reports): raise ValueError('网格尚未全部结束')
    return dict(notice='独立修正分析：所有要求证据的dev题入分母，错误澄清/失败计0，无证据要求才排除。保留原汇总，不重跑检索。来源覆盖不是答案正确率；时延排除澄清且含共享编码，非隔离性能基准。',
        selected_dev=len(questions),heldout_executed=0,paid_calls=0,config_sha256=fingerprint(config),variants=reports,
        raw_evidence=[dict(path=p.as_posix(),sha256=file_sha(p)) for p in files])


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','dataset','manifest','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=analyze(args.source,args.dataset,args.manifest)
    # 原件/已有分析一律不覆盖；写入前已经完成所有读取与核对。
    with args.output.open('x',encoding='utf-8') as stream:json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps(dict(variants=len(result['variants']),heldout_executed=0,paid_calls=0)))


if __name__=='__main__':main()
