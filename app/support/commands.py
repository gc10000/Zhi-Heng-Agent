"""支持上下文纠正只影响未来运行；已开始运行使用不可变快照。"""
from copy import deepcopy
from app.api.errors import APIError


def freeze_support(conversation):
    context = conversation.get('support')
    if not context or context['state'] in {'cancelled', 'resolved'}:
        return None
    row = {key: deepcopy(context[key]) for key in ('version','context_version','state','slots','run_id')}
    row['subject_withdrawn'] = bool(context.get('subject_withdrawn'))
    # r2撤回记录依靠history.withdrawal表达，保留它供升级后的查询边界识别。
    row['history'] = deepcopy(context.get('history', []))
    row['operations'] = [{key: deepcopy(step[key]) for key in ('operation_id','suggestion','status','citation_ids')} |
                         {'reports': deepcopy(step['reports'][-1:])} for step in context['operations']]
    return row


def check_run_context(context, run, *, allow_bound=False):
    if allow_bound and context.get('run_id') == run['run_id'] and context.get('evidence_slots') == context['slots']:
        return
    snapshot = run.get('support_snapshot')
    if snapshot is not None:
        if snapshot['context_version'] != context['context_version']:
            raise APIError(409, 'support_context_changed', '运行使用的支持上下文已过期，请依据当前信息新建问答。')
    elif context.get('run_id'):
        raise APIError(409, 'support_context_changed', '旧回答不能替换当前支持上下文；请新建问答。')


def product_context(snapshot, products):
    """用户明确确认的设备槽位才可成为未来问答的主体；目录不匹配仍需澄清。"""
    if not snapshot:
        return None
    device = snapshot['slots'].get('device', {})
    if not device.get('confirmed') or not device.get('value'):
        return None
    from app.products.resolver import resolve_catalog
    result = resolve_catalog(device['value'], products)
    return result.exact if len(result.exact) == 1 and not result.unknown_tokens else ()


def subject_withdrawn(snapshot):
    """撤回设备后形成未来轮主体边界，不能由旧历史或唯一目录项补回。"""
    if not snapshot:
        return False
    device = snapshot.get('slots', {}).get('device', {})
    # 当前已确认的设备是新的有效主体，不能被更早的撤回历史永久覆盖。
    if device.get('confirmed') and device.get('value'):
        return False
    if snapshot.get('subject_withdrawn'):
        return True
    # r2快照没有新增标记，但合法撤回会保留清空后的设备槽位和撤回操作者。
    if (device.get('value') is None and not device.get('confirmed')
            and device.get('source') == 'unknown' and device.get('withdrawn_by')):
        return True
    return any('device' in entry.get('withdrawal', {}).get('slots', [])
               for entry in snapshot.get('history', []))
