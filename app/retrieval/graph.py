"""正式检索增强的有界分支与一次汇合；晚到分支不写运行状态。"""
import copy
import time
import threading
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor,TimeoutError
from .routing import EnhancementPolicy,enhancement_queries

_POOL=ThreadPoolExecutor(max_workers=2,thread_name_prefix='可选检索增强')
_SLOTS=threading.BoundedSemaphore(2)


@dataclass
class RetrievalGraphResult:
    hits:list
    branches:list
    merge_count:int=1


def _trace(name,hits):
    output=copy.deepcopy(hits)
    if name!='local':
        from .adapters import score_record
        for rank,hit in enumerate(output,1):
            steps=hit.get('retrieval_trace') or [score_record('retrieval',rank,hit.get('distance'),'backend_unspecified')]
            hit['retrieval_trace']=[s|dict(query_id='branch:'+name+'/'+s['query_id']) for s in steps]
    return output


def run_retrieval_graph(plan,search,*,policy,hyde=None,boundary=lambda:None):
    policy=EnhancementPolicy.model_validate(policy)
    routes=enhancement_queries(plan,policy)
    pending={};branches={};hits={}
    def invoke(name,operation):
        started=time.monotonic()
        try:
            found=operation()
            return dict(name=name,status='completed' if found else 'empty',seconds=time.monotonic()-started),_trace(name,found)
        except Exception as exc:
            from app.infrastructure.providers.policy import classify
            return dict(name=name,status='failed',seconds=time.monotonic()-started,error_code=classify(exc)[0]),[]
    def submit(name,operation,enabled):
        if not enabled:branches[name]=dict(name=name,status='skipped',seconds=0.);return
        semaphore=_SLOTS
        if not semaphore.acquire(blocking=False):branches[name]=dict(name=name,status='busy',seconds=0.);return
        started=time.monotonic()
        try:future=_POOL.submit(invoke,name,operation)
        except BaseException:semaphore.release();raise
        future.add_done_callback(lambda f:semaphore.release())
        pending[name]=(started,future)
    def hyde_search():
        if hyde is None:raise ValueError('HyDE供应商未配置')
        hypothesis=hyde(plan.search_queries[0],policy)
        if not isinstance(hypothesis,str) or not hypothesis.strip() or len(hypothesis)>policy.hyde_max_chars:raise ValueError('HyDE响应格式无效')
        derived=plan.model_copy(update=dict(search_queries=(plan.search_queries[0]+'\n检索假设：'+hypothesis,)))
        return search(derived)
    submit('hyde',hyde_search,routes['hyde'])
    submit('decomposition',lambda:search(plan.model_copy(update=dict(search_queries=routes['decomposition']))),bool(routes['decomposition']))
    boundary();started=time.monotonic()
    # 主路径失败必须由外层保存failed；可选分支不能伪造主路径成功。
    found=search(plan)
    branches['local']=dict(name='local',status='completed' if found else 'empty',seconds=time.monotonic()-started)
    hits['local']=_trace('local',found)
    for name,(started,future) in pending.items():
        boundary()
        remaining=max(0.,policy.timeout_seconds-(time.monotonic()-started))
        try:
            info,found=future.result(timeout=remaining)
            if info['seconds']>policy.timeout_seconds:
                info=dict(name=name,status='timeout',seconds=policy.timeout_seconds);found=[]
        except TimeoutError:
            info=dict(name=name,status='timeout',seconds=policy.timeout_seconds);found=[]
        branches[name]=info;hits[name]=found
    boundary()
    ordered=('local','hyde','decomposition')
    return RetrievalGraphResult([hit for name in ordered for hit in hits.get(name,[])],[branches[name] for name in ordered])
