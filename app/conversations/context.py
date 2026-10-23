"""型号确认产生本轮新快照，保留之前消息的原始选择。"""
from app.api.errors import APIError


def confirm_snapshot(row, product_ids):
    allowed = {candidate['product_id'] for candidate in row['candidates']}
    if not product_ids or len(product_ids) != len(set(product_ids)) or not set(product_ids) <= allowed:
        raise APIError(422, 'invalid_candidate', '请选择本次提供的候选型号。')
    return {'product_ids': list(product_ids), 'version': row['product_snapshot']['version'] + 1}
