"""M7新隔离八槽；只用合成计量，不访问模型。"""
import copy
import importlib
import json
from concurrent.futures import ThreadPoolExecutor

import pytest

pytestmark = pytest.mark.integration


@pytest.fixture(params=[1,2])
def demo(mongo_db, tmp_path, monkeypatch, request):
    m = importlib.import_module('app.infrastructure.providers.m7_demo')
    from app.infrastructure.providers.output_contract import OperationalDemoContract
    from app.knowledge.repository import fingerprint
    version=request.param
    batch=f'm7-operational-closure-r{version}'
    auth = {'kind': f'explicit_user_m7_operational_authorization_v{version}', 'adopted': True,
            'control_database': mongo_db.name, 'max_streams': 8,
            'input_budget': 227328, 'output_budget': 32768, 'adopted_at':'2026-11-04', 'user_instruction_sha256':'a'*64,
            'accepted_unknown_limits':['gateway_hard_limit','paid_output_hard_limit','cost_limit','exact_http_count']}
    if version==2:
        import hashlib
        auth.update(batch=batch,user_instruction='synthetic',user_instruction_sha256=hashlib.sha256(b'synthetic').hexdigest())
    ap = tmp_path / 'auth.json'; ap.write_text(json.dumps(auth), encoding='utf-8')
    import hashlib
    manifest = dict(id=batch, control_database=mongo_db.name,
        source_identity=m.source_identity(), targets=[dict(database=mongo_db.name+('_s' if version==2 else ''), bucket='zh-preview-test', collection='c'),dict(database=mongo_db.name+'_r',bucket='zh-preview-restore',collection='r')],
        scope=dict(owner_id='org', kb_id='kb', product_id='p'), sources=[],
        members=[dict(slot=f'{i+1:02}', question=q, user_id='u', conversation_id=f'c{i}', request_id=f'{batch}:{i+1:02}' if version==2 else f'r{i}',
                      target=0 if i<7 else 1, wave=0 if i==0 else 1 if i<3 else 2 if i<7 else 3) for i,q in enumerate(m.QUESTIONS)])
    mp = tmp_path / 'manifest.json'; mp.write_text(json.dumps(manifest), encoding='utf-8')
    monkeypatch.setenv('M7_DEMO_MANIFEST', str(mp)); monkeypatch.setenv('M7_DEMO_AUTHORIZATION', str(ap))
    policy = OperationalDemoContract(function_version=f'm7_operational_demo_v{version}',enabled=True, endpoint_sha256='e'*64, model='qwen3.8-flash',
        client_versions={'openai':'2.28.0','langchain-openai':'1.1.11'}, ledger_id=manifest['id'],
        limit_field='max_completion_tokens',thinking=False, max_total_input_tokens=227328,max_total_output_tokens=32768,
        manifest_sha256=fingerprint(manifest),control_database=mongo_db.name,
        authorization_sha256=hashlib.sha256(ap.read_bytes()).hexdigest())
    ledger=m.DemoLedger(mongo_db,policy)
    def row(i=0):
        x=manifest['members'][i]
        return dict(execution_token='lease',run_id=m.member_run_id(manifest,x),identity=f'i{i}',owner_id='u',kb_id='kb',
            conversation_id=x['conversation_id'],client_request_id=x['request_id'],question=x['question'])
    def freeze(i=0):
        r=row(i);ledger.persist_input(r,'exact prompt',{'prompt_budget':{'input_tokens':20,'input_limit':28416},
            'prompt_used_docs':[{'text':'合成原文','chunk_uid':'u','revision_id':'r'}],'prompt_reference_map':[{'reference_number':1}]})
        return r
    return m,ledger,row,freeze,manifest,policy


def test_slot_cas_concurrent_only_one(demo):
    m,l,row,freeze,_,_=demo; r=freeze()
    def begin(_):
        try:l.begin(r['run_id'],r['identity'],input_reservation=20);return True
        except Exception:return False
    with ThreadPoolExecutor(max_workers=8) as pool:result=list(pool.map(begin,range(8)))
    assert sum(result)==1
    assert len(l.read()['pending'])==1


@pytest.mark.parametrize('mode',['missing','bad','excess','interrupted','thinking','finish'])
def test_first_failure_persistently_stops_new_dispatch(demo, mode):
    _,l,row,freeze,_,_=demo;r=freeze();l.begin(r['run_id'],r['identity'],input_reservation=20)
    usage={'input':10,'output':4}
    if mode=='missing':usage={}
    if mode=='bad':usage['output']=True
    if mode=='excess':usage['output']=4097
    product={'visible_body':True,'truncated':False,'finish_reason':'stop','observed_reasoning':mode=='thinking'}
    if mode=='finish':product['finish_reason']='content_filter'
    l.settle(r['run_id'],r['identity'],usage,completed=mode!='interrupted',
             logical_calls={'invoke_started':0,'stream_started':1},product_state=product)
    assert l.read()['halt'] is True
    with pytest.raises(Exception):l.begin(r['run_id'],r['identity'],input_reservation=20)


def test_settlement_idempotent_and_conflict_rejected(demo):
    _,l,_,freeze,_,_=demo;r=freeze();l.begin(r['run_id'],r['identity'],input_reservation=20)
    args=dict(completed=True,logical_calls={'invoke_started':0,'stream_started':1},
              product_state={'visible_body':True,'truncated':False,'finish_reason':'stop','observed_reasoning':False})
    l.settle(r['run_id'],r['identity'],{'input':10,'output':4},**args)
    l.settle(r['run_id'],r['identity'],{'input':10,'output':4},**args)
    assert l.read()['known_input']==10
    with pytest.raises(Exception):l.settle(r['run_id'],r['identity'],{'input':11,'output':4},**args)
    with pytest.raises(Exception):l.begin(r['run_id'],r['identity'],input_reservation=20)


def test_wave_input_and_identity_fail_closed(demo):
    _,l,row,freeze,manifest,_=demo
    r=freeze(1)
    with pytest.raises(Exception):l.begin(r['run_id'],r['identity'],input_reservation=20)
    forged=copy.deepcopy(row());forged['question']='任意问题'
    with pytest.raises(Exception):l.persist_input(forged,'p',{})
    r=freeze();l.begin(r['run_id'],r['identity'],input_reservation=20)
    l.inputs.delete_one({'run_id':r['run_id']})
    with pytest.raises(Exception):l.begin(r['run_id'],r['identity'],input_reservation=20)
    assert len(l.read()['pending'])==1


def test_failure_before_provider_halts_without_usage_zero(demo):
    _,l,_,_,_,_=demo;l.fail('r','retrieval_failed')
    assert l.read()['halt'] and not l.read()['settled'] and l.read()['input_tokens'] is None


def test_input_cannot_be_resigned_after_consumption(demo):
    _,l,_,freeze,_,_=demo;r=freeze();l.begin(r['run_id'],r['identity'],input_reservation=20)
    l.inputs.delete_one({'run_id':r['run_id']})
    with pytest.raises(Exception):freeze()
    assert l.inputs.count_documents({})==0


def test_profile_and_disabled_route(demo, monkeypatch):
    m,_,_,_,_,policy=demo
    from app.infrastructure.providers.output_contract import parse_contract,is_product_risk,OutputLedger
    assert parse_contract(policy.model_dump()).function_version==policy.function_version
    assert is_product_risk(policy)
    assert not is_product_risk(policy.model_copy(update={'enabled':False}))
    for key,value in [('thinking',True),('max_total_output_tokens',32769),('model','other')]:
        with pytest.raises(Exception):parse_contract(policy.model_dump()|{key:value})
    monkeypatch.delenv('M7_DEMO_MANIFEST')
    assert m.contract_from_environment() is None


@pytest.mark.parametrize('mutation',['batch','request','control','source_hash'])
def test_v2_rejects_cross_batch_and_recoverable_control(demo,monkeypatch,tmp_path,mutation):
    m,l,_,_,manifest,policy=demo
    if policy.function_version!='m7_operational_demo_v2':
        pytest.skip('r2增量身份边界不适用于历史v1')
    from app.knowledge.repository import fingerprint
    forged=copy.deepcopy(manifest)
    if mutation=='batch':forged['id']='m7-operational-closure-r1'
    if mutation=='request':forged['members'][0]['request_id']='new-nonce'
    if mutation=='control':forged['targets'][0]['database']=policy.control_database
    if mutation=='source_hash':forged['source_identity']='0'*64
    mp=tmp_path/'forged.json';mp.write_text(json.dumps(forged),encoding='utf-8')
    monkeypatch.setenv('M7_DEMO_MANIFEST',str(mp))
    with pytest.raises(Exception):m.require(policy.model_copy(update={'manifest_sha256':fingerprint(forged)}))
