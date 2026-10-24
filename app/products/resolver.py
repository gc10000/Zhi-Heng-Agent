"""目录标准名/别名先精确匹配；相似型号仅作为待确认候选。"""
from dataclasses import dataclass
import re
import unicodedata


def normalized(value):
    return re.sub(r'[\s_-]+', '', unicodedata.normalize('NFKC', value)).casefold()


def terms(product):
    values = [product['model'], *product.get('aliases', [])]
    # 品牌+型号显示名中的独立型号也是确定的目录标识，不凭空生成近型号。
    values.extend(token for token in re.findall(r'[A-Za-z]+[-_ ]?\d[A-Za-z0-9_.-]*', product['model'])
                  if len(normalized(token)) >= 4)
    return {normalized(v) for v in values if v and normalized(v)}


def occurrences(question, term):
    pattern = r'[\s_-]*'.join(re.escape(c) for c in term)
    if term[0].isascii() and term[0].isalnum(): pattern = r'(?<![a-zA-Z0-9])' + pattern
    if term[-1].isascii() and term[-1].isalnum(): pattern += r'(?![a-zA-Z0-9])'
    return list(re.finditer(pattern, unicodedata.normalize('NFKC', question).casefold()))


@dataclass(frozen=True)
class Resolution:
    exact: tuple[str, ...]
    series: tuple[str, ...]
    unknown_tokens: tuple[str, ...]


def interface_identifier(question,start,end):
    """只有明确接口语境识别端口编号；不能借此确认陌生设备型号。"""
    token=question[start:end].rstrip('.-_')
    if not re.fullmatch(r'(?:ethernet|gigabitethernet|fastethernet|tengigabitethernet|serial|loopback|vlan|bridge)\d+',token,re.I):return False
    if re.search(r'型号\s*[:：]?\s*$',question[:start]):return False
    return bool(re.match(r'(?:/\d+){0,3}(?:接口|端口)',question[end:]))


def resolve_catalog(question, products):
    question = unicodedata.normalize('NFKC', question)
    found = []
    all_terms = {p['product_id']: terms(p) for p in products}
    for pid, names in all_terms.items():
        for name in names:
            found.extend((m.start(), m.end(), pid) for m in occurrences(question, name))
    # 同一出现位置优先完整型号，避免AX24增强版也命中短型号AX24。
    exact = {pid for start, end, pid in found if not any(
        a <= start and b >= end and b-a > end-start for a, b, _ in found)}
    prefixes = {re.match(r'[a-z]+', name).group() for names in all_terms.values() for name in names
                if re.match(r'[a-z]+\d', name)}
    tokens = list(re.finditer(r'[A-Za-z]+[-_ ]?\d[A-Za-z0-9_.-]*', question))
    known = set().union(*all_terms.values()) if all_terms else set()
    known.update(normalized(p[k]) for p in products for k in ('brand', 'series') if p.get(k))
    protocol_terms = {'ipv4', 'ipv6', 'rs485', 'rs232', 'rj45', 'cat5', 'cat5e', 'cat6', 'ieee802.11'}
    unknown = []
    for match in tokens:
        token = match[0].rstrip('.-_')
        if interface_identifier(question,match.start(),match.end()):continue
        if re.search(r'(?:错误码|报错|故障码|端口|寄存器)\s*[:：]?\s*$', question[:match.start()]):
            continue
        name = normalized(token); prefix = re.match(r'[a-z]+', name).group()
        protocol = prefix in {'ipv', 'http', 'tcp', 'udp', 'rs', 'rj', 'ieee', 'cat',
                              'ubuntu', 'windows', 'debian', 'centos', 'rhel', 'python', 'linux', 'macos'}
        explicit = bool(re.search(r'型号\s*[:：]?\s*' + re.escape(token), question, re.I))
        if name not in known and name not in protocol_terms and (explicit or (not protocol and (prefix in prefixes or len(prefix) >= 2))):
            unknown.append(token)
    for match in re.finditer(r'型号(?:是|为)?\s*[:：]?\s*([A-Za-z0-9][A-Za-z0-9_.-]*)', question):
        token = match[1].rstrip('.-_')
        if normalized(token) not in known: unknown.append(token)
    uncertain = re.search(r'型号(?:不确定|不清楚|未知|未确认)|不知道(?:设备)?型号', question)
    if uncertain: unknown.append(uncertain[0])
    series = {p['product_id'] for p in products if any(occurrences(question, normalized(p[k]))
        for k in ('series', 'brand') if p.get(k))}
    return Resolution(tuple(sorted(exact)), tuple(sorted(series)), tuple(dict.fromkeys(unknown)))
