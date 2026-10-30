"""默认关闭的来源术语隔离投影；不改变产品路由、预算、正文或能力判断。"""
import hashlib
import json
import re
from .models import QueryPlan

VERSION = 'source_network_terms_v1'
_TERM = r'[A-Za-z0-9][A-Za-z0-9+./-]{1,23}'
_NETWORK = re.compile(r'(?<![A-Za-z0-9+./-])('+_TERM+r')\s*网络'
                      r'(?=$|\s*(?:[，。；、:：]|和|与|的|连接|接入|$))')
_TOPIC = re.compile(r'上联|上行|广域网|\b(?:WAN|uplink)\b', re.I)


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                    separators=(',', ':')).encode()).hexdigest()


def collect_network_terms(rows, *, revision_ids, product_ids):
    """只从已授权正文概述/产品简介提取字面网络介质名，不读取题目或答案。

    术语不是上联能力证明。每修订最多两个、总计最多四个；超限整体不用，
    不挑有利子集。故障排查、图摘要、未知出处不能为术语提供依据。
    """
    found = {}
    for row in sorted(rows, key=lambda r:r['chunk_uid']):
        metadata = row['metadata']
        products = metadata.get('product_ids', [])
        refs = metadata.get('source_refs', [])
        if (row['revision_id'] not in revision_ids or not products or
                not set(products) <= set(product_ids) or any(
                    ref.get('document_id') != row['document_id'] or
                    ref.get('revision_id') != row['revision_id'] for ref in refs)):
            raise ValueError('术语来源超出已授权产品/修订或引用映射不一致')
        heading = '/'.join(metadata.get('heading_path', []))
        if (metadata.get('content_kind') == 'image_description' or
                not re.search(r'(?:概述|产品简介)(?:$|/)', heading) or not refs or
                any(ref.get('page') is None or ref.get('kind') != 'pdf' for ref in refs)):
            continue
        payload = {k:row[k] for k in ('chunk_uid','document_id','revision_id','text','metadata')}
        for match in _NETWORK.finditer(row['text']):
            key = row['revision_id'], match[1].casefold()
            value = dict(term=match[1], document_id=row['document_id'],
                         revision_id=row['revision_id'], product_ids=sorted(products),
                         chunk_uid=row['chunk_uid'], chunk_sha256=_digest(payload),
                         heading_path=metadata.get('heading_path', []), source_refs=refs,
                         literal=match[0], version=VERSION)
            found.setdefault(key, value | {'sha256':_digest(value)})
    if len(found)>4 or any(sum(rid==key[0] for key in found)>2 for rid,_ in found):
        return []
    return [found[key] for key in sorted(found)]


def project_network_terms(plan, terms, *, enabled=False):
    """调用方逐授权scope使用；只追加原件字面术语，不改原题及生成输入。"""
    plan = QueryPlan.model_validate(plan)
    if not enabled or plan.route not in {'answer','compare'} or plan.unconfirmed_tokens:
        return plan
    if len(terms)>4:
        raise ValueError('术语投影超过固定预算')
    for term in terms:
        payload = {k:v for k,v in term.items() if k != 'sha256'}
        if (_digest(payload) != term.get('sha256') or term.get('version') != VERSION or
                term['revision_id'] not in plan.revision_ids or
                not set(term['product_ids']) <= set(plan.product_ids) or
                re.fullmatch(_TERM, term['term']) is None):
            raise ValueError('术语指纹、版本或产品/修订范围变化')
    names = sorted({t['term'] for t in terms}, key=str.casefold)
    if not names:
        return plan
    suffix = '\n原件网络介质术语：'+'、'.join(names)
    queries = tuple(q+suffix if _TOPIC.search(q) and not re.search(r'[`~<>\r\n]',q)
                    else q for q in plan.search_queries)
    return plan.model_copy(update={'search_queries':queries})
