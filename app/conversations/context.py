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
