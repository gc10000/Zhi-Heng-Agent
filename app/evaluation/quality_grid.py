"""当前版本dev单因素/组合检索评价；真实阶段缓存显式留痕，绝不伪装模型新调用。"""
import argparse
import copy
import json
import math
from pathlib import Path
import threading
import time
from uuid import uuid4
from .validate_dataset import validate_dataset,file_sha,fingerprint
from .runner import run_experiment,output_lock,atomic_json,evidence_metrics,percentile
from .retrieval_grid import RetrievalExecutor,source_citations,summarize_recall
from .strategy import EvaluationStrategy


class StageCache:
    def __init__(self,root,scope):
        self.root=Path(root);self.scope=scope;self.locks={k:threading.RLock() for k in ('retrieval','rank','hypothesis','expansion')}
        self.root.mkdir(parents=True,exist_ok=True)
    def get(self,kind,args,operation):
        key=fingerprint([self.scope,kind,args]);path=self.root/(key+'.json')
        with self.locks[kind]:
            if path.exists():
                saved=json.loads(path.read_text('utf-8'))
                payload={k:saved[k] for k in ('key','value','seconds')}
                if saved['key']!=key or saved.get('payload_sha256')!=fingerprint(payload) or not math.isfinite(saved['seconds']) or saved['seconds']<0:
                    raise ValueError('阶段缓存被改动或不属于当前冻结执行')
                return copy.deepcopy(saved['value']),dict(reused=True,original_seconds=saved['seconds'],key=key)
            started=time.perf_counter();value=operation();seconds=time.perf_counter()-started
            saved=dict(key=key,value=value,seconds=seconds)
            saved['payload_sha256']=fingerprint(saved)
            with path.open('x',encoding='utf-8') as stream:json.dump(saved,stream,ensure_ascii=False,allow_nan=False)
            return copy.deepcopy(value),dict(reused=False,original_seconds=seconds,key=key)


class QualityExecutor(RetrievalExecutor):
    def __init__(self,config,gateway,*,embedder,ranker,cache,hyde=None,counts=None):
        super().__init__(config,gateway,embedder=embedder,ranker=ranker)
        self.cache,self.hyde,self.counts=cache,hyde,counts
    def execute(self,question,parameters):
        from app.retrieval.query_planner import plan_query
        from app.retrieval.search import retrieve
        from app.retrieval.graph import run_retrieval_graph
        from app.retrieval.adapters import from_index_hits,stable_key
        from app.retrieval.rerank import rank_hits
        from app.retrieval.expansion import expand_evidence
        from app.query_process.agent.nodes.node_answer_output import step_2_construct_prompt
        from app.knowledge.citation_api import controlled_markdown
        policies=EvaluationStrategy.model_validate(parameters);policy=policies.retrieval
        before=self.counts.snapshot() if self.counts else {}
        # 只用用户输入规划；标签严格限于最后的辅助指标。
        plan=plan_query(question['question'],self.products,
            selected_ids=[self.products_by_name[p] for p in question['product_names']],messages=question['history'])
        empty=dict(answer='',citations=[],behavior='clarify' if plan.route=='clarify' else 'insufficient',
            route=plan.route,stage_metrics={},stage_timings={},stage_counts={},stage_cache=[],logical_provider_calls={})
        if plan.route=='clarify':return empty
        revisions=self.repo.get_active_revisions()
        if {(d['document_id'],d['revision_id']) for d in self.documents.values()}!={(d['document_id'],d['active_revision_id']) for d in revisions}:
            raise ValueError('活动修订已漂移')
        plan=plan.model_copy(update=dict(revision_ids=tuple(r['active_revision_id'] for r in revisions)))
        observations=[];observation_lock=threading.Lock();sealed=False
        def memo(kind,args,operation,branch='post_join'):
            value,observation=self.cache.get(kind,args,operation)
            with observation_lock:
                if not sealed:observations.append(observation|dict(kind=kind,branch=branch))
            return value
        def search(branch):
            name='local' if branch.search_queries==plan.search_queries else ('hyde' if any('\n检索假设：' in q for q in branch.search_queries) else 'decomposition')
            return memo('retrieval',[branch.model_dump(mode='json'),policy.model_dump()],lambda:retrieve(self.g.index(),self.repo,
                branch,embedder=self.encode,revision_snapshot=revisions,policy=policy),name)
        def hyde(query,p):
            if self.hyde is None:raise ValueError('HyDE未配置')
            return memo('hypothesis',[query,p.model_dump(),policies.answer_budget.output_token_field],lambda:self.hyde(query,p,policies.answer_budget.output_token_field),'hyde')
        branches=run_retrieval_graph(plan,search,policy=policies.enhancement,hyde=hyde)
        # 复用仅免去重复计算，不得把原本超时的可选证据重新纳入上下文。
        # 以各分支实际阶段耗时之和作下界；主路径证据即使重复也不受影响。
        with observation_lock:
            snapshot=copy.deepcopy(observations)
        expired=set()
        for info in branches.branches:
            if info['name']=='local':continue
            seconds=sum(o['original_seconds'] for o in snapshot if o['branch']==info['name'])
            if info['status'] in ('completed','empty') and seconds>policies.enhancement.timeout_seconds:
                info.update(status='timeout',original_stage_seconds=seconds,cache_timeout_guard=True)
                expired.add(info['name'])
        branches.hits=[h for h in branches.hits if not any(
            s.get('query_id','').startswith('branch:'+name+'/')
            for name in expired for s in h.get('retrieval_trace',[]))]
        candidates=from_index_hits(branches.hits)
        def cached_rank(query,docs):
            args=[query,[{k:d[k] for k in ('document_id','revision_id','chunk_uid','text','metadata')} for d in docs]]
            def compute():
                found=self.ranker(query,docs)
                known={stable_key(d) for d in docs}
                rows=[dict(identity=list(stable_key(d)),score=d.get('score')) for d in found]
                if len(rows)!=len(docs) or len({tuple(r['identity']) for r in rows})!=len(rows) or any(tuple(r['identity']) not in known or not isinstance(r['score'],(int,float)) or not math.isfinite(r['score']) for r in rows):
                    raise ValueError('实际重排结果格式无效')
                return rows
            rows=memo('rank',args,compute);by_id={stable_key(d):d for d in docs}
            return [by_id[tuple(r['identity'])]|dict(score=r['score']) for r in rows]
        ranked=rank_hits(question['question'],candidates,ranker=cached_rank,policy=policy)
        def related(seeds,**kw):
            return memo('expansion',[[s.model_dump() for s in seeds],kw],lambda:self.g.index().related_rows(self.repo,seeds,**kw))
        expanded=expand_evidence(ranked[:policy.context_limit],loader=related,
            owner_id=self.repo.owner_id,kb_id=self.repo.kb_id,policy=policies.expansion)
        docs=[h.document() for h in expanded.selected]
        state=dict(original_query=question['question'],history=question['history'],answer_budget=policies.answer_budget,
            item_names=[p['model'] for p in self.products if p['product_id'] in plan.product_ids],
            evidence_groups=expanded.groups,
            reranked_docs=[d|dict(text=controlled_markdown(d['text'],set(d['asset_ids']))) for d in docs])
        if plan.route=='compare':state['evidence_scope_note']='比较只能依据本轮参考内容，未提供某型号证据时必须明确资料不足，不得推断其参数。'
        step_2_construct_prompt(state)
        selected_ids={stable_key(d) for d in state['prompt_used_docs']}
        selected=[h for h in expanded.selected if h.identity in selected_ids]
        stages={name:evidence_metrics(question,dict(citations=source_citations(hits,self.documents,self.assets)),
            asset_equivalences=self.config['corpus'].get('asset_equivalences',[]))['allowed_evidence_group_recall']
            for name,hits in [('candidates',candidates),('reranked',ranked),('context',selected)]}
        with observation_lock:
            sealed=True;observations=copy.deepcopy(observations)
        return empty|dict(citations=source_citations(selected,self.documents,self.assets),behavior='answer' if selected else 'insufficient',
            stage_metrics=stages,stage_counts=dict(candidates=len(candidates),reranked=len(ranked),context=len(selected),expanded=len(expanded.expanded)),
            prompt_budget=state['prompt_budget'],expansion_excluded=expanded.excluded,retrieval_branches=branches.branches,
            stage_cache=observations,stage_timings=dict(original_observed_stage_seconds=sum(o['original_seconds'] for o in observations)),
            logical_provider_calls={k:v-before[k] for k,v in self.counts.snapshot().items()} if self.counts else {})


def validate_quality_grid(config,dataset,manifest):
    rows=validate_dataset(dataset,manifest=manifest)
    if config.get('split')!='dev' or config.get('phase')!='development' or config.get('strategy')!='m4-configured' or config.get('execution_mode')!='real_retrieval_grid':
        raise ValueError('质量开发网格只允许明确的dev检索评价')
    if config['dataset_sha256']!=file_sha(dataset) or config['split_manifest_sha256']!=file_sha(manifest):raise ValueError('题集/划分指纹不符')
    import re
    variants=config.get('grid',[])
    if not 1<=len(variants)<=12 or len({v['id'] for v in variants})!=len(variants):raise ValueError('网格名称须唯一且有界')
    for variant in variants:
        if not re.fullmatch(r'[a-z0-9][a-z0-9_-]{0,63}',variant['id']):raise ValueError('非法配置名称')
        EvaluationStrategy.model_validate(variant['parameters'])
    return [r for r in rows if r['split']=='dev']


def run_quality_grid(config,dataset,manifest,output,gateway,*,embedder,ranker,hyde=None,counts=None):
    questions=validate_quality_grid(config,dataset,manifest);output=Path(output)
    with output_lock(output):
        path=output/'quality-config.json'
        if path.exists():
            if json.loads(path.read_text('utf-8'))!=config:raise ValueError('输出目录属于其他配置')
        else:
            if any(p.name!='.runner.lock' for p in output.iterdir()):raise ValueError('输出目录非空')
            atomic_json(path,config)
        scope=fingerprint({k:config[k] for k in ('versions','target','corpus')})
        cache=StageCache(output/'stage-cache',scope)
        execute=QualityExecutor(config,gateway,embedder=embedder,ranker=ranker,cache=cache,hyde=hyde,counts=counts)
        reports=[]
        try:
            for variant in config['grid']:
                per=copy.deepcopy(config);per.pop('grid');per.update(experiment_id=config['experiment_id']+'-'+variant['id'],parameters=variant['parameters'])
                report=run_experiment(dataset,manifest,per,output/variant['id'],lambda q:execute.execute(q,variant['parameters']))
                records=[json.loads(line) for line in (output/variant['id']/'results.jsonl').read_text('utf-8').splitlines()]
                complete=[r for r in records if r['status']=='completed']
                categories={category:summarize_recall(records,[q for q in questions if q['category']==category]) for category in sorted({q['category'] for q in questions})}
                reports.append(dict(id=variant['id'],parameters=variant['parameters'],completed=report['completed'],failed=report['failed'],
                    recall=summarize_recall(records,questions),by_category=categories,
                    p50_execution_seconds=report['p50_seconds'],p95_execution_seconds=report['p95_seconds'],
                    cache_reuse_operations=sum(o['reused'] for r in complete for o in r['result'].get('stage_cache',[])),
                    clarified_ids=[r['id'] for r in complete if r['result']['route']=='clarify'],
                    branch_statuses={name:{status:sum(b['name']==name and b['status']==status for r in complete for b in r['result'].get('retrieval_branches',[]))
                        for status in ('completed','empty','skipped','failed','timeout','busy')} for name in ('local','hyde','decomposition')}))
                atomic_json(output/'quality-summary.json',dict(config_sha256=fingerprint(config),variants=reports,selected_dev=len(questions),heldout_executed=0,
                    notice='检索来源覆盖不是答案正确率。真实阶段缓存命中显式记录；执行wall含复用，不能当生产性能或新模型调用。'))
        finally:
            if counts is not None:
                with (output/('provider-counts-'+uuid4().hex+'.json')).open('x',encoding='utf-8') as stream:
                    json.dump(dict(config_sha256=fingerprint(config),logical_calls=counts.snapshot(),exact_sdk_http_calls=None,exact_cost=None),stream,indent=2)
        return reports


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('dataset','manifest','config','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    import yaml
    config=yaml.safe_load(args.config.read_text('utf-8'));validate_quality_grid(config,args.dataset,args.manifest)
    from .readonly import open_frozen_corpus
    from .provider_counts import LogicalProviderCounts
    from app.lm.runtime import ModelRuntimePolicy,warmup_models
    from app.runs.query_runner import encode,rerank
    counts=LogicalProviderCounts()
    def hyde(query,policy,output_token_field):
        from app.core.load_prompt import load_prompt
        from app.lm.lm_utils import get_llm_client
        from app.infrastructure.providers.clients import output_limit_options
        client=counts.wrap(get_llm_client())
        return client.invoke(load_prompt('hyde_prompt',rewritten_query=query),timeout=policy.timeout_seconds,
            **output_limit_options(client,policy.hyde_output_tokens,output_token_field)).content
    if any(EvaluationStrategy.model_validate(v['parameters']).runtime!=ModelRuntimePolicy.load() for v in config['grid']):raise ValueError('模型运行策略不符')
    with open_frozen_corpus(config) as gateway:
        warmup_models()
        reports=run_quality_grid(config,args.dataset,args.manifest,args.output,gateway,embedder=encode,ranker=rerank,hyde=hyde,counts=counts)
    print(json.dumps(dict(completed_variants=len(reports),failed_questions=sum(r['failed'] for r in reports),logical_calls=counts.snapshot(),heldout_executed=0)))
    if any(r['failed'] for r in reports):raise SystemExit(1)


if __name__=='__main__':main()
