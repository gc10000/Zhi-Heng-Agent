"""型号确认产生本轮新快照，保留之前消息的原始选择。"""
from app.api.errors import APIError


def confirm_snapshot(row, product_ids):
    allowed = {candidate['product_id'] for candidate in row['candidates']}
    if not product_ids or len(product_ids) != len(set(product_ids)) or not set(product_ids) <= allowed:
        raise APIError(422, 'invalid_candidate', '请选择本次提供的候选型号。')
    return {'product_ids': list(product_ids), 'version': row['product_snapshot']['version'] + 1}


def recent_product_ids(messages, known_ids):
    """只继承本会话的已持久、仍在当前目录范围内的快照，不重写旧消息。"""
    return recent_product_context(messages, known_ids)[0]


def recent_product_context(messages, known_ids):
    """成功助手快照才是已确认上下文；通用问题构成显式清空边界。"""
    for message in reversed(messages):
        if message.get('role') != 'assistant': continue
        snapshot = message.get('product_snapshot', {})
        if snapshot.get('context_route') == 'general': return (), True
        ids = snapshot.get('product_ids', [])
        if ids: return (tuple(ids), False) if set(ids) <= set(known_ids) else ((), True)
    return (), False


def support_history(snapshot):
    """只汇入用户确认事实和最新自报结果，AI建议始终标记未执行。"""
    if not snapshot:
        return []
    import json
    facts = {key: slot['value'] for key, slot in snapshot['slots'].items() if slot.get('confirmed') and slot.get('value')}
    steps = [{'suggestion': step['suggestion'], 'execution_source': 'user_report',
              'status': step['status'], 'reports': step.get('reports', [])[-1:]} for step in snapshot.get('operations', [])]
    text = '用户确认的支持上下文（仅用户自报，系统未实际操作设备）：' + json.dumps(
        {'context_version': snapshot['context_version'], 'facts': facts, 'steps': steps}, ensure_ascii=False)
    text += '\n标记ineffective的步骤已由用户自报无效，不要重复建议；若无新的可追溯操作证据，应说明不足并转交人工。'
    return [{'role': 'user', 'text': text}]
