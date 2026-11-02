"""确定性主体与查询计划；不调用生成模型补写用户未确认的事实。"""
import re
from app.conversations.context import recent_product_context
from app.products.resolver import resolve_catalog
from .models import QueryPlan


_COMPARISON_DIMENSIONS = (
    ('device_uplink', re.compile(r'上联方式|上联链路|uplink', re.IGNORECASE)),
    ('client_access', re.compile(r'客户端访问|用户访问|访问方式', re.IGNORECASE)),
    ('management_link', re.compile(r'管理连接|管理链路|management\s+link', re.IGNORECASE)),
    ('diagnostic_check', re.compile(r'排障检查|物理检查|检查条件|diagnostic\s+check', re.IGNORECASE)),
)


def _comparison_target(question, route):
    if route != 'compare':
        return None, 'not_comparison'
    matches = {target for target, pattern in _COMPARISON_DIMENSIONS if pattern.search(question)}
    if len(matches) > 1:
        return None, 'ambiguous_targets'
    if matches == {'device_uplink'}:
        return 'device_uplink', 'explicit_single_target'
    return None, 'unsupported_or_missing_target'


def serialize_query_plan(plan, *, include_comparison=False):
    value = plan.model_dump(mode='json')
    if include_comparison:
        value['comparison_target'] = plan.comparison_target
        value['comparison_target_reason'] = plan.comparison_target_reason
    return value


def plan_query(question, products, *, selected_ids=(), requested_ids=(), messages=(), confirmed=False,
               context_reset=False, candidate_search=None):
    directory = {p['product_id']: p for p in products}
    if not set(selected_ids) <= directory.keys() or not set(requested_ids) <= directory.keys():
        raise ValueError('输入选择不在当前授权产品目录')
    resolution = resolve_catalog(question, products)
    base = {'original_query': question, 'search_queries': (question,), 'unconfirmed_tokens': resolution.unknown_tokens}
    slots = {}
    for label, key in [('功能', 'function'), ('现象', 'symptom'), ('环境', 'environment'), ('已尝试', 'tried')]:
        match = re.search(label + r'[:：]\s*([^，；\n]+)', question)
        if match: slots[key] = match[1].strip()
    error = re.search(r'(?:错误码|报错|故障码)\s*[:：]?\s*([A-Za-z0-9_-]+)', question)
    if error: slots['error_code'] = error[1]
    def finish(ids, route, reason):
        ids = tuple(ids)
        if ids: slots['device'] = '、'.join(directory[pid]['model'] for pid in ids)
        groups = tuple((pid,) for pid in ids) if route == 'compare' else (ids,)
        values = dict(base)
        if ids and reason == 'confirmed_context' and re.search(r'它|该设备|这个型号|上述设备|那个型号', question):
            values['rewritten_query'] = f'设备型号：{slots["device"]}\n原问题：{question}'
            values['search_queries'] = (values['rewritten_query'],)
        target, target_reason = _comparison_target(question, route)
        return QueryPlan(**values, product_ids=ids, route=route, slots=slots, scope_groups=groups,
            reason=reason, comparison_target=target, comparison_target_reason=target_reason)
    def clarify(ids, reason):
        return QueryPlan(**base, route='clarify', candidates=tuple(dict.fromkeys(ids)), slots=slots, reason=reason)
    if confirmed and selected_ids:
        return finish(selected_ids, 'compare' if len(selected_ids) > 1 else 'answer', 'user_confirmed')
    if resolution.unknown_tokens:
        candidates = candidate_search(question, products) if candidate_search else list(directory)
        candidates = [pid for pid in candidates if pid in directory]
        return clarify([*resolution.exact, *candidates] or directory, 'unconfirmed_model')
    exact = resolution.exact
    switch = re.search(r'(?:切换到|改看|改用|换成|改成|现在使用|现在用|现在是)\s*[:：]?\s*(.+)', question)
    if switch:
        target = resolve_catalog(switch[1], products)
        if len(target.exact) == 1 and not target.unknown_tokens:
            return finish(target.exact, 'answer', 'explicit_switch')
    if len(exact) > 1:
        return finish(exact, 'compare', 'explicit_comparison') if re.search(r'比较|对比|区别|分别|差异', question) else clarify(exact, 'ambiguous_model')
    if exact: return finish(exact, 'answer', 'catalog_exact')
    if re.search(r'不限定型号|不指定型号|所有设备|所有型号|通用问题', question):
        return finish((), 'general', 'explicit_general')
    if resolution.series: return finish(resolution.series, 'series', 'catalog_series')
    recent, history_reset = recent_product_context(messages, directory)
    context_reset = context_reset or history_reset
    if not recent and not context_reset:
        # 老历史若未记录型号快照，仅信任用户自己明确说出的单一目录型号。
        for message in reversed(messages):
            if message.get('role') != 'user': continue
            prior = resolve_catalog(message['text'], products)
            if len(prior.exact) == 1 and not prior.unknown_tokens: recent = prior.exact
            break
    if requested_ids:
        if recent and set(recent) != set(requested_ids) and re.search(r'它|该设备|这个型号|上述设备|那个型号', question):
            return clarify([*requested_ids, *recent], 'selection_context_conflict')
        selected = tuple(requested_ids)
    else:
        selected = recent or (() if context_reset else tuple(selected_ids))
    if selected:
        if len(selected) > 1 and not re.search(r'比较|对比|区别|分别|差异', question):
            return clarify(selected, 'multiple_selected_models')
        return finish(selected, 'compare' if len(selected) > 1 else 'answer', 'confirmed_context' if recent else 'explicit_selection')
    if re.search(r'什么是|基本原理|一般.*注意事项|通用', question): return finish((), 'general', 'general_question')
    if context_reset and products: return clarify(tuple(directory), 'model_required_after_context_reset')
    if len(products) == 1: return finish(tuple(directory), 'answer', 'single_catalog_model')
    if not products: return finish((), 'insufficient', 'empty_catalog')
    candidates = candidate_search(question, products) if candidate_search else list(directory)
    return clarify([pid for pid in candidates if pid in directory] or directory, 'model_required')
