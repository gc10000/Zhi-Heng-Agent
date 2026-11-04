"""两版完整候选的冻结标量与正式prompt重算；不创建模型或访问业务状态。"""
from copy import deepcopy

from app.knowledge.repository import fingerprint


def validate_scalar_pool(config, rows):
    from app.answering.comparison_context import _checked_row
    attribution = config['parameters']['evidence_attribution']
    scope = attribution['scope']
    frozen = attribution['source_relations']['frozen_payloads']
    checked = [_checked_row(row, scope, frozen) for row in rows]
    if len(checked) != len(frozen) or {row['chunk_uid'] for row in checked} != set(frozen):
        raise ValueError('完整反馈输入缺失、重复或增加冻结标量成员')
    return sorted(checked, key=lambda row: row['chunk_uid'])


def assemble_member(config, pool, inputs):
    from app.answering.service import AnswerBudget
    from app.retrieval.models import QueryPlan
    from app.runs.query_runner import QueryRunner
    from app.answering.comparison_context import _checked_row
    from .connection_048_inputs import assemble_input

    inputs = deepcopy(inputs)
    question = inputs['question']
    plan = QueryPlan.model_validate(inputs['query_plan'])
    if plan.original_query != question['question']:
        raise ValueError('生产输入规划与原题不一致')
    if plan.route == 'clarify':
        if inputs['seeds'] or inputs['groups']:
            raise ValueError('澄清输入不能携带生成来源')
        return None
    if plan.route == 'compare':
        return assemble_input(config, inputs | {'frozen_scalar_payloads': pool})['result']
    attribution = config['parameters']['evidence_attribution']
    for seed in inputs['seeds']:
        _checked_row(seed, attribution['scope'], attribution['source_relations']['frozen_payloads'])
    runner = object.__new__(QueryRunner)
    runner.answer_budget = AnswerBudget.model_validate(config['parameters']['answer_budget'])
    runner.evidence_attribution = deepcopy(attribution)
    products = config['corpus']['snapshot']['products']
    names = [p['model'] for p in products if p['product_id'] in plan.product_ids]
    state, prompt = runner.evidence_prompt(question['question'], inputs['seeds'], inputs['groups'], plan,
        item_names=names, history=question['history'], session_id='m6-feedback-production-freeze')
    refs = state['prompt_reference_map']
    if (not prompt or state.get('comparison_answer_short_circuit') or
            [r['reference_number'] for r in refs] != list(range(1, len(refs) + 1)) or
            state['prompt_budget']['input_limit'] != 28416 or
            state['prompt_budget']['input_tokens'] > 28416 or
            state['prompt_budget']['omitted_documents'] or state['prompt_budget']['omitted_history']):
        raise ValueError('完整候选输入必须保留连续引用、完整来源与历史且预算内')
    return dict(prompt=prompt, context=state['prompt_used_docs'], prompt_reference_map=refs,
        groups=state['evidence_groups'], budget=state['prompt_budget'])


def validate_member(config, pool, entry):
    validate_input_plan(config, entry)
    production = entry['production_input']
    result = assemble_member(config, pool, production['inputs'])
    if result != production['result']:
        raise ValueError('完整候选prompt、来源、引用、分组或预算不能从冻结标量重算')
    return result


def validate_input_plan(config, entry):
    """冻结路由和主体来自原题及授权产品目录，不能由自洽prompt另行声明。"""
    from app.retrieval.models import QueryPlan
    from app.retrieval.query_planner import plan_query
    question = entry['question']
    inputs = entry['production_input']['inputs']
    plan = QueryPlan.model_validate(inputs['query_plan'])
    products = config['corpus']['snapshot']['products']
    by_name = {p['model']: p['product_id'] for p in products}
    try:
        requested = [by_name[name] for name in question['product_names']]
    except KeyError:
        raise ValueError('冻结原题指定产品不在授权目录') from None
    expected = plan_query(question['question'], products, requested_ids=requested, messages=question['history'])
    fields = ('original_query', 'product_ids', 'route', 'scope_groups', 'slots', 'search_queries',
        'rewritten_query', 'comparison_target', 'comparison_target_reason')
    revisions = config['parameters']['evidence_attribution']['scope']['revisions']
    expected_revisions = set(revisions.values()) if plan.route != 'clarify' else set()
    if (entry['member']['question_id'] != question['id'] or inputs['question'] != question or
            entry['member']['route'] != plan.route or list(plan.product_ids) != inputs['product_ids'] or
            any(getattr(plan, field) != getattr(expected, field) for field in fields) or
            set(plan.revision_ids) != expected_revisions or len(plan.revision_ids) != len(expected_revisions)):
        raise ValueError('生产输入路由、产品、原题或冻结修订规划漂移')
    return plan


def validate_production_manifest(manifest):
    from app.infrastructure.providers import m6_feedback_candidate_risk as risk
    from .runner import select_questions
    from .validate_dataset import validate_dataset, file_sha
    from app.infrastructure.providers.product_risk import code_version
    risk.validate_full_dispatch(manifest)
    candidates = manifest.get('candidate_versions', [])
    if len(candidates) != 2 or {v['candidate_slot'] for v in candidates} != set(risk.CANDIDATE_SLOTS):
        raise ValueError('完整生产清单必须包含两版唯一配置')
    for version in candidates:
        config = version['config_subject']
        if (risk.config_subject(config) != config or
                config['versions']['code'] != code_version() or
                config['versions'] != version['versions']):
            raise ValueError('生产输入配置必须关闭且绑定当前源码')
        pool = validate_scalar_pool(config, manifest['frozen_scalar_payloads'])
        dataset, split = (risk.local(version[k]['path']) for k in ('dataset', 'split_manifest'))
        if file_sha(dataset) != config['dataset_sha256'] or file_sha(split) != config['split_manifest_sha256']:
            raise ValueError('生产清单题集或划分字节漂移')
        questions = select_questions(validate_dataset(dataset, manifest=split), config)
        ids = [q['id'] for q in questions]
        if sorted(ids) != sorted(version['question_ids']) or len(ids) != 85:
            raise ValueError('完整反馈生产范围不是对应全部85道dev题')
        questions = {q['id']: q for q in questions}
        entries = [e for e in manifest['entries'] if e['member']['candidate_slot'] == version['candidate_slot']]
        if [e['member']['question_id'] for e in entries] != version['question_ids']:
            raise ValueError('生产清单派发顺序漂移')
        for entry in entries:
            qid = entry['member']['question_id']
            question = {k: questions[qid][k] for k in ('id', 'question', 'product_names', 'history')}
            if entry['question'] != question or entry['production_input']['inputs']['question'] != question:
                raise ValueError('生产输入包含非本题输入或额外答案字段')
            result = validate_member(config, pool, entry)
            if bool(result) != entry['member']['expected_generation']:
                raise ValueError('生产输入生成类别与冻结路由漂移')
    return manifest
