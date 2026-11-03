"""连接比较的调用前输入锚；先于供应商调用且独立于可恢复Run输出保存。"""
from pymongo.errors import DuplicateKeyError

from app.knowledge.repository import fingerprint


VERSION = 'connection_generation_input_v1'
_FIELDS = ('comparison_context_assembly', 'prompt_used_docs', 'prompt_reference_map',
    'comparison_policy_sha256', 'comparison_prompt_used_sha256', 'comparison_target')


def input_sha256(value):
    if any(key not in value for key in _FIELDS):
        raise ValueError('连接比较缺少调用前完整输入')
    product_ids = value.get('comparison_product_ids', (value.get('product_snapshot') or {}).get('product_ids'))
    labels = value.get('comparison_product_labels')
    if labels is None:
        products = (value.get('evidence_attribution') or {}).get('products') or {}
        labels = {pid: products[pid] for pid in product_ids or [] if pid in products}
    from app.answering.evidence_attribution import EvidenceAttributionPolicy
    policy = EvidenceAttributionPolicy.model_validate(value.get('evidence_attribution') or {})
    return fingerprint({key: value[key] for key in _FIELDS} | dict(
        product_ids=product_ids, product_labels=labels,
        evidence_attribution_sha256=fingerprint(policy.model_dump(mode='json'))))


def install_input_guard(state):
    """闭包捕获已核验prompt的身份，缓存/断流不能重写state内摘要自证。"""
    expected = input_sha256(state)
    def guard(current):
        if input_sha256(current) != expected:
            raise ValueError('连接比较输入与调用前核验身份不一致')
    state['_connection_input_guard'] = guard


def validate_input_guard(state):
    guard = state.get('_connection_input_guard')
    if not callable(guard):
        raise ValueError('连接比较缺少调用前输入核验器')
    guard(state)


def validate_input_mode(state, policy):
    """已冻结连接输入不能通过关闭比较开关而走自由回答或缓存快捷路径。"""
    mode = policy.comparison_answer
    configured = mode is not None and mode.enabled and mode.function_version == 'connection_comparison_v1'
    if (state.get('comparison_context_assembly') is not None or '_connection_input_guard' in state or
            (configured and state.get('comparison_target') is not None)):
        if not configured or state.get('comparison_mode') is not True:
            raise ValueError('冻结连接比较输入不能降级为自由回答')
        validate_input_guard(state)


def _identity(run, inputs):
    return dict(function_version=VERSION, run_id=run['run_id'],
        run_identity=run['identity'], owner_id=run['owner_id'], kb_id=run['kb_id'],
        input_sha256=input_sha256(inputs))


def validate_frozen_input(db, run, *, inputs=None):
    expected = _identity(run, run if inputs is None else inputs)
    saved = db.comparison_generation_inputs.find_one({'_id': run['run_id']})
    if saved != dict(expected, _id=run['run_id']):
        raise ValueError('连接比较输入与独立保存的调用前记录不一致')
    return expected


def freeze_input(db, run, state):
    """仅首次生成调用；恢复只校验，不能在缺记录时补签或覆盖。"""
    validate_input_guard(state)
    expected = _identity(run, state)
    try:
        db.comparison_generation_inputs.update_one({'_id': run['run_id']},
            {'$setOnInsert': expected}, upsert=True)
    except DuplicateKeyError:
        pass
    return validate_frozen_input(db, run, inputs=state)
