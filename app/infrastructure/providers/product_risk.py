"""封存授权的单题风险准入；与网关能力事实分离，不提供批量放行。"""
import copy
import hashlib
import json
import os
from pathlib import Path
from datetime import datetime,timezone

from pydantic import BaseModel,ConfigDict,Field
from app.answering.reviewed_subjects import GitEvidence,evidence_bytes
from app.knowledge.repository import fingerprint

ROOT=Path(__file__).resolve().parents[3]
SLOT='m6-05a-product-canary-r1'
AUTHORIZED_GIT=dict(commit='bcee5395604bcd7169c907ddcf146f163ccc2d14',
    path='docs/development/reviews/M6-single-product-risk-authorization-r1.json',
    sha256='0270a6e7d8cdfc434a0dadf8fcbe7bae8b80e2417515f73117b83b3f1f81a591')
MASTER_PATH='output/m6-attributed-evidence-diagnostic-20261031/prepared-r2/master-source-manifest.json'
MASTER_SHA256='e479481dec4be520d673d561975ab7a068d8298bbc85ea4ce72bcb5ed3d4e0e0'
BINDING_PATH='output/m6-diagnostic-subject-usage-fix-20261031/subject-binding.json'
SIX_USAGE_PATH='output/m6-diagnostic-subject-usage-review-20261031/r2/usage-review.json'
PROBE_PATH='output/m6-authorized-probes/m6-output-cap-4096-probe-r1/settled.json'


class SingleProductAdmission(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    authorization:GitEvidence
    manifest_sha256:str=Field(pattern=r'^[a-f0-9]{64}$')


def local(path):
    p=(ROOT/path).resolve()
    if not p.is_relative_to(ROOT.resolve()) or 'private-identity' in p.parts:
        raise ValueError('单题授权来源路径越界')
    return p


def read(path):return json.loads(Path(path).read_text('utf-8'))
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def code_version():
    return fingerprint({p.relative_to(ROOT).as_posix():sha(p) for p in sorted((ROOT/'app').rglob('*.py'))})


def prior_receipt():
    six=read(local(SIX_USAGE_PATH));probe=read(local(PROBE_PATH))
    if probe.get('slot')!='m6-output-cap-4096-probe-r1' or probe.get('classification')!='observed_limit_4096_at_fixed_profile':
        raise ValueError('缺少已结算探测来源，不能重置累计量')
    usage=probe['usage_receipt']
    counts=[x[k] for x in six['jobs'] for k in ('input','output')]+[usage['input_tokens'],usage['output_tokens']]
    if any(type(v) is not int or v<0 for v in counts) or not usage.get('usage_validation',{}).get('valid',True):
        raise ValueError('历史计量来源不完整')
    value=dict(six_sha256=sha(local(SIX_USAGE_PATH)),probe_sha256=sha(local(PROBE_PATH)),
        input_tokens=sum(x['input'] for x in six['jobs'])+usage['input_tokens'],
        output_tokens=sum(x['output'] for x in six['jobs'])+usage['output_tokens'])
    return value|dict(sha256=fingerprint(value))


def sources(policy):
    ref=policy.admission.authorization.model_dump(mode='json')
    if ref!=AUTHORIZED_GIT:raise ValueError('风险授权不是本包受控Git来源')
    auth=json.loads(evidence_bytes(ref))
    if (auth.get('kind')!='coordinator_scoped_product_diagnostic_risk_authorization' or
        auth.get('admission_version')!=policy.function_version or auth.get('fixed_authorization_slot')!=SLOT or
        auth.get('source_version')!='v1_only' or auth['budget']['max_new_product_streams']!=1 or
        auth['risk']['gateway_capability_status']!='unknown' or
        auth['risk']['unknown_paid_upper_bound_accepted_only_for_this_one_product_stream'] is not True):
        raise ValueError('单题风险授权内容不适用')
    source=local(auth['source_input']['path'])
    if sha(source)!=auth['source_input']['file_sha256'] or sha(local(BINDING_PATH))!=auth['source_input']['subject_binding_file_sha256']:
        raise ValueError('已审输入或绑定来源漂移')
    anchor=read(source)
    if (fingerprint(anchor['result']['prompt'])!=auth['source_input']['prompt_canonical_fingerprint'] or
        hashlib.sha256(anchor['result']['prompt'].encode()).hexdigest()!=auth['source_input']['prompt_utf8_sha256']):
        raise ValueError('已审prompt来源漂移')
    if sha(local(MASTER_PATH))!=MASTER_SHA256:raise ValueError('版1控制库来源清单变化')
    parent=next(x for x in read(local(MASTER_PATH))['version_sources'] if x['version']==1)
    if any(parent[k]!=anchor['new_config']['target'][k] for k in ('owner_id','kb_id')):
        raise ValueError('原正式主体与输入来源不一致')
    runtime=auth['runtime'];budget=auth['budget'];prior=prior_receipt()
    expected=dict(status='unknown',semantics='unknown',evidence=None,n=runtime['n'],model=runtime['model'],
        endpoint_sha256=runtime['endpoint_sha256'],client_versions=runtime['client_versions'],limit_field=runtime['limit_field'],
        thinking=None,reasoning_budget=None,per_request_total_output_tokens=runtime['requested_total_output_tokens'],
        prior_input_tokens=budget['prior_diagnostic_input_tokens'],prior_output_tokens=budget['prior_diagnostic_output_tokens'],
        prior_source_sha256=prior['sha256'],max_total_input_tokens=budget['max_total_diagnostic_input_tokens'],
        max_total_output_tokens=budget['max_total_diagnostic_output_tokens'])
    if any(getattr(policy,k)!=v for k,v in expected.items()) or (prior['input_tokens'],prior['output_tokens'])!=(policy.prior_input_tokens,policy.prior_output_tokens):
        raise ValueError('风险准入profile或历史预算漂移')
    return auth,anchor,parent


def config_subject(config):
    from .output_contract import payload
    value=copy.deepcopy(config)
    contract=payload(value['parameters']['answer_budget']['output_contract'])
    contract['admission'].pop('manifest_sha256')
    value['parameters']['answer_budget']['output_contract']=contract
    return value


def build_manifest(config,question,*,control_database):
    from .output_contract import parse_contract
    policy=parse_contract(config['parameters']['answer_budget']['output_contract'])
    auth,anchor,parent=sources(policy)
    expected=copy.deepcopy(anchor['new_config']);actual=copy.deepcopy(config)
    for item in (expected,actual):
        item.pop('experiment_id',None);item.pop('question_ids',None)
        item['versions'].pop('code',None)
        item['parameters']['answer_budget'].pop('output_contract',None)
        item['parameters']['answer_budget'].pop('output_token_field',None)
    if (actual!=expected or control_database!=parent['control_database'] or
        config['question_ids']!=[auth['question_id']] or question['id']!=auth['question_id'] or
        config['dataset_sha256']!=auth['source_dataset_sha256'] or
        config['split_manifest_sha256']!=auth['source_split_manifest_sha256'] or config['versions']['code']!=code_version()):
        raise ValueError('单题正式配置／题目／控制目标／源码不在授权范围')
    budget=config['parameters']['answer_budget'];limits=auth['budget']
    if any(budget[k]!=limits[v] for k,v in [('context_window','context_window'),('output_tokens','output_tokens_requested'),
        ('reserve_tokens','reserve_tokens'),('max_chars','max_chars')]) or budget['output_token_field']!=auth['runtime']['limit_field']:
        raise ValueError('单题输入输出预算变化')
    inputs={k:question[k] for k in ('id','question','product_names','history')}
    return dict(version='diagnostic_single_product_risk_v1',slot=SLOT,config_subject=config_subject(config),
        control_database=control_database,question=inputs,input_sha256=fingerprint(inputs),
        authorization=policy.admission.authorization.model_dump(mode='json'),prior_receipt=prior_receipt(),
        prompt_sha256=auth['source_input']['prompt_canonical_fingerprint'])


def slot_dir():return ROOT/'output/m6-authorized-products'/SLOT


def exclusive(path,value):
    with Path(path).open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.flush();os.fsync(f.fileno())


def prepare_manifest(manifest):
    directory=slot_dir();directory.mkdir(parents=True,exist_ok=True);path=directory/'planned.json'
    if path.exists():
        prior=read(path)
        if prior!=manifest:
            # 前置失败后仅允许追加同一输入的源码冻结，首份计划及失败现场不改。
            # 所有冻结仍争用同一个started文件，绝不产生第二份调用额度。
            a,b=copy.deepcopy(prior),copy.deepcopy(manifest)
            for value in (a,b):value['config_subject']['versions'].pop('code')
            if a!=b or (directory/'started.json').exists() or (directory/'settled.json').exists():
                raise ValueError('固定授权槽不允许变更范围或已消费后重新计划')
            plans=directory/'code-plans';plans.mkdir(exist_ok=True)
            path=plans/(fingerprint(manifest)+'.json')
            if path.exists():
                if read(path)!=manifest:raise ValueError('追加的源码冻结冲突')
            else:
                try:exclusive(path,manifest)
                except FileExistsError:
                    if read(path)!=manifest:raise ValueError('追加的源码冻结并发冲突')
    else:
        try:exclusive(path,manifest)
        except FileExistsError:
            if read(path)!=manifest:raise ValueError('固定授权槽并发计划冲突')


def require(policy):
    sources(policy)
    planned=read(slot_dir()/'planned.json')
    if fingerprint(planned)!=policy.admission.manifest_sha256:
        path=slot_dir()/'code-plans'/(policy.admission.manifest_sha256+'.json')
        if not path.is_file():raise ValueError('缺少匹配的单题源码冻结')
        planned=read(path)
    if fingerprint(planned)!=policy.admission.manifest_sha256:raise ValueError('单题执行清单身份变化')
    return planned


def validate_config(config,control_database,*,question=None):
    from .output_contract import parse_contract
    policy=parse_contract(config['parameters']['answer_budget']['output_contract']);planned=require(policy)
    q=question if question is not None else planned['question']
    if build_manifest(config,q,control_database=control_database)!=planned:
        raise ValueError('正式请求与固定单题执行清单不一致')
    return planned


def validate_prompt(policy,prompt,state):
    auth,anchor,_=sources(policy);expected=anchor['result'];budget=auth['budget']
    budget_value={k:v for k,v in state['prompt_budget'].items() if k!='policy'}
    original_budget={k:v for k,v in expected['budget'].items() if k!='policy'}
    if (prompt!=expected['prompt'] or state['prompt_used_docs']!=expected['context'] or
        state.get('prompt_reference_map',[])!=expected['prompt_reference_map'] or budget_value!=original_budget or
        state.get('evidence_groups',[])!=expected['groups'] or
        state['prompt_budget']['input_tokens']!=budget['saved_conservative_input_reservation'] or
        state['prompt_budget']['input_limit']!=budget['single_input_limit']):
        raise ValueError('单题实际prompt／context／引用／预算与受审输入不一致')


def validate_runtime(policy,run,context,db):
    if not context:raise ValueError('风险准入只能由正式单题job消费')
    validate_config(context['config'],context['control_database'],question=context['question'])
    from app.evaluation.execution_links import validate_execution
    from app.evaluation.execution_identity import run_input
    validate_execution(context['control_db'],context['execution'],context['config'])
    link=db.evaluation_execution_links.find_one(dict(experiment_id=context['execution']['experiment_id'],
        attempt=context['execution']['attempt'],run_id=run['run_id'],mode='execution'))
    if (not link or link['control_database']!=context['control_database'] or
        link['target_database']!=db.name or link['question_id']!=context['question']['id'] or
        link['output_contract']!=policy.model_dump(mode='json') or
        link['run_input_sha256']!=fingerprint(run_input(run,db))):
        raise ValueError('单题正式执行关联缺失或输入漂移')


def start(policy,*,db_name,run_id,run_identity,context):
    if not context:raise ValueError('缺少单题正式执行身份')
    validate_config(context['config'],context['control_database'],question=context['question'])
    if db_name!=context['config']['target']['database'] or not context.get('execution'):
        raise ValueError('单题账户目标或正式任务身份不一致')
    exclusive(slot_dir()/'started.json',dict(slot=SLOT,manifest_sha256=policy.admission.manifest_sha256,
        contract_sha256=fingerprint(policy.model_dump(mode='json')),run_id=run_id,run_identity=run_identity,
        config_sha256=fingerprint(context['config']),control_database=context['control_database'],target_database=db_name,
        experiment={k:context['execution'][k] for k in ('experiment_id','attempt','config_sha256')},
        at=datetime.now(timezone.utc).isoformat(),status='started_unknown_until_settlement'))


def settle(policy,receipt):
    started=read(slot_dir()/'started.json')
    if any(receipt[k]!=started[k] for k in ('run_id','run_identity')):raise ValueError('固定槽结算Run不一致')
    path=slot_dir()/'settled.json';value=dict(manifest_sha256=policy.admission.manifest_sha256,receipt=receipt)
    if path.exists():
        if read(path)!=value:raise ValueError('固定槽结算改变')
    else:exclusive(path,value)


def validate_client(policy,client):
    from .output_contract import unwrap_client
    client=unwrap_client(client);auth,_,_=sources(policy);runtime=auth['runtime']
    if (client.temperature!=runtime['temperature'] or float(client.request_timeout)!=runtime['timeout_seconds'] or
        client.stream_usage is not True or client.root_client._client.follow_redirects is not False):
        raise ValueError('单题实际客户端profile不符')
    effective=client._get_request_payload('',n=1,extra_body={policy.limit_field:4096})
    if set(effective)-{'model','messages','temperature','n','stream','extra_body','stream_options'}:
        raise ValueError('单题存在未授权的额外wire参数')


def open_client(policy):
    """专用客户端沿正式job使用；不修改全局缓存或默认配置。"""
    import httpx
    from app.conf.lm_config import lm_config
    from .diagnostic_usage import preserving_chat_class
    http=httpx.Client(timeout=120,follow_redirects=False)
    try:
        client=preserving_chat_class()(model=policy.model,base_url=lm_config.base_url,api_key=lm_config.api_key,
            temperature=0.1,n=1,stream_usage=True,max_retries=0,timeout=120,http_client=http)
        return client,http
    except BaseException:http.close();raise
