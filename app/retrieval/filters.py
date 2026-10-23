"""过滤由后端构造固定字段，外部输入仅作为JSON字符串值。"""
import json


def literal(value):
    if not isinstance(value,str) or not value:raise ValueError('范围ID必须为非空字符串')
    return json.dumps(value,ensure_ascii=False)


def scoped_filter(*,owner_id,kb_id,revision_ids,document_id=None,product_ids=()):
    revisions='['+', '.join(literal(r) for r in revision_ids)+']'
    expr=f'owner_id == {literal(owner_id)} and kb_id == {literal(kb_id)} and revision_id in {revisions}'
    if document_id is not None:expr+=' and document_id == '+literal(document_id)
    if product_ids:expr+=' and json_contains_any(metadata["product_ids"], ['+', '.join(literal(p) for p in product_ids)+'])'
    return expr
