"""真实有限执行器的预算/失败/并发边界；仓储端口为离线CAS替身。"""
from copy import deepcopy
import threading
from types import SimpleNamespace
import pytest
from app.api.errors import APIError
from app.support.workflow import initial
from app.support.tools import execute_tool, ToolInput, scoped_handlers
from app.support.budget import ToolBudget


class Memory:
    def __init__(self): self.row=initial() | {'state':'ready'}; self.lock=threading.Lock()
    def editable(self,user,cid,version):
        with self.lock:
            if self.row['version']!=version or self.row['state'] in {'cancelled','resolved'}: raise APIError(409,'conflict','冲突')
            return deepcopy(self.row)
    def save(self,user,cid,current,row):
        with self.lock:
            if current['version']!=self.row['version']: raise APIError(409,'conflict','冲突')
            self.row=deepcopy(row) | {'version':current['version']+1}
            return deepcopy(self.row)


def call(repo, handler, **kwargs):
    data=ToolInput(expected_version=repo.row['version'],tool='read_evidence',arguments={'citation_id':'c'})
    return execute_tool(repo,None,'cid',data,{'read_evidence':handler},invoke=lambda f,a,s:f(a),**kwargs)


def output(value='x'): return {'items':[{'text':value}],'notice':'内部资料'}


def test_unknown_and_extra_scope_arguments_never_call_tool():
    repo=Memory(); called=[]
    with pytest.raises(APIError):
        execute_tool(repo,None,'cid',ToolInput(expected_version=0,tool='read_evidence',arguments={'citation_id':'c','kb_id':'foreign'}),{'read_evidence':lambda a:called.append(a)})
    assert called==[] and repo.row['version']==0


def test_call_budget_is_cumulative_after_rebuild():
    repo=Memory()
    call(repo,lambda a:output(),policy=ToolBudget(max_calls=1))
    called=[]
    row=call(repo,lambda a:called.append(a),policy=ToolBudget(max_calls=1))
    assert row['reason']=='tool_call_budget' and called==[] and len(row['tool_calls'])==1


@pytest.mark.parametrize('problem,reason', [('failure','tool_failed'),('invalid','tool_failed'),('large','tool_token_budget')])
def test_failure_invalid_output_and_token_limit_exit_without_private_error(problem,reason):
    repo=Memory()
    def handler(a):
        if problem=='failure': raise RuntimeError('PRIVATE-secret-url')
        return {'arbitrary':'invalid'} if problem=='invalid' else output('x'*200)
    row=call(repo,handler,policy=ToolBudget(max_tokens=100))
    assert row['state']=='handoff' and row['reason']==reason
    assert 'PRIVATE-secret-url' not in str(row)


def test_elapsed_timeout_does_not_accept_late_result():
    repo=Memory(); clock=iter([0,31])
    row=call(repo,lambda a:output(),clock=lambda:next(clock))
    assert row['reason']=='tool_time_budget' and row['tool_calls'][0]['output'] is None


def test_repeat_does_not_continue_loop():
    repo=Memory();call(repo,lambda a:output())
    row=call(repo,lambda a:output())
    assert row['reason']=='tool_repeat'
    with pytest.raises(APIError): call(repo,lambda a:output('new'))


def test_concurrent_or_crashed_inflight_never_dispatches_twice():
    repo=Memory(); entered=threading.Event(); release=threading.Event()
    def handler(a): entered.set(); release.wait(3); return output()
    thread=threading.Thread(target=lambda:call(repo,handler));thread.start();assert entered.wait(3)
    with pytest.raises(APIError) as error: call(repo,lambda a:pytest.fail('重复执行'))
    assert error.value.code=='tool_inflight'
    release.set();thread.join(3)
    assert len(repo.row['tool_calls'])==1


def test_cancellation_during_tool_cannot_be_overwritten():
    repo=Memory()
    def handler(a):
        row=deepcopy(repo.row);row['state']='cancelled';repo.save(None,'cid',repo.row,row)
        return output()
    with pytest.raises(APIError):call(repo,handler)
    assert repo.row['state']=='cancelled' and repo.row['tool_calls'][0]['status']=='running'


def test_search_handler_preserves_source_refs():
    from app.retrieval.models import RetrievalHit
    from app.identity.models import Principal
    user=Principal(user_id='u',username='u',role='viewer',kb_ids=('k',))
    class Gateway:
        def product(self,*a):return {}
        def revision(self,*a):return {}
        def repo(self,*a):return SimpleNamespace(get_active_revisions=lambda:[])
        def index(self):return SimpleNamespace(search=lambda *a,**kw:[{'entity':{'document_id':'d','revision_id':'v','chunk_uid':'c','text':'检查接线','metadata':{'source_refs':[{'line_start':3}]}}}])
    resources={'knowledge':lambda:Gateway(),'conversations':SimpleNamespace(get=lambda *a:{'kb_id':'k'}),
        'runs':SimpleNamespace(get=lambda *a:{'product_snapshot':{'product_ids':['p']}}),
        'query_runner':SimpleNamespace(embedder=lambda t:{})}
    handlers=scoped_handlers(SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(resources=resources))),user,'cid',{'run_id':'r'})
    result=handlers['search_manual']({'query':'检查'})
    assert result['items'][0]['source_refs']==[{'line_start':3}]
