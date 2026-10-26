"""调用观测不保存prompt/响应，完整计量才返回token。"""
from types import SimpleNamespace
import app.runs.telemetry as telemetry


def test_observed_client_counts_success_and_unknown_without_private_content():
    assert hasattr(telemetry,'ObservedClient'), '正式模型端口尚未接安全调用观测'
    class Client:
        model_name='test-model'
        extra_body={}
        def invoke(self,*args,**kwargs):return SimpleNamespace(content='private answer',usage_metadata={'input_tokens':3,'output_tokens':2})
        def stream(self,*args,**kwargs):
            yield SimpleNamespace(content='private stream',usage_metadata={'input_tokens':4,'output_tokens':5})
    recorder=telemetry.ProviderTelemetry()
    client=telemetry.ObservedClient(Client(),recorder)
    client.invoke('private prompt')
    list(client.stream('private prompt'))
    value=recorder.snapshot()
    assert value['logical_provider_calls']=={'invoke_started':1,'stream_started':1}
    assert value['token_usage']=={'input':7,'output':7}
    assert value['models']==['test-model'] and 'private' not in str(value)


def test_failed_or_missing_usage_is_unknown_and_zero_is_preserved():
    assert hasattr(telemetry,'ObservedClient'), '正式模型端口尚未接安全调用观测'
    class Client:
        def invoke(self,*a,**kw):return SimpleNamespace(content='x',usage_metadata={'input_tokens':0,'output_tokens':0})
        def stream(self,*a,**kw):raise TimeoutError('private signature URL')
    recorder=telemetry.ProviderTelemetry()
    client=telemetry.ObservedClient(Client(),recorder)
    client.invoke('private')
    assert recorder.snapshot()['token_usage']=={'input':0,'output':0}
    try:list(client.stream('private'))
    except TimeoutError:pass
    assert recorder.snapshot()['token_usage']=={'input':None,'output':None}
    assert 'private' not in str(recorder.snapshot())


def test_stream_final_usage_is_total_and_non_usage_chunks_do_not_destroy_it():
    class Client:
        def stream(self,*args,**kwargs):
            yield SimpleNamespace(content='private part')
            yield SimpleNamespace(content='',usage_metadata={'input_tokens':10,'output_tokens':5})
    recorder=telemetry.ProviderTelemetry()
    list(telemetry.ObservedClient(Client(),recorder).stream('private'))
    assert recorder.snapshot()['token_usage']=={'input':10,'output':5}


def test_observer_preserves_policy_client_provider_options():
    from app.infrastructure.providers.clients import PolicyChatClient,output_limit_options
    from app.infrastructure.providers.policy import ProviderPolicy
    underlying=SimpleNamespace(extra_body={'enable_thinking':False},model_name='qwen-test')
    wrapped=telemetry.ObservedClient(PolicyChatClient(underlying,ProviderPolicy('text')),telemetry.ProviderTelemetry())
    assert output_limit_options(wrapped,128)['extra_body']=={'enable_thinking':False,'max_tokens':128}


def test_projection_never_trusts_nested_tokens_or_call_objects():
    from tests.unit.test_telemetry_redaction import Repo
    row={'run_id':'r','state':'completed','telemetry':{'schema_version':1,
        'token_usage':{'input':{'private':'secret'},'output':True},
        'logical_provider_calls':{'invoke_started':2,'url':'https://private/?key=secret'},
        'stage_seconds':{'answer':-1,'private':'secret'}}}
    result=telemetry.run_telemetry(Repo(row,[]),None,'r')
    assert 'secret' not in str(result)
    assert result['token_usage']=={'input':None,'output':None}
    assert result['stage_seconds']=={}
