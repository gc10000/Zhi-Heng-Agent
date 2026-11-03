"""完整冻结来源池的确定性装配；不检索、推理或改变旧回答路径。"""
from copy import deepcopy
from dataclasses import dataclass
import re

from app.knowledge.models import content_hash
from app.knowledge.repository import fingerprint


VERSION = 'comparison_source_assembly_v1'
_PAYLOAD_FIELDS = ('chunk_uid', 'owner_id', 'kb_id', 'document_id', 'revision_id',
    'ordinal', 'text', 'metadata', 'content_sha256')
_INTRO_TITLES = {'产品简介', '产品概述', '概述'}


@dataclass(frozen=True)
class ContextAssembly:
    documents: list
    dependencies: list
    dropped: list
    status: str
    issues: list
    identity_sha256: str


def _checked_row(row, scope, frozen_payloads):
    if not isinstance(row, dict):
        raise ValueError('比较资料载荷必须是对象')
    # prompt-used文档可以省略归属和内容hash；按显式范围补出后仍须逐字匹配冻结payload。
    value = dict(row)
    value.setdefault('owner_id', scope['owner_id'])
    value.setdefault('kb_id', scope['kb_id'])
    text = value.get('text')
    if not isinstance(text, str) or not text.strip():
        raise ValueError('比较资料缺少完整正文')
    value.setdefault('content_sha256', content_hash(text.encode('utf-8')))
    if any(k not in value for k in _PAYLOAD_FIELDS):
        raise ValueError('比较资料缺少冻结载荷字段')
    raw = {k: value[k] for k in _PAYLOAD_FIELDS}
    if (type(raw['ordinal']) is not int or raw['ordinal'] < 0 or
            raw['owner_id'] != scope['owner_id'] or raw['kb_id'] != scope['kb_id'] or
            scope['revisions'].get(raw['document_id']) != raw['revision_id'] or
            raw['content_sha256'] != content_hash(text.encode('utf-8')) or
            fingerprint(raw) != frozen_payloads.get(raw['chunk_uid'])):
        raise ValueError('比较资料归属、正文或冻结载荷漂移')
    meta = raw['metadata']
    if (not isinstance(meta, dict) or not isinstance(meta.get('product_ids'), list) or
            not meta['product_ids'] or len(set(meta['product_ids'])) != len(meta['product_ids']) or
            not set(meta['product_ids']) <= set(scope['product_ids'])):
        raise ValueError('比较资料产品归属超出冻结范围')
    refs = meta.get('source_refs')
    headings = meta.get('heading_path')
    if (not isinstance(refs, list) or not refs or
            any(not isinstance(r, dict) or r.get('document_id') != raw['document_id'] or
                r.get('revision_id') != raw['revision_id'] for r in refs) or
            not isinstance(headings, list) or any(not isinstance(h, str) for h in headings) or
            ('source_refs' in row and row['source_refs'] != refs)):
        raise ValueError('比较资料来源定位或章节结构漂移')
    return deepcopy(raw)


def _introduction_root(path):
    if not path:
        return False
    title = re.sub(r'^\s*\d+(?:\.\d+)*[.、]?\s*', '', path[-1]).strip()
    return title in _INTRO_TITLES


def assemble_comparison_context(selected_docs, frozen_pool, *, product_ids, scope,
        frozen_payloads, max_docs, max_chars, required_chunk_uids=None):
    """只装配来源；必要集合省略时保守地保留全部已选资料。

    frozen_payloads须由完整冻结快照按scope投影，frozen_pool必须成员全等。
    调用方不得删掉冲突候选后自报一个更小的“完整”映射。
    字符预算计正文和段间两个换行；完整prompt/token预算仍由既有预算器核验。
    """
    if (not isinstance(scope, dict) or not scope.get('owner_id') or not scope.get('kb_id') or
            not isinstance(scope.get('revisions'), dict) or not scope['revisions'] or
            not isinstance(scope.get('product_ids'), (list, tuple)) or
            not isinstance(product_ids, (list, tuple)) or not product_ids or
            any(not isinstance(p, str) or not p for p in product_ids) or
            len(set(product_ids)) != len(product_ids) or
            not set(product_ids) <= set(scope['product_ids']) or
            not isinstance(frozen_payloads, dict) or not frozen_payloads or
            type(max_docs) is not int or not 1 <= max_docs <= 100 or
            type(max_chars) is not int or not 1 <= max_chars <= 1_000_000 or
            not isinstance(frozen_pool, list) or len(frozen_pool) > 1000 or
            not isinstance(selected_docs, list) or len(selected_docs) > 100):
        raise ValueError('比较装配缺少有效范围、来源池或有界预算')
    pool = {}
    for item in frozen_pool:
        row = _checked_row(item, scope, frozen_payloads)
        uid = row['chunk_uid']
        if uid in pool:
            raise ValueError('完整来源池含重复成员')
        pool[uid] = row
    if set(pool) != set(frozen_payloads):
        raise ValueError('来源池与完整冻结成员不一致')
    selected = []
    for item in selected_docs:
        row = _checked_row(item, scope, frozen_payloads)
        uid = row['chunk_uid']
        if uid in selected:
            raise ValueError('已选来源含重复成员')
        if uid not in pool or row != pool[uid] or not set(row['metadata']['product_ids']) <= set(product_ids):
            raise ValueError('已选来源不在本轮产品及完整冻结池中')
        selected.append(uid)
    required = list(selected if required_chunk_uids is None else required_chunk_uids)
    if (any(not isinstance(uid, str) for uid in required) or
            len(set(required)) != len(required) or not set(required) <= set(selected)):
        raise ValueError('必要来源必须是本轮唯一已选成员')

    roots = {}
    for uid, row in pool.items():
        path = row['metadata']['heading_path']
        if _introduction_root(path) and row['metadata'].get('content_kind') == 'text':
            key = row['document_id'], row['revision_id'], tuple(path)
            roots.setdefault(key, []).append(uid)
    dependencies, issues = [], []
    needed = set(required)
    for pid in product_ids:
        candidates = [key for key, uids in roots.items()
            if any(pid in pool[uid]['metadata']['product_ids'] for uid in uids)]
        if not candidates:
            issues.append(dict(product_id=pid, code='introduction_not_in_frozen_pool'))
            continue
        if len(candidates) != 1:
            issues.append(dict(product_id=pid, code='ambiguous_introduction'))
            continue
        did, rid, path = candidates[0]
        members = [uid for uid, row in pool.items() if
            (row['document_id'], row['revision_id']) == (did, rid) and
            tuple(row['metadata']['heading_path'][:len(path)]) == path]
        if any(pool[uid]['metadata']['product_ids'] != [pid] for uid in members):
            issues.append(dict(product_id=pid, code='ambiguous_introduction_subject'))
            continue
        members.sort(key=lambda uid: (pool[uid]['ordinal'], uid))
        dependencies.append(dict(product_id=pid, reason='complete_product_introduction',
            chunk_uids=members, heading_path=list(path)))
        needed.update(members)

    product_order = {pid: index for index, pid in enumerate(product_ids)}
    def order(uid):
        row = pool[uid]
        return (min(product_order.get(pid, len(product_order)) for pid in row['metadata']['product_ids']),
            row['document_id'], row['revision_id'], row['ordinal'], uid)

    selected_order = sorted(needed, key=order)
    def fits(uids):
        return (len(uids) <= max_docs and
            sum(len(pool[uid]['text']) for uid in uids) + 2 * max(0, len(uids) - 1) <= max_chars)

    dropped = []
    if issues:
        status = ('ambiguous' if any(i['code'].startswith('ambiguous') for i in issues)
            else 'missing_required_source')
        selected_order = []
    elif not fits(selected_order):
        status = 'required_source_budget_exceeded'
        selected_order = []
    else:
        status = 'complete'
        for uid in selected:
            if uid in needed:
                continue
            if fits(selected_order + [uid]):
                selected_order.append(uid)
            else:
                dropped.append(dict(chunk_uid=uid, reason='optional_source_budget'))
        selected_order.sort(key=order)
    identity = dict(function_version=VERSION, scope=scope, product_ids=list(product_ids),
        frozen_pool_sha256=fingerprint(sorted(frozen_payloads.items())),
        selected_chunk_uids=selected, required_chunk_uids=sorted(required),
        max_docs=max_docs, max_chars=max_chars, documents=selected_order,
        dependencies=dependencies, dropped=dropped, status=status, issues=issues)
    return ContextAssembly([deepcopy(pool[uid]) for uid in selected_order], dependencies,
        dropped, status, issues, fingerprint(identity))
