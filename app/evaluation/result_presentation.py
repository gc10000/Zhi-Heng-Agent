"""评测结果只带公开型号选择字段，不传递内部Run或租约内容。"""


def public_candidates(rows, authorized=None):
    allowed = set(authorized) if authorized is not None else None
    result = []
    seen = set()
    for row in rows if isinstance(rows, list) else []:
        if not isinstance(row, dict):
            continue
        pid, model = row.get('product_id'), row.get('model')
        if (not isinstance(pid, str) or not pid or not isinstance(model, str) or not model or
                pid in seen or allowed is not None and pid not in allowed):
            continue
        seen.add(pid)
        result.append(dict(product_id=pid, model=model))
    return result
