"""冻结已授权两版85题的完整生产输入；只读标量，禁止模型调用和正式登记。"""
import argparse
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
MAIN = ROOT.parents[1]
sys.path.insert(0, str(ROOT))


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT/'output/m6-feedback-candidate-full-20261104-r1')
    args = parser.parse_args()
    out = args.output.resolve()
    if not out.is_relative_to(ROOT/'output') or out == ROOT/'output':
        raise ValueError('完整候选冻结只能写入独立output子目录')
    out.mkdir(exist_ok=False)
    os.environ.update(PROJECT_ROOT=str(ROOT), LOG_CONSOLE_ENABLE='False', LOG_FILE_ENABLE='False',
        HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
    import dotenv
    dotenv.load_dotenv = lambda *a, **kw: False
    from app.evaluation.connection_048_inputs import read_scalar_pool
    from app.evaluation.m6_feedback_inputs import validate_scalar_pool, assemble_member, validate_production_manifest
    from app.infrastructure.providers import m6_feedback_candidate_risk as risk
    from app.infrastructure.providers.product_risk import code_version
    from app.infrastructure.providers.output_contract import parse_contract
    from app.evaluation.validate_dataset import file_sha, fingerprint
    from app.retrieval.query_planner import plan_query, serialize_query_plan
    from app.retrieval.models import RetrievalHit, StageScore

    prepared = ROOT/'output/m6-feedback-stage-closure-20261103-r1/prepared-r4'
    state = read(prepared.parent/'live-r3/state-private.json')
    dispatch = read(prepared/'dispatch-closed-private.json')
    requests = read(prepared/'requests-closed.json')
    originals = read(MAIN/'output/m6-review-repair-attestation-20261030/candidate-v2-requests.json')
    shutil.copytree(prepared/'catalog', out/'catalog')
    catalog = read(out/'catalog/catalog-new.json')
    connection = read(ROOT/'output/m6-connection-comparison-048-input-r6/candidate-anchor-private.json')
    configs = [read(prepared/f'catalog/stage-configs/{n}-candidate-closed.json') for n in (1, 2)]
    uri = dotenv.dotenv_values(MAIN/'.env').get('MILVUS_URL')
    if not uri:
        raise ValueError('缺少既有MILVUS_URL')
    from pymilvus import MilvusClient
    client = MilvusClient(uri=uri, timeout=15)
    try:
        pool = read_scalar_pool(client, configs[0])
    finally:
        client.close()
    pool = validate_scalar_pool(configs[0], pool)
    if len(pool) != 582:
        raise ValueError('完整候选必须绑定四资料582标量')
    save(out/'full-scalars-private.json', pool)
    by_uid = {row['chunk_uid']: row for row in pool}
    endpoint = read(ROOT/'docs/development/reviews/M6-connection-comparison-048-authorization-r2.json')['runtime']['endpoint_sha256']
    contract = dict(enabled=False, function_version=risk.VERSION, n=1, status='unknown',
        endpoint_sha256=endpoint, model='qwen3.8-flash', client_versions={'openai':'2.28.0','langchain-openai':'1.1.11'},
        limit_field='max_completion_tokens', semantics='unknown', thinking=False, reasoning_budget=None,
        per_request_total_output_tokens=4096, ledger_id=risk.BATCH, max_total_input_tokens=4773888,
        max_total_output_tokens=688128, admission=None)
    contract = parse_contract(contract).model_dump(mode='json')
    code = code_version()
    candidates, entries, order = [], [], []
    for n, config in enumerate(configs, 1):
        config['versions']['code'] = code
        config['parameters']['answer_budget']['output_contract'] = deepcopy(contract)
        config_id = f'm6-feedback-stage-{n}-candidate'
        version = 'r1-production'
        members = [m for m in dispatch['members'] if m['candidate'] == n]
        ordered_ids = [m['question_id'] for m in members]
        config['dev_question_order'] = ordered_ids
        configfile = out/f'catalog/stage-configs/{n}-candidate-production.json'
        save(configfile, config)
        catalog['configs'].append(dict(id=config_id, version=version, path=configfile.relative_to(out/'catalog').as_posix()))
        request = deepcopy(requests[n-1]['request'])
        request.update(config_id=config_id, config_version=version)
        original = next(row for row in originals if row['baseline'] == n)
        control = original['control_database']
        selected = {q['id']: q for q in state[n-1]['selected']}
        from app.evaluation.catalog import EvaluationCatalog
        all_datasets = EvaluationCatalog(out/'catalog/catalog-new.json')._catalog()['datasets']
        dataset_descriptor = next(d for d in all_datasets if d['version'] == request['eval_set_version'])
        dataset_file = out/'catalog'/dataset_descriptor['dataset']
        split_file = out/'catalog'/dataset_descriptor['manifest']
        # 派生题集由entry.json登记，catalog可能不直接包含。
        source_files = out/'catalog/regression-versions'/request['eval_set_version'][3:35]
        if not dataset_file.is_file():
            raise ValueError('冻结catalog题集文件不存在')
        candidates.append(dict(candidate_slot=f'm6-feedback-stage-r1-v{n}', version=n,
            config_subject=config, control_database=control, experiment_id=config['experiment_id'],
            dataset_sha256=config['dataset_sha256'], split_manifest_sha256=config['split_manifest_sha256'],
            versions=config['versions'], question_ids=ordered_ids, request=request,
            dataset=dict(path=dataset_file.relative_to(ROOT).as_posix(), sha256=file_sha(dataset_file)),
            split_manifest=dict(path=split_file.relative_to(ROOT).as_posix(), sha256=file_sha(split_file))))
        saved = read(MAIN/f'output/m6-calibrated-candidate-execution-20261030/candidate-{n}/final-runs-and-links.json')
        runs = {row['link']['question_id']: row['run'] for row in saved}
        prompts = [read(p)['args'][0] for p in (MAIN/f'output/m6-calibrated-candidate-execution-20261030/candidate-{n}').glob('*stream-input.json')]
        for member in members:
            qid = member['question_id']
            q = selected[qid]
            question = {k: q[k] for k in ('id','question','product_names','history')}
            run = runs[qid]
            product_ids = run['product_snapshot']['product_ids']
            plan = plan_query(q['question'], config['corpus']['snapshot']['products'],
                requested_ids=run['input_product_snapshot']['product_ids'], messages=q['history'])
            if plan.route != member['route']:
                raise ValueError('正式规划与冻结范围不一致')
            plan = plan.model_copy(update={'revision_ids': tuple(r['active_revision_id'] for r in run.get('revision_snapshot', []))})
            seeds = []
            groups = run.get('evidence_groups') or []
            if plan.route == 'compare':
                seeds = deepcopy(connection['production_inputs']['seeds'])
                groups = deepcopy(connection['production_inputs']['groups'])
                product_ids = connection['production_inputs']['product_ids']
                plan = plan.model_copy(update={'product_ids': tuple(product_ids)})
            elif plan.route != 'clarify':
                matches = [p for p in prompts if '\n【用户问题】\n'+q['question'] in p]
                if len(matches) != 1:
                    raise ValueError('原检索种子prompt不唯一')
                text = matches[0].split('\n【参考内容】\n',1)[1].split('\n【历史对话】\n',1)[0]
                blocks = list(re.finditer(r'^\[(\d+)\] \[local\] \[chunk_id=([^\]]+)\](.*)\n', text, re.M))
                if len(blocks) != len(run['citations']):
                    raise ValueError('原检索prompt与引用数量不一致')
                traces = {row['chunk_uid']: row['stages'] for row in run['retrieval_trace']}
                for block, cite in zip(blocks, run['citations']):
                    uid = cite['chunk_uid']
                    source = by_uid[uid]
                    if uid != block[2] or source['text'] != cite['text']:
                        raise ValueError('原检索种子与完整标量不一致')
                    stages = traces.get(uid, [])
                    seed = RetrievalHit(**{k: source[k] for k in ('document_id','revision_id','chunk_uid','ordinal','text','metadata')},
                        stages=[StageScore.model_validate(s) for s in stages]).document()
                    seeds.append(seed)
            inputs = dict(question=question, product_ids=product_ids,
                query_plan=serialize_query_plan(plan, include_comparison=True), seeds=seeds, groups=groups)
            result = assemble_member(config, pool, inputs)
            if result is not None:
                replay = read(prepared.parent/f'saved-input-replay-r2/v{n}/{qid}.json')
                if result['prompt'] != replay['prompt']:
                    raise ValueError(f'保存回放prompt不匹配:v{n}:{qid}')
            identity = dict(candidate_slot=f'm6-feedback-stage-r1-v{n}', version=n,
                ordinal=member['ordinal'], question_id=qid, fixed_slot=member['slot'], split='dev',
                route=plan.route, expected_generation=member['expected_generation'], max_provider_streams=member['max_provider_streams'])
            entry = dict(member=identity, question=question, production_input=dict(inputs=inputs, result=result))
            entries.append(entry)
            order.append(identity['fixed_slot'])
    shared = 'product_knowledge_rag_m6_eval_control'
    manifest = dict(version=risk.VERSION, batch_slot=risk.BATCH, authorization_path=risk.AUTHORIZATION_PATH,
        shared_control_database=shared, expected_members=170, expected_generated_members=168,
        expected_clarifications=2, candidate_versions=candidates, entries=entries, dispatch_order=order,
        frozen_scalar_payloads=pool, source_origin=dict(kind='live_strong_scalar_projection', queries=4,
            vectors_read=False, fresh_retrieval=False, seed_origin='immutable_previous_same_scope_retrieval'))
    save(out/'catalog/catalog-production.json', catalog)
    validate_production_manifest(manifest)
    save(out/'production-manifest-private.json', manifest)
    save(out/'preparation-summary.json', dict(status='passed', members=170, generated=168, clarifications=2,
        production_prompts_frozen=168, full_scalar_members=582, live_scalar_queries=4, new_provider_streams=0,
        new_local_inference=0, formal_experiments=0, production_manifest_sha256=fingerprint(manifest),
        file_sha256=file_sha(out/'production-manifest-private.json'), code=code))
    print(json.dumps(dict(status='passed', production_prompts_frozen=168, full_scalar_members=582,
        members=170, new_provider_streams=0), ensure_ascii=False))


if __name__ == '__main__':
    main()
