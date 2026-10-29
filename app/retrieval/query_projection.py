"""型号已由授权过滤固定时，显式隔离功能检索词；不修改原题和生成输入。"""
import re
import unicodedata
from .models import QueryPlan
from app.products.resolver import terms, occurrences, normalized
from app.products.equivalences import SOURCE_ACCESSORIES, SOURCE_EQUIVALENCES


def project_scoped_subject(plan, products):
    plan = QueryPlan.model_validate(plan)
    if plan.route not in {'answer', 'compare'} or plan.unconfirmed_tokens or not plan.product_ids:
        return plan
    directory = {p['product_id']: p for p in products}
    if not set(plan.product_ids) <= directory.keys():
        raise ValueError('查询投影缺少已授权产品身份')
    selected = [directory[pid] for pid in plan.product_ids]
    accessories = {normalized(a.name) for a in SOURCE_ACCESSORIES}
    variants = {normalized(e.variant) for e in SOURCE_EQUIVALENCES}
    queries = []
    for text in plan.search_queries:
        # 不在代码/参数/多行或规范化坐标不确定时改写；版本变体保留完整检索身份。
        transformed = [unicodedata.normalize('NFKC', ch).casefold() for ch in text]
        if (any(len(ch) != 1 for ch in transformed) or
                ''.join(transformed) != unicodedata.normalize('NFKC', text).casefold() or
                re.search(r'[`~<>\r\n]', text) or
                any(occurrences(text, v) for v in variants)):
            queries.append(text)
            continue
        spans = []
        for product in selected:
            for term in terms(product) - accessories:
                spans.extend((m.start(), m.end()) for m in occurrences(text, term))
        kept = []
        for start, end in sorted(set(spans), key=lambda value: (value[0], -value[1])):
            if kept and start < kept[-1][1]:
                continue
            kept.append((start, end))
        for start, end in reversed(kept):
            text = text[:start] + '该设备' + text[end:]
        queries.append(text)
    return plan.model_copy(update={'search_queries': tuple(queries)})
