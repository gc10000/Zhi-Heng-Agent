"""新连接比较单题风险档案：预检不是授权，旧槽不能提供新额度。"""
import copy
import hashlib
import json
import sys
import subprocess
from pathlib import Path

from app.answering.reviewed_subjects import evidence_bytes
from app.knowledge.repository import fingerprint
from . import remaining_risk as base
from . import nonthinking_risk
from . import comparison_answer_048_v2_risk as consumed
from .product_risk import exclusive, code_version

ROOT = Path(__file__).resolve().parents[3]
VERSION = 'diagnostic_connection_comparison_048_v1'
BATCH = 'm6-connection-comparison-048-r1'
SLOT = BATCH + '-support-v1-048'
QUESTION_ID = 'support-v1-048'
ACCOUNT_COLLECTION = 'diagnostic_connection_comparison_048_accounts'
AUTHORIZATION_REFERENCE_PATH = 'docs/development/reviews/M6-connection-comparison-048-authorization-reference-r1.json'


def load_authorization_reference(root=ROOT):
    """Git引用独立于app指纹，避免授权→源码→输入→授权循环；未提交引用拒绝。"""
    from app.answering.reviewed_subjects import GitEvidence
    pin = root / AUTHORIZATION_REFERENCE_PATH
    if not pin.exists():
        return None
    payload = pin.read_bytes()
    ref = GitEvidence.model_validate_json(payload).model_dump(mode='json')
    if ref['path'] != 'docs/development/reviews/M6-connection-comparison-048-authorization-r1.json':
        raise ValueError('连接048只能绑定本次专属授权')
    saved = subprocess.run(['git', 'show', 'HEAD:' + AUTHORIZATION_REFERENCE_PATH], cwd=root,
        capture_output=True, timeout=10)
    if saved.returncode or saved.stdout != payload:
        raise ValueError('连接048授权引用尚未提交或发生漂移')
    return ref


AUTHORIZED_GIT = load_authorization_reference()
SOURCE_CONFIG = dict(path='output/m6-comparison-answer-048-execution-r10/catalog/configs/m6-comparison-answer-048-execution-r8-final.json',
    sha256='ac0a4178f91fa638fd13ea08c9f897e26bf396005aa3581216e6e82ce8095b50')
TECHNICAL_REVIEW = dict(commit='17103bfb9a37c786185557f25fc4602b62cb682d',
    path='docs/development/reviews/M6-connection-comparison-independent-review-r1.json',
    sha256='3b5b5c32dc8e35b3b60b2a1405fa34e000ff4f740bf605a8def75211ba9360d4')
USAGE_REVIEW = dict(commit='17103bfb9a37c786185557f25fc4602b62cb682d',
    path='docs/development/reviews/M6-comparison-answer-048-v2-execution-r8-validation.json',
    sha256='5f55fa8f7adda4cfa511700ba9f288cc1b446df1466cf8e9e6171393d3b13721')
read, sha, now = base.read, base.sha, base.now
config_subject, entry_for = base.config_subject, base.entry_for


def local(relative):
    if not isinstance(relative,str) or Path(relative).is_absolute() or '\\' in relative:
        raise ValueError('连接048来源必须是仓库内相对路径')
    path=(ROOT/relative).resolve()
    if not path.is_relative_to(ROOT.resolve()) or any(p in {'private-identity','.env'} for p in path.parts):
        raise ValueError('连接048来源路径越界')
    return path


def checked_file(ref):
    path=local(ref['path'])
    if sha(path)!=ref['sha256']:
        raise ValueError('连接048冻结文件hash漂移')
    return path


def source_config():
    return read(checked_file(SOURCE_CONFIG))


def prior_receipt():
    saved=json.loads(evidence_bytes(USAGE_REVIEW))
    if (saved.get('cumulative_input_tokens'),saved.get('cumulative_output_tokens'))!=(56239,30516) or (
        saved.get('prior_input_tokens',0)+saved.get('new_input_tokens',0),
        saved.get('prior_output_tokens',0)+saved.get('new_output_tokens',0))!=(56239,30516):
        raise ValueError('连接048历史计量与封存累计不一致')
    if (saved.get('ledger_state')!='blocked' or saved.get('quality_review')!='rejected' or
            saved.get('halt') is not True or saved.get('pending') is not False or saved.get('unknown_windows')!=0):
        raise ValueError('连接048旧批次停止来源不完整')
    value=dict(input_tokens=56239,output_tokens=30516,sources=dict(r8=USAGE_REVIEW))
    return value|dict(sha256=fingerprint(value))


def technical_review():
    report=json.loads(evidence_bytes(TECHNICAL_REVIEW))
    if report.get('final_technical_review')!='passed_with_specific_boundaries' or report.get('unresolved_reproduced_technical_findings'):
        raise ValueError('连接比较缺少独立技术通过')
    for name,digest in report['final_candidate'].items():
        if name.startswith('app/answering/') and sha(local(name))!=digest:
            raise ValueError('已审连接比较源码发生漂移')
    return report


def prompt_version():
    return fingerprint({p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'prompts').rglob('*.prompt'))})


def candidate_config(original=None):
    """允许的差异在这里一次定义；不从题目rubric构造输入。"""
    config=copy.deepcopy(source_config() if original is None else original)
    config['experiment_id']=SLOT
    config['question_ids']=[QUESTION_ID]
    config['versions'].update(code=code_version(),prompt=prompt_version())
    policy=config['parameters']['evidence_attribution']
    policy['comparison_answer']=dict(enabled=True,function_version='connection_comparison_v1')
    if (policy.get('assertion_binding') or {}).get('enabled'):
        raise ValueError('连接比较不能叠加旧摘录模式')
    from .output_contract import parse_contract
    old=config['parameters']['answer_budget']['output_contract']
    new={k:copy.deepcopy(v) for k,v in old.items() if k not in {'admission','function_version'}}
    new.update(enabled=False,function_version=VERSION,admission=None,ledger_id=BATCH,
        prior_input_tokens=56239,prior_output_tokens=30516,prior_source_sha256=prior_receipt()['sha256'],
        max_total_input_tokens=84655,max_total_output_tokens=34612)
    config['parameters']['answer_budget']['output_contract']=parse_contract(new).model_dump(mode='json')
    return config


def validate_candidate(config):
    expected=candidate_config()
    actual=copy.deepcopy(config)
    # 只正规化派发开关与专属授权；端点、历史来源及其他合同字段不能被整块忽略。
    from .output_contract import parse_contract
    contract=parse_contract(actual['parameters']['answer_budget']['output_contract']).model_dump(mode='json')
    contract.update(enabled=False,admission=None)
    actual['parameters']['answer_budget']['output_contract']=contract
    if actual!=expected:
        raise ValueError('连接048配置超出冻结来源、生成包或新身份范围')
    technical_review()
    return expected


def batch_dir(): return local('output/m6-authorized-products/'+BATCH)
def slot_dir(policy): return batch_dir()/'members'/policy.admission.member_slot


def sources(policy):
    # 先拒绝，不能读取凭据、建目录或用用户的实施授权冒充调用授权。
    if AUTHORIZED_GIT is None or policy.admission is None:
        raise ValueError('连接048尚无新单题Git授权，禁止派发')
    if policy.admission.authorization.model_dump(mode='json')!=AUTHORIZED_GIT:
        raise ValueError('连接048不能借用旧授权')
    auth=json.loads(evidence_bytes(AUTHORIZED_GIT))
    if (auth.get('kind')!='coordinator_scoped_connection_comparison_048_authorization' or
            auth.get('status')!='authorized_for_one_stream_only' or auth.get('admission_version')!=VERSION or
            auth.get('fixed_batch_slot')!=BATCH or auth.get('dispatch_order')!=[SLOT] or
            auth.get('technical_review')!=TECHNICAL_REVIEW or auth.get('prior_usage')!=prior_receipt() or
            auth.get('source_config')!=SOURCE_CONFIG or auth.get('previous_batch')!=consumed.BATCH):
        raise ValueError('连接048授权身份或历史来源不一致')
    if auth.get('user_authorization')!=dict(question_id=QUESTION_ID,max_provider_streams=1,
            accept_unknown_cost_upper_bound=True,stop_on_first_failure=True,retry_or_reuse_old_slots=False):
        raise ValueError('连接048授权缺少单次预算或费用未知接受')
    members=auth.get('members')
    if not isinstance(members,list) or len(members)!=1:
        raise ValueError('连接048授权只能有一个成员')
    member=members[0]
    if (member.get('fixed_slot'),member.get('question_id'),member.get('expected_generation'))!=(SLOT,QUESTION_ID,True):
        raise ValueError('连接048成员身份漂移')
    anchor=read(checked_file(auth['candidate_anchor']))
    if anchor['new_config']!=validate_candidate(anchor['new_config']):
        raise ValueError('连接048来源anchor必须保留完整关闭合同模板')
    from app.evaluation.connection_048_inputs import validate_input_anchor
    validate_input_anchor(anchor)
    if anchor['production_inputs']['question']!=authorized_inputs(auth,member):
        raise ValueError('连接048冻结prompt的问题输入与原完整题集不一致')
    expected_contract=copy.deepcopy(anchor['new_config']['parameters']['answer_budget']['output_contract'])
    actual=policy.model_dump(mode='json');actual.update(enabled=False,admission=None)
    if actual!=expected_contract:
        raise ValueError('连接048实际合同与冻结预算不一致')
    result=anchor['result']
    if (hashlib.sha256(result['prompt'].encode()).hexdigest()!=member.get('prompt_utf8_sha256') or
            fingerprint(result)!=member.get('source_result_sha256') or result['budget']['input_limit']!=28416):
        raise ValueError('连接048精确prompt或输入预算漂移')
    from app.answering.comparison_answers import build_frame_catalog
    from app.answering.comparison_context import validate_assembly_manifest,validate_context_policy
    config=anchor['new_config'];attribution=config['parameters']['evidence_attribution']
    catalog=build_frame_catalog(result['prompt_reference_map'],result['context'],attribution)
    validate_assembly_manifest(result['comparison_context_assembly'],catalog)
    validate_context_policy(result['comparison_context_assembly'],attribution,max_docs=10,max_chars=12000)
    parent=dict(control_database=auth['evaluation_control_database'],**{
        k:config['target'][k] for k in ('owner_id','kb_id')})
    runtime=dict(n=1,model=policy.model,endpoint_sha256=policy.endpoint_sha256,client_versions=policy.client_versions,
        limit_field='max_completion_tokens',requested_total_output_tokens=4096,thinking=False,
        temperature=0.1,timeout_seconds=120,sdk_max_retries=0,stream=True)
    if auth.get('runtime')!=runtime or auth.get('budget')!=dict(context_window=32768,output_tokens_requested=4096,
            reserve_tokens=256,max_chars=12000,single_input_limit=28416,max_new_product_streams=1,max_attempts_per_member=1):
        raise ValueError('连接048运行参数或预算漂移')
    return auth,member,anchor,parent


def authorized_inputs(auth,member):
    dataset=checked_file(auth['dataset']);manifest=checked_file(auth['split_manifest'])
    config=source_config()
    if sha(dataset)!=config['dataset_sha256'] or sha(manifest)!=config['split_manifest_sha256']:
        raise ValueError('连接048原完整题集身份漂移')
    rows=[json.loads(line) for line in dataset.read_text(encoding='utf-8').splitlines() if line.strip()]
    if (len(rows),sum(q['split']=='dev' for q in rows),sum(q['split']=='heldout' for q in rows))!=(150,85,65):
        raise ValueError('连接048不能缩题集或改变85/65划分')
    found=[q for q in rows if q['id']==QUESTION_ID and q['split']=='dev']
    if len(found)!=1: raise ValueError('连接048必须唯一且属于dev')
    return {k:found[0][k] for k in ('id','question','product_names','history')}


def execution_control_database(auth,parent): return auth['evaluation_control_database']
def build_member(config,question,control_database):
    validate_candidate(config)
    return base.build_member(config,question,control_database,profile=sys.modules[__name__])


def build_manifest(items,*,artifacts=None):
    if len(items)!=1: raise ValueError('连接048清单只允许一个成员')
    entry=build_member(*items[0]);policy=items[0][0]['parameters']['answer_budget']['output_contract']
    from .output_contract import parse_contract
    auth=sources(parse_contract(policy))[0]
    return dict(version=VERSION,batch_slot=BATCH,authorization=AUTHORIZED_GIT,prior_receipt=prior_receipt(),
        shared_control_database=auth['evaluation_control_database'],dispatch_order=[SLOT],entries=[entry],artifacts=artifacts or {})


def prepare_manifest(manifest):
    if AUTHORIZED_GIT is None or manifest.get('authorization')!=AUTHORIZED_GIT:
        raise ValueError('连接048未获新授权，不能冻结派发清单')
    validate_manifest(manifest)
    return base.prepare_manifest(manifest,profile=sys.modules[__name__])


def validate_manifest(manifest):
    """重算整个清单，防止只核成员却从顶层改址领取另一份账户。"""
    entries=manifest.get('entries')
    if not isinstance(entries,list) or len(entries)!=1:
        raise ValueError('连接048冻结清单必须恰好一个成员')
    config=copy.deepcopy(entries[0]['config_subject'])
    config['parameters']['answer_budget']['output_contract']['admission']['manifest_sha256']=fingerprint(manifest)
    expected=build_manifest([(config,entries[0]['question'],entries[0]['control_database'])],
        artifacts=manifest.get('artifacts',{}))
    if manifest!=expected:
        raise ValueError('连接048完整清单与专属授权、共享账本或顺序不一致')
    return manifest


def require(policy):
    manifest=base.require(policy,profile=sys.modules[__name__])
    return validate_manifest(manifest)
def validate_config(config,control_database,*,question=None):
    return base.validate_config(config,control_database,question=question,profile=sys.modules[__name__])
def validate_prompt(policy,prompt,state):
    base.validate_prompt(policy,prompt,state,profile=sys.modules[__name__])
    expected=sources(policy)[2]['result']['comparison_context_assembly']
    if state.get('comparison_context_assembly')!=expected:
        raise ValueError('连接048装配身份漂移')
def validate_client(policy,client): return base.validate_client(policy,client,profile=sys.modules[__name__])


def validate_previous_account(policy,client):
    auth=sources(policy)[0]
    old=local('output/m6-authorized-products/'+consumed.BATCH)
    # 文件hash由新授权锚定；旧账户仅查指定key，绝不改state/slot。
    refs=auth['previous_receipts']
    for name in ('planned','halt','settled'):
        checked_file(refs[name])
    planned=read(checked_file(refs['planned']));halt=read(checked_file(refs['halt']))
    settlement=read(checked_file(refs['settled']))
    if (local(refs['planned']['path'])!=old/'planned.json' or
            local(refs['halt']['path'])!=old/'halt.json' or
            local(refs['settled']['path'])!=old/'members'/consumed.SLOT/'settled.json' or
            planned.get('version')!=consumed.VERSION or planned.get('dispatch_order')!=[consumed.SLOT]):
        raise ValueError('连接048旧停止槽来源身份漂移')
    saved=client[planned['shared_control_database']][consumed.ACCOUNT_COLLECTION].find_one(
        {'_id':fingerprint([consumed.VERSION,consumed.BATCH])})
    if (not saved or saved.get('state')!='blocked' or saved.get('pending') is not None or
            saved.get('unknown_windows') or set(saved.get('settled',{}))!={consumed.SLOT} or
            saved['settled'][consumed.SLOT]!=settlement.get('receipt') or saved.get('halt')!=halt or
            saved.get('reviews')!={consumed.SLOT:dict(accepted=False,evidence=halt.get('source_review'))} or
            halt.get('no_more_provider_calls') is not True or halt.get('source_review',{}).get('accepted') is not False):
        raise ValueError('连接048旧账户未保持结算后的拒绝停止')


def validate_runtime(policy,run,context,db):
    base.validate_runtime(policy,run,context,db,profile=sys.modules[__name__])
    validate_previous_account(policy,db.client)


def open_client(policy):
    sources(policy)
    return nonthinking_risk.open_client(policy)


def seal_stop(evidence):
    path=batch_dir()/'halt.json';path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        if read(path)!=evidence: raise ValueError('连接048停止证据不可覆盖')
    else:
        try: exclusive(path,evidence)
        except FileExistsError:
            if read(path)!=evidence: raise ValueError('连接048并发停止证据冲突')


class ConnectionComparison048Ledger(nonthinking_risk.NonthinkingLedger):
    def __init__(self,db,contract):
        base.RemainingLedger.__init__(self,db,contract,profile=sys.modules[__name__])
