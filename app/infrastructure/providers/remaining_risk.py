"""封存剩余清单的限定风险准入；两控制库共享一个CAS账户，逐题来源检查后才放行下一题。"""
import copy
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from pydantic import Field
from pymongo.errors import DuplicateKeyError
from app.api.errors import APIError
from app.answering.reviewed_subjects import evidence_bytes
from app.knowledge.repository import fingerprint
from .product_risk import SingleProductAdmission, exclusive, code_version, open_client

ROOT = Path(__file__).resolve().parents[3]
VERSION = 'diagnostic_remaining_manifest_r1'
BATCH = 'm6-remaining-diagnostic-r1'
ACCOUNT_COLLECTION = 'diagnostic_remaining_accounts'
AUTHORIZED_GIT = dict(commit='e54043f2e0d247d269785b3eb34fcf537a2c461a',
    path='docs/development/reviews/M6-remaining-diagnostic-authorization-r1.json',
    sha256='1ec3415c25a2deaee7f143a8ce77d9aa9400a41247ac51e1780d14f7dab17acd')


class RemainingAdmission(SingleProductAdmission):
    member_slot: str = Field(pattern=r'^[a-zA-Z0-9_-]{1,128}$')


def local(path):
    p = (ROOT/path).resolve()
    if not p.is_relative_to(ROOT.resolve()) or 'private-identity' in p.parts:
        raise ValueError('剩余清单来源路径越界')
    return p


def read(path):return json.loads(Path(path).read_text('utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.now(timezone.utc).isoformat()
def batch_dir():return local('output/m6-authorized-products/'+BATCH)
def slot_dir(policy):return batch_dir()/'members'/policy.admission.member_slot


def seal_stop(evidence):
    path=batch_dir()/'halt.json';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if read(path)!=evidence:raise ValueError('首停止证据不可覆盖')
    else:
        try:exclusive(path,evidence)
        except FileExistsError:
            if read(path)!=evidence:raise ValueError('并发停止证据冲突')


def prior_receipt():
    from .product_risk import prior_receipt as single_prior
    old = single_prior()
    directory = local('output/m6-authorized-products/m6-05a-product-canary-r1')
    started, settled = read(directory/'started.json'), read(directory/'settled.json')
    receipt = settled['receipt']
    if (not receipt['completed'] or not receipt['usage_validation']['valid'] or
        any(started[k] != receipt[k] for k in ('run_id','run_identity')) or
        settled['manifest_sha256'] != started['manifest_sha256'] or
        (receipt['input_tokens'],receipt['output_tokens']) != (5165,1702)):
        raise ValueError('已关闭canary结算来源不完整，不重置前值')
    value = dict(input_tokens=old['input_tokens']+receipt['input_tokens'],
        output_tokens=old['output_tokens']+receipt['output_tokens'],
        sources=dict(six_and_probe=old,canary_started_sha256=sha(directory/'started.json'),
                     canary_settled_sha256=sha(directory/'settled.json')))
    return value | dict(sha256=fingerprint(value))


def sources(policy):
    if policy.admission.authorization.model_dump(mode='json') != AUTHORIZED_GIT:
        raise ValueError('剩余清单必须消费本包封存Git授权')
    auth = json.loads(evidence_bytes(AUTHORIZED_GIT))
    if (auth.get('kind') != 'coordinator_scoped_remaining_diagnostic_risk_authorization' or
        auth.get('admission_version') != VERSION or auth.get('fixed_batch_slot') != BATCH or
        auth['risk']['gateway_capability_status'] != 'unknown' or
        auth['risk']['coordinator_accepts_unknown_paid_upper_bound_only_for_fixed_remaining_manifest'] is not True):
        raise ValueError('剩余清单授权内容不适用')
    matches = [m for m in auth['members'] if m['fixed_slot'] == policy.admission.member_slot]
    if len(matches) != 1:raise ValueError('成员不在固定授权清单')
    member = matches[0]
    if (sha(local(auth['original_master_path'])) != auth['original_master_file_sha256'] or
        sha(local(auth['original_execution_manifest_path'])) != auth['original_execution_manifest_sha256'] or
        sha(local(member['source_input_path'])) != member['source_input_file_sha256']):
        raise ValueError('原主清单或成员输入来源漂移')
    anchor = read(local(member['source_input_path']))
    if member['expected_generation']:
        if hashlib.sha256(anchor['result']['prompt'].encode()).hexdigest() != member['prompt_utf8_sha256']:
            raise ValueError('成员prompt正文漂移')
    elif fingerprint(anchor['result']) != member['clarification_result_sha256']:
        raise ValueError('零生成澄清来源漂移')
    parent = next(p for p in read(local(auth['original_master_path']))['version_sources'] if p['version']==member['version'])
    runtime, budget, prior = auth['runtime'], auth['budget'], prior_receipt()
    expected = dict(status='unknown',semantics='unknown',evidence=None,n=runtime['n'],model=runtime['model'],
        endpoint_sha256=runtime['endpoint_sha256'],client_versions=runtime['client_versions'],limit_field=runtime['limit_field'],
        thinking=None,reasoning_budget=None,per_request_total_output_tokens=runtime['requested_total_output_tokens'],
        ledger_id=BATCH,prior_input_tokens=prior['input_tokens'],prior_output_tokens=prior['output_tokens'],
        prior_source_sha256=prior['sha256'],max_total_input_tokens=budget['max_total_diagnostic_input_tokens'],
        max_total_output_tokens=budget['max_total_diagnostic_output_tokens'])
    if (any(getattr(policy,k)!=v for k,v in expected.items()) or
        prior['input_tokens']!=budget['prior_diagnostic_input_tokens'] or prior['output_tokens']!=budget['prior_diagnostic_output_tokens']):
        raise ValueError('剩余清单profile、共享预算或历史前值漂移')
    return auth, member, anchor, parent


def config_subject(config):
    value=copy.deepcopy(config)
    value['parameters']['answer_budget']['output_contract']['admission'].pop('manifest_sha256')
    return value


def authorized_inputs(auth,member,*,profile=None):
    """输入直接取原完整题集；首次冻结也不能用同题号改写问题或历史。"""
    h=profile or sys.modules[__name__]
    directory=h.local(auth['original_master_path']).parent/'catalog'
    dataset=directory/('version-'+str(member['version'])+'.jsonl')
    manifest=directory/('version-'+str(member['version'])+'-manifest.json')
    if sha(dataset)!=member['dataset_sha256'] or sha(manifest)!=member['split_manifest_sha256']:
        raise ValueError('原完整题集或split身份漂移')
    rows=[json.loads(line) for line in dataset.read_text('utf-8').splitlines() if line.strip()]
    if (len(rows)!=auth['full_dataset_rows_per_version'] or
        sum(q['split']=='dev' for q in rows)!=auth['dev_rows_per_version'] or
        sum(q['split']=='heldout' for q in rows)!=auth['heldout_rows_per_version']):
        raise ValueError('原题集不完整，不缩题集领取额度')
    question=next(q for q in rows if q['id']==member['question_id'])
    entry=next(e for e in read(h.local(auth['original_execution_manifest_path']))['entries']
        if e['version']==member['version'] and e['ordinal']==member['ordinal'])
    if entry['question_id']!=question['id'] or fingerprint(question)!=entry['source']['question_sha256'] or question['split']!='dev':
        raise ValueError('原请求、原序号及题目身份不一致')
    return {k:question[k] for k in ('id','question','product_names','history')}


def build_member(config,question,control_database,*,profile=None):
    from .output_contract import parse_contract
    policy=parse_contract(config['parameters']['answer_budget']['output_contract'])
    h=profile or sys.modules[__name__]
    auth, member, anchor, parent = h.sources(policy)
    actual, expected = copy.deepcopy(config),copy.deepcopy(anchor['new_config'])
    for value in (actual,expected):
        value.pop('experiment_id',None);value.pop('question_ids',None)
        value['versions'].pop('code',None)
        value['parameters']['answer_budget'].pop('output_contract',None)
        value['parameters']['answer_budget'].pop('output_token_field',None)
    expected_control_database = parent['control_database']
    control_database_for = getattr(h, 'execution_control_database', None)
    if control_database_for is not None:
        expected_control_database = control_database_for(auth, parent)
    if (actual!=expected or control_database!=expected_control_database or
        any(config['target'][k]!=parent[k] for k in ('owner_id','kb_id')) or
        config['question_ids']!=[member['question_id']] or question['id']!=member['question_id'] or
        config['experiment_id']!=member['fixed_slot'] or config['versions']['code']!=h.code_version() or
        config['dataset_sha256']!=member['dataset_sha256'] or config['split_manifest_sha256']!=member['split_manifest_sha256']):
        raise ValueError('成员配置、控制库、题集、主体或源码超出授权')
    budget=config['parameters']['answer_budget'];limits=auth['budget']
    if any(budget[k]!=limits[v] for k,v in [('context_window','context_window'),('output_tokens','output_tokens_requested'),
        ('reserve_tokens','reserve_tokens'),('max_chars','max_chars')]) or budget['output_token_field']!=auth['runtime']['limit_field']:
        raise ValueError('成员预算变化')
    inputs={k:question[k] for k in ('id','question','product_names','history')}
    if inputs!=h.authorized_inputs(auth,member):raise ValueError('初次冻结的问题输入不匹配封存完整题集')
    return dict(member=member,control_database=control_database,config_subject=config_subject(config),
        question=inputs,input_sha256=fingerprint(inputs),parent_request_key=anchor.get('new_request_key'),
        source_result_sha256=fingerprint(anchor['result']))


def build_manifest(items, *, artifacts=None):
    entries=[build_member(config,q,control) for config,q,control in items]
    from .output_contract import parse_contract
    policy=parse_contract(items[0][0]['parameters']['answer_budget']['output_contract'])
    auth,_,_,_=sources(policy)
    by_slot={e['member']['fixed_slot']:e for e in entries}
    if len(by_slot)!=len(auth['members']) or set(by_slot)!=set(auth['dispatch_order']):
        raise ValueError('执行清单必须包含全部且仅含授权成员，不缩清单')
    parents=read(local(auth['original_master_path']))['version_sources']
    shared=min(parents,key=lambda p:p['version'])['control_database']
    return dict(version=VERSION,batch_slot=BATCH,authorization=AUTHORIZED_GIT,prior_receipt=prior_receipt(),
        shared_control_database=shared,dispatch_order=auth['dispatch_order'],
        entries=[by_slot[s] for s in auth['dispatch_order']],artifacts=artifacts or {})


def prepare_manifest(manifest,*,profile=None):
    h=profile or sys.modules[__name__]
    path=h.batch_dir()/'planned.json';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if read(path)!=manifest:raise ValueError('固定批次计划不可覆盖或换目录重领')
    else:
        try:h.exclusive(path,manifest)
        except FileExistsError:
            if read(path)!=manifest:raise ValueError('固定批次并发计划冲突')
    for entry in manifest['entries']:
        directory=h.batch_dir()/'members'/entry['member']['fixed_slot'];directory.mkdir(parents=True,exist_ok=True)
        p=directory/'planned.json';value=dict(manifest_sha256=fingerprint(manifest),entry=entry)
        if p.exists():
            if read(p)!=value:raise ValueError('成员计划不一致')
        else:
            try:h.exclusive(p,value)
            except FileExistsError:
                if read(p)!=value:raise ValueError('成员并发计划冲突')


def require(policy,*,profile=None):
    h=profile or sys.modules[__name__]
    h.sources(policy)
    planned=read(h.batch_dir()/'planned.json')
    if fingerprint(planned)!=policy.admission.manifest_sha256 or planned['authorization']!=h.AUTHORIZED_GIT:
        raise ValueError('缺少一致的固定批次冻结')
    if read(h.slot_dir(policy)/'planned.json')!=dict(manifest_sha256=fingerprint(planned),entry=entry_for(policy,planned)):
        raise ValueError('成员固定槽计划不一致')
    return planned


def entry_for(policy,manifest):
    return next(e for e in manifest['entries'] if e['member']['fixed_slot']==policy.admission.member_slot)


def validate_config(config,control_database,*,question=None,profile=None):
    from .output_contract import parse_contract
    h=profile or sys.modules[__name__]
    policy=parse_contract(config['parameters']['answer_budget']['output_contract']);planned=h.require(policy)
    entry=entry_for(policy,planned)
    if h.build_member(config,question if question is not None else entry['question'],control_database)!=entry:
        raise ValueError('正式请求不匹配固定成员执行身份')
    return planned


def validate_prompt(policy,prompt,state,*,profile=None):
    h=profile or sys.modules[__name__]
    auth,member,anchor,_=h.sources(policy)
    if not member['expected_generation']:raise ValueError('零生成成员不得进入答案模型')
    expected=anchor['result']
    if (prompt!=expected['prompt'] or state['prompt_used_docs']!=expected['context'] or
        state.get('prompt_reference_map',[])!=expected['prompt_reference_map'] or state.get('evidence_groups',[])!=expected['groups'] or
        {k:v for k,v in state['prompt_budget'].items() if k!='policy'}!={k:v for k,v in expected['budget'].items() if k!='policy'} or
        state['prompt_budget']['input_limit']!=auth['budget']['single_input_limit']):
        raise ValueError('成员实际prompt、context、引用、分组或预算漂移')


def validate_runtime(policy,run,context,db,*,profile=None):
    h=profile or sys.modules[__name__]
    if not context:raise ValueError('清单准入只能沿正式job消费')
    h.validate_config(context['config'],context['control_database'],question=context['question'])
    from app.evaluation.execution_links import validate_execution
    from app.evaluation.execution_identity import run_input
    validate_execution(context['control_db'],context['execution'],context['config'])
    link=db.evaluation_execution_links.find_one(dict(experiment_id=context['execution']['experiment_id'],
        attempt=context['execution']['attempt'],run_id=run['run_id'],mode='execution'))
    if (not link or link['control_database']!=context['control_database'] or link['target_database']!=db.name or
        link['question_id']!=context['question']['id'] or link['output_contract']!=policy.model_dump(mode='json') or
        link['run_input_sha256']!=fingerprint(run_input(run,db))):
        raise ValueError('清单正式Run执行关联缺失或漂移')


def validate_client(policy,client,*,profile=None):
    from .output_contract import unwrap_client
    h=profile or sys.modules[__name__]
    client=unwrap_client(client);runtime=h.sources(policy)[0]['runtime']
    if (client.temperature!=runtime['temperature'] or float(client.request_timeout)!=runtime['timeout_seconds'] or
        client.stream_usage is not True or client.root_client._client.follow_redirects is not False):
        raise ValueError('清单实际客户端profile不一致')
    effective=client._get_request_payload('',n=1,extra_body={policy.limit_field:4096})
    if set(effective)-{'model','messages','temperature','n','stream','extra_body','stream_options'}:
        raise ValueError('清单存在未授权wire参数')


class RemainingLedger:
    """同一个Mongo文档原子预留成员、在途和预算；跨库客户端始终寻址封存的共享控制库。"""
    def __init__(self,db,contract,*,profile=None):
        from .output_contract import parse_contract
        self.handler=profile or sys.modules[__name__]
        self.policy=parse_contract(contract);self.manifest=self.handler.require(self.policy)
        self.db=db;self.entry=entry_for(self.policy,self.manifest);self.slot=self.policy.admission.member_slot
        if db.name!=self.entry['config_subject']['target']['database']:raise ValueError('目标库不能用于重领清单额度')
        self.rows=db.client[self.manifest['shared_control_database']][self.handler.ACCOUNT_COLLECTION]
        self.key=fingerprint([self.handler.VERSION,self.handler.BATCH]);self.sha=fingerprint(self.manifest)

    def _read(self):
        row=self.rows.find_one({'_id':self.key})
        if not row or row.get('manifest_sha256')!=self.sha:raise APIError(409,'output_account_identity_conflict','共享清单账本身份不一致。')
        return row

    def _cas(self,prior,values):
        if not self.rows.update_one({'_id':self.key,'version':prior['version']},{'$set':values,'$inc':{'version':1}}).matched_count:
            raise APIError(409,'output_account_busy','共享清单并发冲突，停止派发。')

    def begin(self,run_id,run_identity,*,input_reservation=0,risk_context=None,zero_generation=False):
        context=risk_context
        if not context:raise ValueError('缺少正式清单执行上下文')
        self.handler.validate_config(context['config'],context['control_database'],question=context['question'])
        run=self.db.runs.find_one({'run_id':run_id})
        if not run or run.get('identity')!=run_identity:raise ValueError('预留Run完整身份不一致')
        self.handler.validate_runtime(self.policy,run,context,self.db)
        member=self.entry['member'];expected=member['expected_generation']
        if zero_generation==expected or type(input_reservation) is not int or input_reservation<0:
            raise ValueError('成员生成类型或输入预留不一致')
        if expected:
            anchor=self.handler.sources(self.policy)[2]
            if input_reservation!=anchor['result']['budget']['input_tokens']:raise ValueError('输入预留必须匹配实际保守预算')
        elif input_reservation!=0:raise ValueError('澄清生成预算必须为0')
        row=dict(manifest_sha256=self.sha,version=0,state='open',pending=None,settled={},reviews={},cursor=0,
            prior_input_tokens=self.policy.prior_input_tokens,prior_output_tokens=self.policy.prior_output_tokens,
            known_new_input_tokens=0,known_new_output_tokens=0,new_input_tokens=0,new_output_tokens=0,
            logical_reservations=0,job_reservations=0,unknown_windows=[],exact_http_requests=None,exact_cost=None)
        try:self.rows.update_one({'_id':self.key},{'$setOnInsert':row},upsert=True)
        except DuplicateKeyError:pass
        saved=self._read();order=self.manifest['dispatch_order'];out_reservation=4096 if expected else 0
        if (saved['state']!='open' or saved['pending'] is not None or self.slot in saved['settled'] or
            saved['cursor']>=len(order) or order[saved['cursor']]!=self.slot or
            saved['prior_input_tokens']+saved['known_new_input_tokens']+input_reservation>self.policy.max_total_input_tokens or
            saved['prior_output_tokens']+saved['known_new_output_tokens']+out_reservation>self.policy.max_total_output_tokens or
            (self.handler.batch_dir()/'halt.json').exists() or
            (self.handler.slot_dir(self.policy)/'started.json').exists() or (self.handler.slot_dir(self.policy)/'settled.json').exists()):
            raise APIError(409,'output_account_blocked','清单有在途、停止、重复、乱序或预算不足，禁止派发。')
        pending=dict(slot=self.slot,run_id=run_id,run_identity=run_identity,input_reservation=input_reservation,
            output_reservation=out_reservation,expected_generation=expected,at=now(),
            contract_sha256=fingerprint(self.policy.model_dump(mode='json')),control_database=context['control_database'],
            target_database=self.db.name,config_sha256=fingerprint(context['config']),
            execution={k:context['execution'][k] for k in ('experiment_id','attempt','config_sha256')})
        self._cas(saved,dict(state='pending',pending=pending,new_input_tokens=None,new_output_tokens=None,
            logical_reservations=saved['logical_reservations']+int(expected),job_reservations=saved['job_reservations']+1))
        if (self.handler.batch_dir()/'halt.json').exists():
            self._cas(self._read(),dict(state='blocked'))
            raise APIError(409,'output_account_blocked','批次已封存停止，保留本次预留，不联网。')
        # CAS后磁盘失败仍留pending，不能重领；两个位置都确认完成后才允许联网。
        self.handler.exclusive(self.handler.slot_dir(self.policy)/'started.json',dict(manifest_sha256=self.sha,**pending))

    def _seal(self,receipt):
        started=read(self.handler.slot_dir(self.policy)/'started.json')
        if any(started[k]!=receipt[k] for k in ('run_id','run_identity')):raise ValueError('成员结算Run漂移')
        value=dict(manifest_sha256=self.sha,receipt=receipt);path=self.handler.slot_dir(self.policy)/'settled.json'
        if path.exists():
            if read(path)!=value:raise ValueError('成员结算内容改变')
        else:
            try:self.handler.exclusive(path,value)
            except FileExistsError:
                if read(path)!=value:raise ValueError('成员并发结算内容改变')

    def settle(self,run_id,run_identity,usage,*,completed,reasoning=None,logical_calls=None,observations=None,product_state=None):
        from .output_contract import usage_receipt
        receipt=usage_receipt(usage,observations=observations)|dict(run_id=run_id,run_identity=run_identity,
            completed=bool(completed),product_state=product_state,
            logical_provider_calls={k:logical_calls.get(k) for k in ('invoke_started','stream_started')} if isinstance(logical_calls,dict) else None)
        return self._settle(receipt)

    def _settle(self,receipt):
        saved=self._read()
        if self.slot in saved['settled']:
            if saved['settled'][self.slot]!=receipt:raise APIError(409,'output_settlement_conflict','成员结算内容改变。')
            self._seal(receipt);return saved
        pending=saved['pending']
        if not pending or any(pending[k]!=v for k,v in dict(slot=self.slot,run_id=receipt['run_id'],run_identity=receipt['run_identity']).items()):
            raise APIError(409,'output_settlement_conflict','成员没有匹配的在途预留。')
        zero=not pending['expected_generation']
        known=receipt['input_tokens'] is not None and receipt['output_tokens'] is not None
        ni=saved['known_new_input_tokens']+(receipt['input_tokens'] or 0);no=saved['known_new_output_tokens']+(receipt['output_tokens'] or 0)
        product=receipt.get('product_state') or {}
        good=(known and receipt['completed'] and receipt['usage_validation']['valid'] and receipt['output_tokens']<=4096 and
            saved['prior_input_tokens']+ni<=self.policy.max_total_input_tokens and saved['prior_output_tokens']+no<=self.policy.max_total_output_tokens and
            self.product_valid(receipt,zero))
        windows=list(saved['unknown_windows'])
        if not known or not receipt['completed'] or not receipt['usage_validation']['valid']:
            windows.append(dict(slot=self.slot,reason='invalid_usage_or_incomplete',run_id=receipt['run_id'],reported=receipt['usage_validation']['reported']))
        # 好结果也等来源诊断；没有审后决定不能派发下一题。
        self._cas(saved,dict(state='awaiting_review' if good else 'blocked',pending=None,
            settled=saved['settled']|{self.slot:receipt},known_new_input_tokens=ni,known_new_output_tokens=no,
            new_input_tokens=ni if known and receipt['completed'] else None,new_output_tokens=no if known and receipt['completed'] else None,
            unknown_windows=windows))
        self._seal(receipt)
        return self._read()

    def product_valid(self,receipt,zero):
        product=receipt.get('product_state') or {}
        return (product.get('clarification_valid') is True if zero else
            product.get('visible_body') is True and product.get('truncated') is False and product.get('finish_reason')=='stop')

    def settle_clarification(self,run,result):
        expected=self.handler.sources(self.policy)[2]['result']
        wanted=expected.get('candidates',[])
        actual=result.get('candidates',[])
        valid=(run['state']=='awaiting_input' and not result.get('answer') and
            {(x['product_id'],x['model']) for x in actual}=={(x['product_id'],x['model']) for x in wanted})
        receipt=dict(run_id=run['run_id'],run_identity=run['identity'],completed=valid,input_tokens=0,output_tokens=0,
            reasoning_tokens=0,visible_tokens=None,http_requests=None,cost=None,logical_provider_calls=dict(invoke_started=0,stream_started=0),
            usage_validation=dict(valid=True,reported=dict(input=0,output=0,reasoning=0)),product_state=dict(clarification_valid=valid))
        return self._settle(receipt)

    def review(self,*,accepted,evidence):
        if type(accepted) is not bool or not isinstance(evidence,dict) or not evidence or not evidence.get('source_checked'):
            raise ValueError('来源诊断必须显式留下输入、证据与输出决定')
        saved=self._read();value=dict(accepted=accepted,evidence=evidence)
        if self.slot in saved['reviews']:
            if saved['reviews'][self.slot]!=value:raise ValueError('已封存来源诊断不能改变')
            return saved
        if self.slot not in saved['settled'] or saved['pending'] is not None:raise ValueError('先结算再诊断')
        # 必须先有完整磁盘结算；DB先提交后崩溃只能恢复同等结算，不能误派发。
        self._seal(saved['settled'][self.slot])
        if accepted and saved['state']!='awaiting_review':raise ValueError('坏usage或未知窗口不能由人工诊断放行')
        path=self.handler.slot_dir(self.policy)/'source-review.json'
        if path.exists():
            if read(path)!=value:raise ValueError('磁盘来源诊断冲突')
        else:self.handler.exclusive(path,value)
        self._cas(saved,dict(state='open' if accepted else 'blocked',reviews=saved['reviews']|{self.slot:value},
            cursor=saved['cursor']+int(accepted)))
        return self._read()

    def require_open(self):
        saved=self._read()
        if (saved['state'] not in ('open','awaiting_review') or saved['unknown_windows'] or
            self.slot not in saved['settled']):
            raise APIError(409,'output_account_blocked','清单usage、完成性或正文异常，全批暂停。')
        return saved

    def halt(self,evidence):
        """前置或来源失败只增加停止证据；不清pending、不返还额度。"""
        if not isinstance(evidence,dict) or not evidence:raise ValueError('停止必须保留具体证据')
        self.handler.seal_stop(evidence)
        if self.rows.find_one({'_id':self.key}) is None:return None
        saved=self._read()
        if saved.get('halt'):
            if saved['halt']!=evidence:raise ValueError('首停止证据不可改变')
            return saved
        self._cas(saved,dict(state='blocked',halt=evidence))
        return self._read()
