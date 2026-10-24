"""冻结dev上的1/2/4会话检索资源观测；不调用答案供应商，不写语料。"""
import argparse
import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .validate_dataset import validate_dataset,file_sha,fingerprint
from .runner import percentile


def measure_wave(execute,questions,concurrency,*,resources):
    if concurrency not in (1,2,4) or len(questions)<concurrency:raise ValueError('资源测量仅允许足量的1/2/4会话')
    gate=threading.Barrier(concurrency)
    def one(q):
        gate.wait();start=time.perf_counter()
        result=execute(q)
        return dict(id=q['id'],seconds=time.perf_counter()-start,result=result)
    before=resources();start=time.perf_counter()
    with ThreadPoolExecutor(max_workers=concurrency) as pool:
        records=list(pool.map(one,questions[:concurrency]))
    duration=time.perf_counter()-start
    return dict(concurrency=concurrency,completed=len(records),failed=0,seconds=duration,
        p50_seconds=percentile([r['seconds'] for r in records],.5),
        p95_seconds=percentile([r['seconds'] for r in records],.95),
        observed_queries_per_second=len(records)/duration,before=before,after=resources(),records=records)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dataset','manifest','config','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('资源报告已存在，禁止覆盖')
    import yaml
    config=yaml.safe_load(args.config.read_text('utf-8'))
    questions=validate_dataset(args.dataset,manifest=args.manifest)
    if config.get('split')!='dev' or config.get('phase')!='development':raise ValueError('资源实验只允许dev')
    if config['dataset_sha256']!=file_sha(args.dataset) or config['split_manifest_sha256']!=file_sha(args.manifest):raise ValueError('冻结题集/划分不符')
    chosen=[q for q in questions if q['id'] in config['resource_question_ids'] and q['split']=='dev']
    if len(chosen)!=4 or len(set(config['resource_question_ids']))!=4:raise ValueError('必须预先指定4道不同dev题')
    from .readonly import open_frozen_corpus
    from .retrieval_grid import RetrievalExecutor
    from app.runs.query_runner import encode,rerank
    from app.retrieval.search import RetrievalPolicy
    from app.lm.runtime import warmup_models,ModelRuntimePolicy
    from app.lm.embedding_utils import get_bge_m3_ef
    from app.lm.reranker_utils import get_reranker_model
    import psutil,torch
    process=psutil.Process()
    def resources():
        memory=process.memory_info()
        value=dict(rss_bytes=memory.rss,peak_rss_bytes=getattr(memory,'peak_wset',None),
            cpu_seconds=sum(process.cpu_times()[:2]),system_available_bytes=psutil.virtual_memory().available)
        if torch.cuda.is_available():
            value.update(gpu_allocated_bytes=torch.cuda.memory_allocated(),gpu_reserved_bytes=torch.cuda.memory_reserved(),
                gpu_peak_allocated_bytes=torch.cuda.max_memory_allocated(),gpu_peak_reserved_bytes=torch.cuda.max_memory_reserved(),
                gpu_total_bytes=torch.cuda.get_device_properties(0).total_memory)
        return value
    report=dict(notice='真实本机模型/隔离索引，仅检索；每档一次观测不是稳定吞吐或生产容量。编码缓存每档清空、权重预热复用，答案/付费/heldout0。',
        config_sha256=fingerprint(config),versions=config['versions'],runtime_policy=ModelRuntimePolicy.load().model_dump(),
        paid_calls=0,heldout_executed=0,waves=[])
    with open_frozen_corpus(config) as gateway:
        report['corpus_before_sha256']=gateway.corpus_sha256
        started=time.perf_counter();warmup_models();report['cold_load_warmup_seconds']=time.perf_counter()-started
        execute=RetrievalExecutor(config,gateway,embedder=encode,ranker=rerank)
        models=set()
        def run(q):
            result=execute.execute(q,RetrievalPolicy.model_validate(config['parameters']))
            models.add((id(get_bge_m3_ef()),id(get_reranker_model())))
            return dict(route=result['route'],stage_counts=result['stage_counts'],stage_timings=result['stage_timings'])
        for concurrency in (1,2,4):
            execute.embeddings.clear()
            if torch.cuda.is_available():torch.cuda.reset_peak_memory_stats()
            report['waves'].append(measure_wave(run,chosen,concurrency,resources=resources))
        report['distinct_model_pairs']=len(models)
        report['corpus_after_sha256']=gateway.verify()
        report['corpus_unchanged']=report['corpus_before_sha256']==report['corpus_after_sha256']
    report['passed']=report['corpus_unchanged'] and report['distinct_model_pairs']==1 and all(w['completed']==w['concurrency'] for w in report['waves'])
    with args.output.open('x',encoding='utf-8') as stream:json.dump(report,stream,ensure_ascii=False,indent=2,allow_nan=False)
    print(json.dumps(dict(passed=report['passed'],concurrency=[w['concurrency'] for w in report['waves']],paid_calls=0)))


if __name__=='__main__':main()
