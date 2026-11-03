"""读取指定四修订标量并冻结精确输入；不创建模型、Mongo客户端或正式派发对象。"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'output/m6-connection-comparison-048-input-r1')
    parser.add_argument('--saved-rows',type=Path,help='仅用于离线复放已保存完整标量；省略时只读指定Milvus修订')
    args=parser.parse_args()
    out=args.output.resolve();allowed=(ROOT/'output').resolve()
    if not out.is_relative_to(allowed) or out==allowed or out.is_relative_to(allowed/'m6-authorized-products'):
        raise ValueError('输入冻结目录不得越界或占用正式账本')
    # 排他建目录必须在任何真实读取之前；失败目录和中间文件也不覆盖。
    out.mkdir(parents=True,exist_ok=False)
    def save(name,value):
        with (out/name).open('x',encoding='utf-8',newline='\n') as stream:
            json.dump(value,stream,ensure_ascii=False,indent=2);stream.write('\n')
    os.environ.update(PROJECT_ROOT=str(ROOT),LOG_CONSOLE_ENABLE='False',LOG_FILE_ENABLE='False',
        HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1')
    import dotenv
    dotenv.load_dotenv=lambda *a,**kw:False
    from app.evaluation.connection_048_preflight import prepare_catalog,DATASET_ID,DATASET_VERSION,CONFIG_ID,CONFIG_VERSION
    from app.evaluation.catalog import EvaluationCatalog
    from app.evaluation.connection_048_inputs import assemble_input,validate_input_anchor,read_scalar_pool
    from app.infrastructure.providers import connection_comparison_048_risk as risk
    from app.knowledge.repository import fingerprint
    digest=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    summary=dict(status='started',provider_calls=0,local_inference=0,real_business_db_writes=0,
        formal_experiment_created=False,ledger_reserved=False,dispatch_admission='blocked_no_new_authorization')
    try:
        prepare_catalog(out/'prepared')
        resolved=EvaluationCatalog(out/'prepared/catalog/catalog.json').resolve(DATASET_ID,DATASET_VERSION,
            CONFIG_ID,CONFIG_VERSION,kb_id=risk.source_config()['target']['kb_id'])
        config=resolved['config'];risk.validate_candidate(config)
        seed_ref=dict(path='output/m6-comparison-answer-048-execution-r10/run-private.json',
            sha256='5e675da31560859ab2a4e15f347ae68a4963ab1a8a2ae0334cbf3f37eb46d64f')
        old=risk.read(risk.checked_file(seed_ref))
        rows=[json.loads(line) for line in resolved['dataset_path'].read_text(encoding='utf-8').splitlines() if line.strip()]
        selected=[q for q in rows if q['id']==risk.QUESTION_ID and q['split']=='dev']
        if len(selected)!=1:raise ValueError('原完整题集必须唯一选择dev048')
        question={k:selected[0][k] for k in ('id','question','product_names','history')}
        if question['question']!=old['question'] or old['query_plan']['original_query']!=question['question']:
            raise ValueError('封存种子问题与原题不一致')
        if args.saved_rows:
            pool=json.loads(args.saved_rows.read_text(encoding='utf-8'));operations=0
            origin=dict(kind='saved_full_scalar_replay',path=str(args.saved_rows.resolve()),sha256=digest(args.saved_rows))
        else:
            # 只取Milvus连接配置，禁用load_dotenv，既不消费MONGO_URL也不读取private-identity。
            uri=dotenv.dotenv_values(ROOT.parents[1]/'.env').get('MILVUS_URL')
            if not uri:raise ValueError('缺少既有MILVUS_URL')
            from pymilvus import MilvusClient
            client=MilvusClient(uri=uri,timeout=15)
            try:pool=read_scalar_pool(client,config)
            finally:client.close()
            operations=len(config['corpus']['snapshot']['documents'])
            origin=dict(kind='live_strong_scalar_projection',vectors_read=False,query_operations=operations)
        save('full-scalar-payloads-private.json',pool)
        inputs=dict(question=question,product_ids=old['product_snapshot']['product_ids'],
            query_plan=old['query_plan'],seeds=old['prompt_used_docs'],groups=old.get('evidence_groups') or [],
            frozen_scalar_payloads=pool)
        anchor=assemble_input(config,inputs);validate_input_anchor(anchor)
        save('candidate-anchor-private.json',anchor)
        with (out/'prompt-private.txt').open('xb') as stream:stream.write(anchor['result']['prompt'].encode('utf-8'))
        result=anchor['result']
        summary.update(status='passed',full_scope_scalar_payloads_replayed=True,exact_production_prompt_frozen=True,
            frozen_documents=len(config['corpus']['snapshot']['documents']),frozen_payload_members=len(pool),
            prompt_utf8_sha256=anchor['prompt_utf8_sha256'],source_result_sha256=fingerprint(result),
            candidate_anchor=dict(path=(out/'candidate-anchor-private.json').relative_to(ROOT).as_posix(),
                sha256=digest(out/'candidate-anchor-private.json')),
            config_subject_sha256=fingerprint(config),versions=config['versions'],
            documents=len(result['context']),reference_numbers=[r['reference_number'] for r in result['prompt_reference_map']],
            budget=result['budget'],seed_source=seed_ref,scalar_origin=origin,
            fresh_retrieval=False,real_scalar_query_operations=operations,
            model_identity='preserved_saved_fingerprint_not_fresh_weight_verification',
            independent_technical_review='open',real_answer_quality='open')
        save('input-freeze-summary-private.json',summary)
        print(json.dumps({k:summary[k] for k in ('status','frozen_documents','frozen_payload_members','documents',
            'prompt_utf8_sha256','real_scalar_query_operations','dispatch_admission')},ensure_ascii=False))
    except Exception as exc:
        # 不输出可能携带连接串或原文的底层异常；保留已写中间材料。
        save('failed-private.json',summary|dict(status='failed',error_type=type(exc).__name__))
        print(json.dumps(dict(status='failed',error_type=type(exc).__name__),ensure_ascii=False))
        return 1
    return 0


if __name__=='__main__':
    raise SystemExit(main())
