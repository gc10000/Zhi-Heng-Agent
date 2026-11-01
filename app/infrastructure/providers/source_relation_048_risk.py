"""已审关系输入的固定048单次准入；复用非思考客户端及共享CAS，不解锁旧批。"""
import copy
import hashlib
import json
import sys
from pathlib import Path

from app.answering.reviewed_subjects import evidence_bytes
from app.knowledge.repository import fingerprint
from . import remaining_risk as base, nonthinking_risk as previous
from .product_risk import exclusive, code_version

ROOT=Path(__file__).resolve().parents[3]
VERSION='diagnostic_source_relation_048_v1'
BATCH='m6-source-relation-048-canary-r1'
SLOT='m6-sr048-r1-v1-support-v1-048'
QUESTION_ID='support-v1-048'
ACCOUNT_COLLECTION='diagnostic_source_relation_048_accounts'
AUTHORIZED_GIT=dict(commit='4cc94e61cf22e3c3339301440da8f1517e7ba9f5',
    path='docs/development/reviews/M6-source-relation-048-canary-authorization-r1.json',
    sha256='2ea1b4868be934979d3d62f1524b3df18aa0c72028760b8acf466c9be7a75129')
read=base.read
sha=base.sha
now=base.now
config_subject=base.config_subject
entry_for=base.entry_for


def local(path):
    p=(ROOT/path).resolve()
    if not p.is_relative_to(ROOT.resolve()) or 'private-identity' in p.parts:raise ValueError('单次来源路径越界')
    return p


def batch_dir():return local('output/m6-authorized-products/'+BATCH)
def slot_dir(policy):return batch_dir()/'members'/policy.admission.member_slot


def seal_stop(evidence):
    path=batch_dir()/'halt.json';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if read(path)!=evidence:raise ValueError('单次首停止证据不可改变')
    else:
        try:exclusive(path,evidence)
        except FileExistsError:
            if read(path)!=evidence:raise ValueError('单次并发停止冲突')


def prior_receipt():
    auth=json.loads(evidence_bytes(AUTHORIZED_GIT));old=previous.prior_receipt()
    directory=local('output/m6-authorized-products/'+auth['previous_batch'])
    account_path=local(auth['previous_account_snapshot_path']);settlement=local(auth['previous_settlement_source_path'])
    if (auth['previous_batch']!=previous.BATCH or sha(directory/'halt.json')!=auth['previous_halt_sha256'] or
        fingerprint(read(directory/'planned.json'))!=auth['previous_manifest_sha256'] or
        sha(account_path)!=auth['previous_account_snapshot_sha256'] or sha(settlement)!=auth['previous_settlement_source_sha256']):
        raise ValueError('旧非思考停止或计量来源漂移')
    saved=read(account_path)
    if (saved!=read(settlement)['account'] or saved['state']!='blocked' or saved['pending'] is not None or
        saved['unknown_windows'] or saved['halt']!=read(directory/'halt.json') or len(saved['settled'])!=2):
        raise ValueError('旧两槽必须已结算并保持blocked')
    tokens=[0,0];files={}
    for slot,receipt in saved['settled'].items():
        sd=directory/'members'/slot;started=read(sd/'started.json');settled=read(sd/'settled.json')
        if (settled['receipt']!=receipt or settled['manifest_sha256']!=started['manifest_sha256'] or
            any(started[k]!=receipt[k] for k in ('run_id','run_identity')) or not receipt['completed'] or not receipt['usage_validation']['valid']):
            raise ValueError('旧两流结算不完整')
        for i,k in enumerate(('input_tokens','output_tokens')):
            if type(receipt[k]) is not int or receipt[k]<0:raise ValueError('旧计量非法')
            tokens[i]+=receipt[k]
        files[slot]={n:sha(sd/(n+'.json')) for n in ('started','settled','source-review')}
    if tokens!=[9432,920] or tokens!=[saved['known_new_input_tokens'],saved['known_new_output_tokens']]:raise ValueError('旧两流累计不符')
    value=dict(input_tokens=old['input_tokens']+tokens[0],output_tokens=old['output_tokens']+tokens[1],
        sources=dict(prior=old,account_sha256=sha(account_path),halt_sha256=sha(directory/'halt.json'),settlement_sha256=sha(settlement),members=files))
    if (value['input_tokens'],value['output_tokens'])!=(46973,29553):raise ValueError('单次共享前值不符')
    return value|dict(sha256=fingerprint(value))


def sources(policy):
    if policy.admission.authorization.model_dump(mode='json')!=AUTHORIZED_GIT:raise ValueError('须消费本次封存Git授权')
    auth=json.loads(evidence_bytes(AUTHORIZED_GIT))
    if (auth.get('kind')!='coordinator_scoped_source_relation_048_single_authorization' or auth['admission_version']!=VERSION or
        auth['fixed_batch_slot']!=BATCH or len(auth['members'])!=1 or auth['dispatch_order']!=[SLOT] or
        auth['risk']['gateway_capability_status']!='unknown' or
        auth['risk']['coordinator_accepts_unknown_paid_upper_bound_only_for_this_fixed_single_stream'] is not True):
        raise ValueError('非本固定单成员授权')
    m=auth['members'][0]
    if (m['version'],m['ordinal'],m['question_id'],m['fixed_slot'],m['expected_generation'])!=(1,27,QUESTION_ID,SLOT,True) or policy.admission.member_slot!=SLOT:
        raise ValueError('仅允许版1固定048单成员')
    if (sha(local(auth['original_master_path']))!=auth['original_master_file_sha256'] or
        sha(local(auth['original_execution_manifest_path']))!=auth['original_execution_manifest_sha256'] or
        sha(local(m['source_input_path']))!=m['source_input_file_sha256'] or
        sha(local('app/answering/source_relations.py'))!=auth['reviewed_extractor_file_sha256']):raise ValueError('已审来源或角色实现漂移')
    anchor=read(local(m['source_input_path']))
    if (fingerprint(anchor['result'])!=m['source_result_sha256'] or fingerprint(anchor['new_config'])!=m['source_config_sha256'] or
        hashlib.sha256(anchor['result']['prompt'].encode()).hexdigest()!=m['prompt_utf8_sha256'] or
        anchor['new_config']['versions']['prompt']!=auth['prompt_version']):raise ValueError('锚配置或完整输入漂移')
    parent=next(p for p in read(local(auth['original_master_path']))['version_sources'] if p['version']==1)
    prior=prior_receipt();r=auth['runtime'];b=auth['budget']
    expected=dict(enabled=True,status='unknown',semantics='unknown',evidence=None,n=r['n'],model=r['model'],endpoint_sha256=r['endpoint_sha256'],
        client_versions=r['client_versions'],limit_field=r['limit_field'],thinking=False,reasoning_budget=None,per_request_total_output_tokens=4096,
        ledger_id=BATCH,prior_input_tokens=prior['input_tokens'],prior_output_tokens=prior['output_tokens'],prior_source_sha256=prior['sha256'],
        max_total_input_tokens=b['max_total_diagnostic_input_tokens'],max_total_output_tokens=b['max_total_diagnostic_output_tokens'])
    if (any(getattr(policy,k)!=v for k,v in expected.items()) or
        (prior['input_tokens'],prior['output_tokens'])!=(b['prior_diagnostic_input_tokens'],b['prior_diagnostic_output_tokens']) or
        any(b[k]!=1 for k in ('max_new_product_jobs','max_new_product_streams','max_attempts_per_member'))):raise ValueError('单次profile或预算漂移')
    return auth,m,anchor,parent


def authorized_inputs(auth,member):return base.authorized_inputs(auth,member,profile=sys.modules[__name__])


def build_member(config,question,control_database):
    from .output_contract import parse_contract
    anchor=sources(parse_contract(config['parameters']['answer_budget']['output_contract']))[2]
    a,b=copy.deepcopy(config),copy.deepcopy(anchor['new_config'])
    for v in (a,b):
        v.pop('experiment_id',None);v['versions'].pop('code',None)
        v['parameters']['answer_budget'].pop('output_contract',None);v['parameters']['answer_budget'].pop('output_token_field',None)
    if a!=b:raise ValueError('单次仅允许授权指定四处配置差异')
    return base.build_member(config,question,control_database,profile=sys.modules[__name__])


def build_manifest(items,*,artifacts=None):
    if len(items)!=1:raise ValueError('本批仅一个成员')
    entry=build_member(*items[0])
    return dict(version=VERSION,batch_slot=BATCH,authorization=AUTHORIZED_GIT,prior_receipt=prior_receipt(),
        shared_control_database=entry['control_database'],dispatch_order=[SLOT],entries=[entry],artifacts=artifacts or {})


def prepare_manifest(manifest):return base.prepare_manifest(manifest,profile=sys.modules[__name__])
def require(policy):return base.require(policy,profile=sys.modules[__name__])
def validate_config(config,control_database,*,question=None):return base.validate_config(config,control_database,question=question,profile=sys.modules[__name__])
def validate_prompt(policy,prompt,state):return base.validate_prompt(policy,prompt,state,profile=sys.modules[__name__])
def validate_client(policy,client):return base.validate_client(policy,client,profile=sys.modules[__name__])


def validate_previous_account(policy,client):
    auth=sources(policy)[0];planned=read(local('output/m6-authorized-products/'+auth['previous_batch']+'/planned.json'))
    saved=read(local(auth['previous_account_snapshot_path']))
    actual=client[planned['shared_control_database']][previous.ACCOUNT_COLLECTION].find_one({'_id':saved['_id']})
    if actual!=saved:raise ValueError('旧blocked非思考账户现场漂移，停止新单次')


def validate_runtime(policy,run,context,db):
    base.validate_runtime(policy,run,context,db,profile=sys.modules[__name__])
    validate_previous_account(policy,db.client)


open_client=previous.open_client


class SourceRelation048Ledger(previous.NonthinkingLedger):
    def __init__(self,db,contract):base.RemainingLedger.__init__(self,db,contract,profile=sys.modules[__name__])
