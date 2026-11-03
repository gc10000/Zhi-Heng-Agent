"""只读冻结材料并生成关闭的单题catalog；无数据库、模型或授权登记。"""
import argparse
import copy
import json
import shutil
from pathlib import Path

from app.infrastructure.providers import connection_comparison_048_risk as risk
from app.knowledge.repository import fingerprint
from .catalog import EvaluationCatalog
from .runner import select_questions

DATASET_ID='m6-full-dev-r1'
DATASET_VERSION='fb-07c584730833908571fe9dd7c7c890afa3cf9e66'
CONFIG_ID=risk.BATCH
CONFIG_VERSION='connection-r1'
SOURCE_CATALOG='output/m6-comparison-answer-048-execution-r10/catalog/catalog.json'
DEFAULT_OUTPUT='output/'+risk.BATCH


def write_once(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    with path.open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')


def preflight_catalog(catalog_path,*,control_database):
    catalog=EvaluationCatalog(catalog_path)
    raw=catalog._catalog()
    if len(raw['datasets'])!=1 or len(raw['configs'])!=1:
        raise ValueError('连接048目录必须只有一个完整题集和一个专属配置')
    original=risk.source_config();kb=original['target']['kb_id']
    resolved=catalog.resolve(DATASET_ID,DATASET_VERSION,CONFIG_ID,CONFIG_VERSION,kb_id=kb)
    config=resolved['config'];risk.validate_candidate(config)
    if not isinstance(control_database,str) or not control_database or control_database==config['target']['database']:
        raise ValueError('连接048须显式采用独立持久评测控制库')
    from .query_adapter import RealQueryExecutor
    # 只构造验证对象，不enter：不打开资源、模型、Mongo或执行题目。
    RealQueryExecutor(config)
    rows=[json.loads(line) for line in resolved['dataset_path'].read_text(encoding='utf-8').splitlines() if line.strip()]
    if (len(rows),sum(q['split']=='dev' for q in rows),sum(q['split']=='heldout' for q in rows))!=(150,85,65):
        raise ValueError('连接048预检要求原完整150题85/65划分')
    selected=select_questions(rows,config)
    if len(selected)!=1 or selected[0]['id']!=risk.QUESTION_ID or selected[0]['split']!='dev':
        raise ValueError('连接048只能选择原dev单题')
    policy=config['parameters']['evidence_attribution'];snapshot=config['corpus']['snapshot']
    chunks=[c for d in snapshot['documents'] for c in d['chunks']]
    frozen={c['chunk_uid']:c['payload_sha256'] for c in chunks}
    if (len(snapshot['documents'])!=4 or len(chunks)!=582 or len(frozen)!=582 or
            frozen!=policy['source_relations']['frozen_payloads']):
        raise ValueError('连接048须保留原4资料582成员快照，不能用333投影冒充')
    output=config['parameters']['answer_budget']['output_contract']
    if output['enabled'] is not False or output.get('admission') is not None:
        raise ValueError('零调用预检只接受无伪授权的关闭合同')
    return dict(schema_version=1,kind='connection_048_static_catalog_preflight',status='passed',
        batch=risk.BATCH,slot=risk.SLOT,config_id=CONFIG_ID,config_version=CONFIG_VERSION,
        dataset_version=DATASET_VERSION,dataset_sha256=resolved['dataset_sha256'],
        split_manifest_sha256=resolved['manifest_sha256'],config_file_sha256=resolved['config_sha256'],
        config_subject_sha256=fingerprint(config),runtime_versions=copy.deepcopy(config['versions']),
        source_config=risk.SOURCE_CONFIG,technical_review=risk.TECHNICAL_REVIEW,
        prior_receipt=risk.prior_receipt(),full_dataset_rows=150,dev_rows=85,heldout_rows=65,
        selected_questions=1,question_input_sha256=fingerprint({k:selected[0][k] for k in ('id','question','product_names','history')}),
        frozen_documents=4,frozen_payload_members=582,full_scope_scalar_payloads_replayed=False,
        exact_production_prompt_frozen=False,prompt_utf8_sha256=None,
        dispatch_admission='blocked_no_new_authorization',formal_experiment_created=False,
        ledger_reserved=False,provider_calls=0,local_inference=0,real_business_db_reads=0,real_business_db_writes=0,
        model_identity='preserved_saved_fingerprint_not_fresh_weight_verification',
        control_database=control_database)


def prepare_catalog(output,*,source_catalog=None):
    output=Path(output).resolve();allowed=(risk.ROOT/'output').resolve()
    if (not output.is_relative_to(allowed) or output==allowed or
            output.is_relative_to(allowed/'m6-authorized-products')):
        raise ValueError('连接048预检输出目录不能越界或占用正式账本路径')
    if output.exists():raise FileExistsError('连接048预检目录已存在，保留原证据')
    source=EvaluationCatalog(source_catalog or risk.local(SOURCE_CATALOG))
    original=risk.source_config()
    resolved=source.resolve(DATASET_ID,DATASET_VERSION,'m6-comparison-answer-048-execution-r8','r8',
        kb_id=original['target']['kb_id'])
    if resolved['config']!=original:raise ValueError('原catalog与固定配置来源不同')
    config=risk.candidate_config(original);risk.validate_candidate(config)
    # 沿已封存的控制库身份选择；只读取Git资料，不建立数据库连接。
    from app.answering.reviewed_subjects import evidence_bytes
    from app.infrastructure.providers.comparison_answer_048_v2_risk import AUTHORIZED_GIT
    control=json.loads(evidence_bytes(AUTHORIZED_GIT))['evaluation_control_database']
    output.mkdir(parents=True,exist_ok=False)
    catalog_dir=output/'catalog';catalog_dir.mkdir();(output/'execution').mkdir()
    shutil.copyfile(resolved['dataset_path'],catalog_dir/'support-v1-fb-07c584.jsonl')
    shutil.copyfile(resolved['manifest_path'],catalog_dir/'support-v1-fb-07c584-manifest.json')
    write_once(catalog_dir/'configs/connection-r1.json',config)
    definition=dict(datasets=[dict(id=DATASET_ID,version=DATASET_VERSION,
        dataset='support-v1-fb-07c584.jsonl',manifest='support-v1-fb-07c584-manifest.json',kb_ids=[original['target']['kb_id']])],
        configs=[dict(id=CONFIG_ID,version=CONFIG_VERSION,path='configs/connection-r1.json')])
    write_once(catalog_dir/'catalog.json',definition)
    summary=preflight_catalog(catalog_dir/'catalog.json',control_database=control)
    write_once(output/'execution/static-preflight-private.json',summary)
    write_once(output/'execution/prepared-identity-private.json',dict(
        catalog_path=str(catalog_dir/'catalog.json'),execution_output=str(output/'execution'),
        config_id=CONFIG_ID,config_version=CONFIG_VERSION,client_request_id=risk.BATCH+'-request-01',
        evaluation_control_database=control,status='prepared_disabled_not_authorized',
        experiment_id=None,run_id=None,checkpoint_id=None))
    return summary


def main():
    parser=argparse.ArgumentParser(description='准备默认关闭的新连接048目录，静态核验，不联网或派发。')
    parser.add_argument('--output',type=Path,default=risk.ROOT/DEFAULT_OUTPUT)
    args=parser.parse_args()
    summary=prepare_catalog(args.output)
    print(json.dumps({k:summary[k] for k in ('status','selected_questions','frozen_documents',
        'frozen_payload_members','dispatch_admission','provider_calls','exact_production_prompt_frozen')},ensure_ascii=False))
