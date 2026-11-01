"""仅本包封存清单允许显式false；旧批保持blocked，复用已审CAS结算核心。"""
import copy
import hashlib
import json
import sys
from pathlib import Path
from . import remaining_risk as base
from .product_risk import exclusive,code_version
from app.answering.reviewed_subjects import evidence_bytes
from app.knowledge.repository import fingerprint

ROOT=Path(__file__).resolve().parents[3]
VERSION='diagnostic_nonthinking_manifest_r1'
BATCH='m6-nonthinking-diagnostic-r1'
ACCOUNT_COLLECTION='diagnostic_nonthinking_accounts'
AUTHORIZED_GIT=dict(commit='0e61ada4795f495b31593ab56e9be8b857968a58',path='docs/development/reviews/M6-nonthinking-diagnostic-authorization-r1.json',sha256='eb49a82f33415255a122318a82926ea6fec62e3b41290e7e3027d2fc8821388b')
RemainingAdmission=base.RemainingAdmission
read=base.read
sha=base.sha
now=base.now
entry_for=base.entry_for
config_subject=base.config_subject

def local(path):
    p=(ROOT/path).resolve()
    if not p.is_relative_to(ROOT.resolve()) or 'private-identity' in p.parts:raise ValueError('非思考清单来源路径越界')
    return p

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
    auth=json.loads(evidence_bytes(AUTHORIZED_GIT))
    old=base.prior_receipt()
    directory=local('output/m6-authorized-products/'+auth['previous_batch'])
    account_path=local(auth['previous_account_snapshot_path'])
    if (auth['previous_batch']!=base.BATCH or sha(directory/'halt.json')!=auth['previous_halt_sha256'] or
        sha(account_path)!=auth['previous_account_snapshot_sha256'] or fingerprint(read(directory/'planned.json'))!=auth['previous_manifest_sha256']):
        raise ValueError('旧blocked批次或前值来源漂移')
    account=read(account_path)
    if account['state']!='blocked' or account['pending'] is not None or account['unknown_windows'] or account['halt']!=read(directory/'halt.json'):
        raise ValueError('旧账户必须已知结算并保持blocked')
    tokens=[0,0];files={}
    for slot,receipt in account['settled'].items():
        sd=directory/'members'/slot;started=read(sd/'started.json');settled=read(sd/'settled.json')
        if (settled['receipt']!=receipt or any(started[k]!=receipt[k] for k in ('run_id','run_identity')) or
            not receipt['completed'] or not receipt['usage_validation']['valid']):raise ValueError('旧成员计量来源不完整')
        for i,key in enumerate(('input_tokens','output_tokens')):
            if type(receipt[key]) is not int or receipt[key]<0:raise ValueError('旧计量非法')
            tokens[i]+=receipt[key]
        files[slot]={name:sha(sd/(name+'.json')) for name in ('started','settled','source-review')}
    if tokens!=[account['known_new_input_tokens'],account['known_new_output_tokens']]:raise ValueError('旧累计与分题结算不符')
    value=dict(input_tokens=old['input_tokens']+tokens[0],output_tokens=old['output_tokens']+tokens[1],sources=dict(prior=old,account_sha256=sha(account_path),halt_sha256=sha(directory/'halt.json'),members=files))
    if (value['input_tokens'],value['output_tokens'])!=(37541,28633):raise ValueError('前值不匹配封存裁定')
    return value|dict(sha256=fingerprint(value))

def sources(policy):
    if policy.admission.authorization.model_dump(mode='json')!=AUTHORIZED_GIT:raise ValueError('须使用本包封存Git授权')
    auth=json.loads(evidence_bytes(AUTHORIZED_GIT))
    if (auth.get('kind')!='coordinator_scoped_nonthinking_diagnostic_authorization' or auth['admission_version']!=VERSION or
        auth['fixed_batch_slot']!=BATCH or auth['single_experimental_change']!='effective_wire_enable_thinking_false' or
        auth['risk']['gateway_capability_status']!='unknown' or auth['risk']['coordinator_accepts_unknown_paid_upper_bound_only_for_this_fixed_manifest'] is not True):
        raise ValueError('非思考清单授权不适用')
    matches=[m for m in auth['members'] if m['fixed_slot']==policy.admission.member_slot]
    if len(matches)!=1:raise ValueError('非本包成员')
    member=matches[0]
    if (not member['expected_generation'] or sha(local(auth['original_master_path']))!=auth['original_master_file_sha256'] or
        sha(local(auth['original_execution_manifest_path']))!=auth['original_execution_manifest_sha256'] or
        sha(local(member['source_input_path']))!=member['source_input_file_sha256']):raise ValueError('清单或输入来源漂移')
    anchor=read(local(member['source_input_path']))
    if hashlib.sha256(anchor['result']['prompt'].encode()).hexdigest()!=member['prompt_utf8_sha256']:raise ValueError('prompt漂移')
    parent=next(p for p in read(local(auth['original_master_path']))['version_sources'] if p['version']==member['version'])
    prior=prior_receipt();runtime=auth['runtime'];budget=auth['budget']
    expected=dict(status='unknown',semantics='unknown',evidence=None,n=runtime['n'],model=runtime['model'],endpoint_sha256=runtime['endpoint_sha256'],client_versions=runtime['client_versions'],limit_field=runtime['limit_field'],thinking=False,reasoning_budget=None,per_request_total_output_tokens=4096,ledger_id=BATCH,prior_input_tokens=prior['input_tokens'],prior_output_tokens=prior['output_tokens'],prior_source_sha256=prior['sha256'],max_total_input_tokens=budget['max_total_diagnostic_input_tokens'],max_total_output_tokens=budget['max_total_diagnostic_output_tokens'])
    if any(getattr(policy,k)!=v for k,v in expected.items()) or policy.thinking is not False:raise ValueError('模式／profile／共享前值不符')
    return auth,member,anchor,parent

def authorized_inputs(auth,member):return base.authorized_inputs(auth,member,profile=sys.modules[__name__])
def build_member(config,question,control_database):return base.build_member(config,question,control_database,profile=sys.modules[__name__])

def build_manifest(items,*,artifacts=None):
    from .output_contract import parse_contract
    entries=[build_member(c,q,d) for c,q,d in items]
    auth=sources(parse_contract(items[0][0]['parameters']['answer_budget']['output_contract']))[0]
    by_slot={e['member']['fixed_slot']:e for e in entries}
    if len(by_slot)!=len(auth['members']) or set(by_slot)!=set(auth['dispatch_order']):raise ValueError('须冻结全部且仅45成员')
    parents=read(local(auth['original_master_path']))['version_sources']
    return dict(version=VERSION,batch_slot=BATCH,authorization=AUTHORIZED_GIT,prior_receipt=prior_receipt(),shared_control_database=min(parents,key=lambda p:p['version'])['control_database'],dispatch_order=auth['dispatch_order'],entries=[by_slot[s] for s in auth['dispatch_order']],artifacts=artifacts or {})

def prepare_manifest(manifest):return base.prepare_manifest(manifest,profile=sys.modules[__name__])
def require(policy):return base.require(policy,profile=sys.modules[__name__])
def validate_config(config,control_database,*,question=None):return base.validate_config(config,control_database,question=question,profile=sys.modules[__name__])
def validate_prompt(policy,prompt,state):return base.validate_prompt(policy,prompt,state,profile=sys.modules[__name__])
def validate_client(policy,client):return base.validate_client(policy,client,profile=sys.modules[__name__])

def validate_previous_account(policy,client):
    auth=sources(policy)[0];planned=read(local('output/m6-authorized-products/'+auth['previous_batch']+'/planned.json'))
    saved=read(local(auth['previous_account_snapshot_path']))
    actual=client[planned['shared_control_database']][base.ACCOUNT_COLLECTION].find_one({'_id':saved['_id']})
    if actual!=saved:raise ValueError('旧blocked账户现场与封存来源不符，禁止新调用')

def validate_runtime(policy,run,context,db):
    base.validate_runtime(policy,run,context,db,profile=sys.modules[__name__])
    validate_previous_account(policy,db.client)

def open_client(policy):
    client,http=base.open_client(policy)
    client.extra_body={'enable_thinking':False}
    return client,http

class NonthinkingLedger(base.RemainingLedger):
    def __init__(self,db,contract):super().__init__(db,contract,profile=sys.modules[__name__])

    def product_valid(self,receipt,zero):
        observations=receipt['usage_validation'].get('observations',[])
        positive=any(type(o['counts'].get('reasoning')) is int and o['counts']['reasoning']>0 for o in observations)
        return (not zero and super().product_valid(receipt,zero) and
            (receipt.get('product_state') or {}).get('observed_reasoning') is False and
            receipt['reasoning_tokens'] in (None,0) and not positive)
