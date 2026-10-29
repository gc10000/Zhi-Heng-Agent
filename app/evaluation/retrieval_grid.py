"""固定dev检索网格；真实本机模型/索引，只读语料，不调用答案供应商。"""
import argparse
import copy
import json
from pathlib import Path
import time
from .runner import atomic_json, run_experiment, percentile, evidence_metrics, output_lock, check_split
from .validate_dataset import file_sha, fingerprint, validate_dataset
from app.retrieval.search import RetrievalPolicy, retrieve
from app.retrieval.adapters import from_index_hits
from app.retrieval.rerank import rank_hits
from app.retrieval.query_planner import plan_query
from app.retrieval.models import EvidencePack


def validate_grid(config, dataset, manifest):
    rows = validate_dataset(dataset, manifest=manifest)
    if config.get('split') != 'dev' or config.get('phase') != 'development':
        raise ValueError('检索调参网格只允许dev')
    if config['dataset_sha256'] != file_sha(dataset) or config['split_manifest_sha256'] != file_sha(manifest):
        raise ValueError('网格与冻结题集/划分不一致')
    if config.get('execution_mode') != 'real_retrieval_grid' or not config.get('grid'):
        raise ValueError('必须明确真实检索网格，不能冒充生成问答')
    if 'metric_schema_version' in config:
        check_split(config, json.loads(Path(manifest).read_text(encoding='utf-8')))
    if len(config['grid']) > 20 or len({r['id'] for r in config['grid']}) != len(config['grid']):
        raise ValueError('网格有界且名称不能重复')
    import re
    for row in config['grid']:
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}', row['id']): raise ValueError('非法配置名称')
        RetrievalPolicy.model_validate(row['policy'])
    return [q for q in rows if q['split'] == 'dev']


def source_citations(hits, documents, assets):
    refs = []
    for h in hits:
        source = documents[h.document_id]
        if h.revision_id != source['revision_id']: raise ValueError('检索证据跨修订')
        refs.extend(dict(document_sha256=source['original_sha256'], page=r['page'])
            for r in h.metadata.get('source_refs', []) if r.get('page'))
        for aid in h.metadata.get('asset_ids', []):
            a = assets.get(aid)
            if not a or a['document_id'] != h.document_id or a['revision_id'] != h.revision_id:
                raise ValueError('图片证据身份不符')
            refs.extend(dict(document_sha256=source['original_sha256'], page=r['page'], asset_sha256=a['sha256'])
                for r in a['source_refs'] if r.get('page'))
    return refs


def ranked_source_candidates(hits, documents, assets):
    """保留真实排序身份及授权来源指纹，供实验运行器离线计分。"""
    candidates = []
    seen = set()
    for hit in hits:
        identity = hit.identity
        if identity in seen:
            raise ValueError('检索排名包含重复切片身份')
        seen.add(identity)
        citations = source_citations([hit], documents, assets)
        candidates.append({
            'candidate_id': json.dumps(list(identity), ensure_ascii=False, separators=(',', ':')),
            'sources': citations,
        })
    return candidates


class RetrievalExecutor:
    def __init__(self, config, gateway, *, embedder, ranker):
        self.config, self.g, self.embedder, self.ranker = config, gateway, embedder, ranker
        self.repo = gateway.repo(config['target']['kb_id'])
        self.documents = {d['document_id']: d for d in config['corpus']['documents']}
        pids = gateway.product_kbs.distinct('product_id', dict(owner_id=gateway.owner_id, kb_id=self.repo.kb_id))
        self.products = list(gateway.products.collection.find(dict(owner_id=gateway.owner_id, product_id={'$in': pids})))
        self.products_by_name = {p['model']: p['product_id'] for p in self.products}
        self.assets = {a['asset_id']: a for d in config['corpus']['snapshot']['documents'] for a in d['assets']}
        self.embeddings = {}

    def encode(self, texts):
        key = tuple(texts)
        if key not in self.embeddings:
            start = time.perf_counter()
            result = self.embedder(texts)
            self.embeddings[key] = (result, time.perf_counter()-start)
        return self.embeddings[key][0]

    def execute(self, question, policy):
        policy = RetrievalPolicy.model_validate(policy)
        # 标准证据/期望行为只在下方指标阶段使用，不传入规划/编码/重排。
        plan = plan_query(question['question'], self.products,
            selected_ids=[self.products_by_name[p] for p in question['product_names']], messages=question['history'])
        if policy.query_projection == 'scoped_subject_v1':
            from app.retrieval.query_projection import project_scoped_subject
            plan = project_scoped_subject(plan, self.products)
        empty = dict(answer='', citations=[], behavior='clarify' if plan.route == 'clarify' else 'insufficient',
            route=plan.route, stage_timings={}, stage_counts={}, stage_metrics={})
        if plan.route == 'clarify':
            if self.config.get('metric_schema_version') == 1:
                empty['retrieval_candidates'] = {'candidates': [], 'reranked': [], 'context': []}
            return empty
        revisions = self.repo.get_active_revisions()
        expected = {(d['document_id'], d['revision_id']) for d in self.documents.values()}
        if expected != {(d['document_id'], d['active_revision_id']) for d in revisions}: raise ValueError('活动修订漂移')
        import psutil
        process = psutil.Process()
        rss_before = process.memory_info().rss
        cpu_before = sum(process.cpu_times()[:2])
        for query in plan.search_queries: self.encode([query])
        encode_seconds = sum(self.embeddings[(query,)][1] for query in plan.search_queries)
        start = time.perf_counter()
        hits = from_index_hits(retrieve(self.g.index(), self.repo, plan, embedder=self.encode,
            revision_snapshot=revisions, policy=policy))
        search_seconds = time.perf_counter()-start
        start = time.perf_counter()
        ranked = rank_hits(question['question'], hits, ranker=self.ranker, policy=policy)
        rank_seconds = time.perf_counter()-start
        # 与正式入口相同的字符预算/图像许可处理；M4-07后由统一预算服务替代。
        from app.query_process.agent.nodes.node_answer_output import step_2_construct_prompt
        from app.knowledge.citation_api import controlled_markdown
        docs = [h.document() for h in ranked[:policy.context_limit]]
        state = dict(original_query=question['question'], history=question['history'],
            item_names=[p['model'] for p in self.products if p['product_id'] in plan.product_ids],
            reranked_docs=[d | dict(text=controlled_markdown(d['text'], set(d['asset_ids']))) for d in docs])
        step_2_construct_prompt(state)
        selected_ids = {(d['document_id'], d['revision_id'], d['chunk_uid']) for d in state['prompt_used_docs']}
        selected = [h for h in ranked if h.identity in selected_ids]
        stage_metrics = {}
        ranked_candidates = {}
        for stage, group in [('candidates', hits), ('reranked', ranked), ('context', selected)]:
            refs = source_citations(group, self.documents, self.assets)
            stage_metrics[stage] = evidence_metrics(question, dict(citations=refs),
                asset_equivalences=self.config['corpus'].get('asset_equivalences', []))['allowed_evidence_group_recall']
            if self.config.get('metric_schema_version') == 1:
                ranked_candidates[stage] = ranked_source_candidates(group, self.documents, self.assets)
        memory = process.memory_info()
        result = empty | dict(citations=source_citations(selected, self.documents, self.assets),
            behavior='answer' if selected else 'insufficient', stage_metrics=stage_metrics,
            stage_counts=dict(candidates=len(hits), reranked=len(ranked), context=len(selected)),
            stage_timings=dict(shared_encoding_seconds=encode_seconds, search_seconds=search_seconds,
                rerank_seconds=rank_seconds, estimated_pipeline_seconds=encode_seconds+search_seconds+rank_seconds),
            resources=dict(rss_before_bytes=rss_before, rss_after_bytes=memory.rss,
                process_peak_rss_bytes=getattr(memory, 'peak_wset', None), cpu_seconds=sum(process.cpu_times()[:2])-cpu_before),
            trace=EvidencePack(plan=plan, candidates=hits, reranked=ranked, selected=selected).trace())
        if self.config.get('metric_schema_version') == 1:
            result['retrieval_candidates'] = ranked_candidates
        try:
            import torch
            if torch.cuda.is_available(): result['resources']['gpu_allocated_bytes'] = torch.cuda.memory_allocated()
        except ImportError:
            pass
        return result


def summarize_recall(records, questions):
    """所有要求证据的题都入分母；错误澄清、执行失败和缺结果均计0。"""
    by_id = {row['id']: row for row in records}
    if len(by_id) != len(records): raise ValueError('逐题结果身份重复')
    applicable = [q for q in questions if q['allowed_evidence']]
    summary = {}
    for stage in ('candidates', 'reranked', 'context'):
        values = []
        for question in applicable:
            row = by_id.get(question['id'], {})
            value = row.get('result', {}).get('stage_metrics', {}).get(stage) if row.get('status') == 'completed' else None
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not 0 <= value <= 1):
                raise ValueError('阶段召回须为有限0..1值')
            values.append(0. if value is None else value)
        summary[stage] = dict(mean=sum(values)/len(values) if values else None, applicable_questions=len(values))
    return summary


def run_grid(config, dataset, manifest, output, gateway, *, embedder, ranker):
    # 网格整体也有占用，避免不同进程在不同子配置之间交错写总报告。
    validate_grid(config, dataset, manifest)
    with output_lock(Path(output)):
        return _run_grid(config, dataset, manifest, output, gateway, embedder=embedder, ranker=ranker)


def _run_grid(config, dataset, manifest, output, gateway, *, embedder, ranker):
    selected = validate_grid(config, dataset, manifest)
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    frozen = output/'grid-config.json'
    if frozen.exists():
        if json.loads(frozen.read_text('utf-8')) != config: raise ValueError('输出目录属于其他网格配置')
    else:
        if any(p.name != '.runner.lock' for p in output.iterdir()): raise ValueError('网格输出目录非空')
        atomic_json(frozen, config)
    execute = RetrievalExecutor(config, gateway, embedder=embedder, ranker=ranker)
    # 冷加载独立记录，不把首组权重加载时间当策略差异。
    from uuid import uuid4
    start = time.perf_counter()
    execute.encode(['设备技术参数查询预热'])
    ranker('设备技术参数查询预热', [dict(text='设备参数以对应资料为准。')])
    atomic_json(output/('warmup-'+uuid4().hex+'.json'), dict(seconds=time.perf_counter()-start,
        config_sha256=fingerprint(config), notice='本机嵌入/重排冷加载及预热；无生成模型调用'))
    reports = []
    for variant in config['grid']:
        per = copy.deepcopy(config)
        per.pop('grid')
        per.update(experiment_id=config['experiment_id']+'-'+variant['id'], parameters=variant['policy'])
        report = run_experiment(dataset, manifest, per, output/variant['id'], lambda q: execute.execute(q, variant['policy']))
        records = [json.loads(line) for line in (output/variant['id']/'results.jsonl').read_text('utf-8').splitlines()]
        completed = [r for r in records if r['status'] == 'completed']
        row = dict(id=variant['id'], policy=variant['policy'], completed=report['completed'], failed=report['failed'])
        row['recall'] = summarize_recall(records, selected)
        timings = [r['result']['stage_timings']['estimated_pipeline_seconds'] for r in completed if r['result']['stage_timings']]
        row.update(p50_pipeline_seconds=percentile(timings,.5), p95_pipeline_seconds=percentile(timings,.95))
        row['max_observed_rss_bytes'] = max((r['result']['resources']['rss_after_bytes'] for r in completed if 'resources' in r['result']), default=None)
        row['clarified'] = sum(r['result']['route']=='clarify' for r in completed)
        if config.get('metric_schema_version') == 1:
            row['summary'] = report.get('summary')
        reports.append(row)
        atomic_json(output/'grid-summary.json', dict(config_sha256=fingerprint(config),
            selected_dev=len(selected), heldout_executed=0, paid_calls=0, variants=reports,
            notice='真实检索实验，未生成答案；页/图来源命中不是答案正确率。编码按问题共享计时，非隔离性能基准；原付费基线不覆盖。'))
    return reports


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dataset', type=Path, required=True)
    parser.add_argument('--manifest', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    try:
        import yaml
        config = yaml.safe_load(args.config.read_text('utf-8'))
        validate_grid(config, args.dataset, args.manifest)
        from .readonly import open_frozen_corpus
        from app.runs.query_runner import encode, rerank
        with open_frozen_corpus(config) as gateway:
            reports = run_grid(config, args.dataset, args.manifest, args.output, gateway, embedder=encode, ranker=rerank)
        if any(r['failed'] for r in reports): raise ValueError('存在失败项，按检查点续验')
    except Exception as exc:
        parser.exit(1, '检索网格未完成，异常类型：'+type(exc).__name__+'；私有输入与服务信息仅留本机。\n')
    print(json.dumps(dict(completed_variants=len(reports), paid_calls=0, heldout_executed=0)))


if __name__ == '__main__': main()
