"""八槽内部演示准入。控制账本独立于可恢复的知识数据，不沿用M6额度。"""
import copy
import hashlib
import json
import os
from pathlib import Path
from uuid import NAMESPACE_URL, uuid5

from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.knowledge.repository import fingerprint

VERSION = 'm7_operational_demo_v1'
BATCH = 'm7-operational-closure-r1'
QUESTIONS = (
    '机身有几个演示网口？请引用资料。',
    'ZH-DEMO-Dock的端口能否算作机身能力？请引用资料说明。',
    '操作前的电源状态应该是什么？请引用资料。',
    '指示灯亮起与松开按钮的先后顺序是什么？请引用资料。',
    '资料要求先断电吗？请说明这一前提并引用。',
    '决定后续操作前，需要核对哪些信息？请引用资料。',
    '请分别说明机身网口和Dock端口的归属，引用各自依据。',
    '机身有几个演示网口？请引用资料。')


def deny(message='内部演示范围、输入或额度不符，停止派发。'):
    raise APIError(409, 'm7_demo_blocked', message)


def source_identity():
    root = Path(__file__).resolve().parents[3]
    files = sorted(p for directory in ('app', 'prompts') for p in (root / directory).rglob('*')
                   if p.is_file() and p.suffix in {'.py', '.md', '.txt', '.jinja', '.j2'})
    return fingerprint({p.relative_to(root).as_posix(): hashlib.sha256(
        p.read_bytes().replace(b'\r\n', b'\n')).hexdigest() for p in files})


def require(policy):
    from .output_contract import parse_contract
    policy=parse_contract(policy)
    raw = Path(os.environ['M7_DEMO_AUTHORIZATION']).read_bytes()
    auth = json.loads(raw)
    m = json.loads(Path(os.environ['M7_DEMO_MANIFEST']).read_text('utf-8'))
    if (hashlib.sha256(raw).hexdigest() != policy.authorization_sha256 or
        auth.get('kind') != 'explicit_user_m7_operational_authorization_v1' or auth.get('adopted') is not True or
        [auth.get(k) for k in ('max_streams','input_budget','output_budget')] != [8,227328,32768] or
        auth.get('control_database') != policy.control_database or
        fingerprint(m) != policy.manifest_sha256 or m.get('id') != BATCH or
        m.get('control_database') != policy.control_database or m.get('source_identity') != source_identity() or
        len(m.get('members', [])) != 8 or [x.get('question') for x in m['members']] != list(QUESTIONS) or
        [x.get('slot') for x in m['members']] != [f'{i:02}' for i in range(1,9)] or
        [x.get('wave') for x in m['members']] != [0,1,1,2,2,2,2,3] or
        [x.get('target') for x in m['members']] != [0,0,0,0,0,0,0,1] or
        len(m.get('targets',[])) != 2 or
        len({x['conversation_id'] for x in m['members']}) != 8 or
        len({x['request_id'] for x in m['members']}) != 8 or
        len({x['user_id'] for x in m['members']}) != 1 or
        auth.get('accepted_unknown_limits') != ['gateway_hard_limit','paid_output_hard_limit','cost_limit','exact_http_count'] or
        not auth.get('user_instruction_sha256') or not auth.get('adopted_at') or
        not policy.control_database.startswith('m1_test_m4_')):
        deny()
    return m


def member_run_id(manifest, member):
    return str(uuid5(NAMESPACE_URL, manifest['id'] + ':' + member['slot']))


def contract_from_environment():
    if not os.getenv('M7_DEMO_MANIFEST'):
        return None
    from app.answering.service import AnswerBudget
    p = AnswerBudget.load().output_contract
    if p is None or p.function_version != VERSION or not p.enabled:
        deny()
    require(p)
    return p


def member_for(m, row):
    found = [x for x in m['members'] if all(row.get(k) == x[v] for k,v in (
        ('owner_id','user_id'),('conversation_id','conversation_id'),
        ('client_request_id','request_id'),('question','question')))]
    if len(found) != 1 or row.get('kb_id') != m['scope']['kb_id']:
        deny()
    x = found[0]
    if row.get('run_id', member_run_id(m,x)) != member_run_id(m,x):
        deny()
    return x


def admit_request(db, user, cid, data):
    """仅受控新实例注入内部合同；公开请求不能指定合同、控制库或新槽。"""
    p = contract_from_environment()
    if p is None:
        if getattr(getattr(data,'output_contract',None),'function_version',None) == VERSION:
            deny()
        return data, None
    m = require(p)
    x = member_for(m, dict(owner_id=user.user_id, conversation_id=cid, kb_id=data.kb_id,
        question=data.question,client_request_id=data.client_request_id))
    target = m['targets'][x['target']]
    if (db.name != target['database'] or os.getenv('M2_OBJECT_BUCKET') != target['bucket'] or
        os.getenv('M2_MILVUS_COLLECTION') != target['collection'] or
        list(data.product_ids) != [m['scope']['product_id']]):
        deny()
    DemoLedger(db,p).require_open()
    from app.runs.models import InternalRunInput
    return InternalRunInput(**data.model_dump(exclude={'output_contract'}),output_contract=p),member_run_id(m,x)


def validate_runtime(policy, row, context, db):
    m = require(policy); x = member_for(m,row); target=m['targets'][x['target']]
    if (db.name != target['database'] or os.getenv('M2_OBJECT_BUCKET') != target['bucket'] or
        os.getenv('M2_MILVUS_COLLECTION') != target['collection'] or
        os.getenv('M2_KNOWLEDGE_OWNER_ID') != m['scope']['owner_id']):
        deny()


def validate_client(policy, client):
    if (client.temperature != .1 or float(client.request_timeout) != 120 or client.stream_usage is not True or
        client.root_client._client.follow_redirects is not False):
        deny('演示客户端profile不符。')


def validate_prompt(policy, prompt, state):
    require(policy)
    b=state['prompt_budget']
    if (not state.get('prompt_used_docs') or len(state['prompt_used_docs'])>10 or
        type(b['input_tokens']) is not int or not 0 < b['input_tokens'] <= 28416 or
        b['input_limit'] != 28416 or state.get('history') or
        state.get('answer') or any(d.get('source')=='internet' for d in state['prompt_used_docs'])):
        deny('演示实际输入或来源边界不符。')


def validate_pipeline(runner, row, gateway):
    from .policy import ProviderPolicy
    m=require(row['output_contract']); member_for(m,row)
    validate_runtime(runner.answer_budget.output_contract,row,None,runner.repo.db)
    config=dict(retrieval=runner.retrieval_policy.model_dump(mode='json'),
        expansion=runner.expansion_policy.model_dump(mode='json'),enhancement=runner.enhancement_policy.model_dump(mode='json'),
        attribution=runner.evidence_attribution.model_dump(mode='json'))
    if (config != m['configuration'] or any(ProviderPolicy.load(k).max_retries for k in ('text','embedding','rerank')) or
        [getattr(runner.answer_budget,k) for k in ('context_window','output_tokens','reserve_tokens','max_chars')] != [32768,4096,256,12000] or
        runner.retrieval_policy.context_limit != 10 or
        not os.getenv('MODEL_HOST_URL') or not os.getenv('MODEL_HOST_TOKEN') or
        (runner.enhancement_policy.hyde_enabled or runner.enhancement_policy.decomposition_enabled) or runner.expansion_policy.enabled or
        runner.source_prerequisites.enabled or runner.retrieval_combination.enabled or runner.evidence_attribution.enabled or
        row['input_product_snapshot']['product_ids'] != [m['scope']['product_id']] or
        runner._history(runner.user(row),row) or row.get('support_snapshot')):
        deny('演示策略、历史或本地调用profile漂移。')
    repo=gateway.repo(row['kb_id'])
    actual=sorted((r['document_id'],r['active_revision_id']) for r in repo.get_active_revisions())
    expected=sorted((r['document_id'],r['revision_id']) for r in m['sources'])
    if actual != expected:
        deny('演示活动修订漂移。')
    for s in m['sources']:
        r=repo.get_revision(s['revision_id'])
        if r['original_sha256'] != s['original_sha256']:
            deny('演示原件hash漂移。')


class DemoLedger:
    def __init__(self, db, contract):
        from .output_contract import parse_contract
        self.policy=parse_contract(contract); self.manifest=require(self.policy)
        control=db.client[self.policy.control_database]
        self.rows,self.inputs,self.observations=control.m7_demo_accounts,control.m7_demo_inputs,control.m7_demo_observations
        self.inputs.create_index('run_id',unique=True)
        self.sha=fingerprint(self.policy.model_dump(mode='json'))
        initial=dict(contract_sha256=self.sha,version=0,wave=0,halt=False,pending={},settled={},
            reserved_input=0,reserved_output=0,known_input=0,known_output=0,input_tokens=None,output_tokens=None,
            streams_reserved=0,unknown_windows=[],failures=[],http_requests=None,cost=None)
        try:self.rows.update_one({'_id':BATCH},{'$setOnInsert':initial},upsert=True)
        except DuplicateKeyError:pass
        self.read()

    def read(self):
        r=self.rows.find_one({'_id':BATCH})
        if r is None or r['contract_sha256']!=self.sha:deny()
        return r

    def cas(self, r, fields):
        ok=self.rows.update_one({'_id':BATCH,'version':r['version']},{'$set':fields,'$inc':{'version':1}})
        return bool(ok.matched_count)

    def require_open(self):
        r=self.read()
        if r['halt'] or r['unknown_windows']:deny()
        return r

    def persist_input(self,row,prompt,state):
        x=member_for(self.manifest,row)
        account=self.require_open()
        if x['slot'] in account['pending'] or x['slot'] in account['settled']:
            deny('已经预留或结算的槽禁止补签输入。')
        if not row.get('execution_token'):
            deny('调用前输入缺少当前正式租约。')
        body=dict(slot=x['slot'],run_id=row['run_id'],run_identity=row['identity'],
            execution_token=row.get('execution_token'),manifest_sha256=self.policy.manifest_sha256,
            prompt=prompt,prompt_utf8_sha256=hashlib.sha256(prompt.encode()).hexdigest(),
            docs=copy.deepcopy(state.get('prompt_used_docs')),references=copy.deepcopy(state.get('prompt_reference_map') or [
                dict(reference_number=i+1,chunk_uid=d['chunk_uid'],revision_id=d['revision_id'])
                for i,d in enumerate(state.get('prompt_used_docs') or [])]),
            budget=copy.deepcopy(state.get('prompt_budget')),contract_sha256=self.sha)
        body['sha256']=fingerprint(body)
        try:self.inputs.update_one({'run_id':row['run_id']},{'$setOnInsert':body},upsert=True)
        except DuplicateKeyError:pass
        if self.inputs.find_one({'run_id':row['run_id']},{'_id':0})!=body:deny('调用前输入冲突，不能补签。')

    def begin(self,run_id,run_identity,*,input_reservation=0,risk_context=None):
        require(self.policy)
        x=next((x for x in self.manifest['members'] if member_run_id(self.manifest,x)==run_id),None)
        saved=self.inputs.find_one({'run_id':run_id},{'_id':0})
        if (not x or not saved or saved['run_identity']!=run_identity or
            fingerprint({k:v for k,v in saved.items() if k!='sha256'})!=saved['sha256'] or
            type(input_reservation) is not int or not 0<input_reservation<=28416 or
            saved['budget']['input_tokens']!=input_reservation):deny()
        for _ in range(32):
            r=self.require_open();slot=x['slot']
            if (r['wave']!=x['wave'] or slot in r['pending'] or slot in r['settled'] or
                r['streams_reserved']>=8 or r['reserved_input']+input_reservation>227328 or
                r['reserved_output']+4096>32768):deny()
            pending=r['pending']|{slot:dict(run_id=run_id,identity=run_identity,input_reservation=input_reservation,input_sha256=saved['sha256'])}
            if self.cas(r,dict(pending=pending,streams_reserved=r['streams_reserved']+1,
                reserved_input=r['reserved_input']+input_reservation,reserved_output=r['reserved_output']+4096)):
                return self.read()
        deny()

    def settle(self,run_id,run_identity,usage,*,completed,observations=None,logical_calls=None,product_state=None,**unused):
        from .output_contract import usage_receipt
        receipt=usage_receipt(usage,observations=observations)|dict(run_id=run_id,identity=run_identity,
            completed=completed,logical_calls=logical_calls,product_state=product_state)
        slot=next((x['slot'] for x in self.manifest['members'] if member_run_id(self.manifest,x)==run_id),None)
        for _ in range(32):
            r=self.read()
            if slot in r['settled']:
                if r['settled'][slot]!=receipt:deny('同一次结算内容冲突。')
                return r
            pending=r['pending'].get(slot)
            if not pending or pending['run_id']!=run_id or pending['identity']!=run_identity:deny()
            saved=self.inputs.find_one({'run_id':run_id},{'_id':0})
            intact=bool(saved and saved.get('sha256')==pending['input_sha256'] and
                fingerprint({k:v for k,v in saved.items() if k!='sha256'})==saved['sha256'])
            p=product_state or {};good=(intact and completed and receipt['usage_validation']['valid'] and
                type(receipt['input_tokens']) is int and receipt['input_tokens']<=pending['input_reservation'] and
                type(receipt['output_tokens']) is int and receipt['output_tokens']<=4096 and
                logical_calls=={'invoke_started':0,'stream_started':1} and p.get('visible_body') is True and
                p.get('truncated') is False and p.get('finish_reason')=='stop' and not p.get('observed_reasoning') and
                receipt.get('reasoning_tokens') in (None,0))
            pending_new=dict(r['pending']);pending_new.pop(slot)
            known_input=r['known_input']+(receipt['input_tokens'] if type(receipt['input_tokens']) is int else 0)
            known_output=r['known_output']+(receipt['output_tokens'] if type(receipt['output_tokens']) is int else 0)
            unknown=list(r['unknown_windows'])
            if not receipt['usage_validation']['valid'] or not completed or not intact:unknown.append(slot)
            if self.cas(r,dict(pending=pending_new,settled=r['settled']|{slot:receipt},halt=r['halt'] or not good,
                failures=r['failures']+([] if good else [dict(run_id=run_id,reason='settlement_rejected',input_intact=intact,
                    reservation=pending)]),
                known_input=known_input,known_output=known_output,unknown_windows=unknown,
                input_tokens=known_input if not unknown else None,output_tokens=known_output if not unknown else None)):
                return self.read()
        deny()


    def fail(self,run_id,reason):
        for _ in range(32):
            r=self.read()
            if self.cas(r,dict(halt=True,failures=r['failures']+[{'run_id':run_id,'reason':reason}])):return
        deny()

    def observation(self,run_id,state,telemetry):
        body={k:copy.deepcopy(state.get(k)) for k in ('answer_raw_text','answer_usage_observations',
            'answer_mode_observations','answer_observed_finishes','answer_finish_reason','output_truncated')}
        body['telemetry']=telemetry
        self.observations.update_one({'_id':run_id},{'$setOnInsert':body},upsert=True)

    def advance(self,wave):
        for _ in range(32):
            r=self.require_open()
            required=[x['slot'] for x in self.manifest['members'] if x['wave']==r['wave']]
            if wave!=r['wave']+1 or r['pending'] or any(s not in r['settled'] for s in required):deny()
            if self.cas(r,dict(wave=wave)):return
        deny()


def open_client(policy,run_id):
    import httpx
    from app.conf.lm_config import lm_config
    from .diagnostic_usage import preserving_chat_class
    root=Path(os.environ['M7_DEMO_EVIDENCE_DIR'])
    root.mkdir(parents=True,exist_ok=True)
    def request_hook(request):
        # 不落URL、Authorization或其他headers；仅封存实际ChatCompletions正文。
        with (root/(run_id+'-wire.json')).open('xb') as f:
            f.write(request.content)
    def response_hook(response):
        underlying=response.stream
        class RecordedStream(httpx.SyncByteStream):
            def __iter__(self):
                with (root/(run_id+'-raw.sse')).open('xb') as f:
                    for chunk in underlying:
                        f.write(chunk);f.flush()
                        yield chunk
            def close(self):
                underlying.close()
        response.stream=RecordedStream()
    http=httpx.Client(timeout=120,follow_redirects=False,event_hooks={'request':[request_hook],'response':[response_hook]})
    try:
        client=preserving_chat_class()(model=policy.model,base_url=lm_config.base_url,api_key=lm_config.api_key,
            temperature=.1,n=1,stream_usage=True,max_retries=0,timeout=120,http_client=http,
            extra_body={'enable_thinking':False})
        return client,http
    except BaseException:
        http.close()
        raise
