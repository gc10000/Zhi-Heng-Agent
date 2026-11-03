"""有界连接语法：来源话语、端点角色、介质、用途和现场状态分别保留。"""
from copy import deepcopy
import html
import re

from app.core.markdown_source import block_code_ranges, inline_code_ranges
from app.knowledge.repository import fingerprint
from app.knowledge.models import content_hash

VERSION = 'connection_comparison_v1'
COMPARABLE_MEDIA = {
    '3g/4g': 'cellular_3g4g', '3g/4g网络': 'cellular_3g4g',
    '同轴': 'coaxial', '同轴电缆': 'coaxial', 'coaxial': 'coaxial',
    '以太网': 'ethernet', 'ethernet': 'ethernet', '光纤': 'fiber', 'fiber': 'fiber',
    'cable': 'cable', 'cable网络': 'cable', 'cellular_3g4g': 'cellular_3g4g',
}
MEDIA_LABELS = {'cellular_3g4g': '3G/4G', 'coaxial': '同轴', 'ethernet': '以太网',
    'fiber': '光纤', 'cable': 'Cable'}
_MEDIA = r'3G/4G网络|3G/4G|同轴电缆|同轴|以太网|Ethernet|光纤|fiber'
_CONDITION = re.compile(r'若|如果|是否|不|未|不能|无法|仅|只有|除非|假设|示例|例如')
_ROLES = {'controller_link', 'documented_physical_path', 'explicit_uplink'}


def _canonical(value):
    return COMPARABLE_MEDIA.get(re.sub(r'\s+', '', value).casefold()) if isinstance(value, str) else None


def _span(text, start, end):
    return dict(start=start, end=end, text=text[start:end], sha256=content_hash(text[start:end].encode('utf-8')))


def _protected(text):
    # 不从HTML、图片或代码中抽取业务关系；原文仍完整保存在scope。
    ranges = block_code_ranges(text) + inline_code_ranges(text)
    for pattern in (r'<([A-Za-z][\w:-]*)\b[^>]*>.*?</\1\s*>', r'<[^>]*>',
                    r'!\[[^\]]*\]\([^\n]*?\)', r'<!--.*?-->'):
        ranges.extend((m.start(), m.end()) for m in re.finditer(pattern, text, re.DOTALL))
    return ranges


def _names(pid, labels):
    names = {'本设备', '该设备', '设备', '本机', '本网关', '本路由器'}
    label = (labels or {}).get(pid)
    if label:
        names.add(label)
        model = label.split()[-1]
        if re.fullmatch(r'[A-Za-z][A-Za-z0-9_.-]*\d[A-Za-z0-9_.-]*', model):
            names.add(model)
    return names


def _source_fact(doc, pid, sentence, start, match, *, role, speech, rule,
                 purpose=None, purpose_span=None, interpretation=None):
    text = doc['text']
    refs = (doc.get('metadata') or {}).get('source_refs', doc.get('source_refs', [])) or []
    exact = bool(refs) and all(r.get('kind') == 'pdf' and type(r.get('page')) is int and
        r['page'] > 0 for r in refs)
    fields = {}
    for name in ('origin', 'medium', 'destination'):
        if name in match.groupdict() and match.group(name):
            a, b = match.span(name)
            fields[name] = _span(text, start + a, start + b)
        else:
            fields[name] = None
    fields['purpose'] = purpose_span
    value = dict(product_id=pid, connection_role=role, speech_act=speech,
        medium=_canonical(match.groupdict().get('medium')),
        medium_original=match.groupdict().get('medium'), purpose=purpose,
        origin=match.groupdict().get('origin'), destination=match.groupdict().get('destination'),
        operational_status='not_observed', interpretation=interpretation,
        clause=sentence, source_span=_span(text, start, start + len(sentence)),
        field_spans=fields, scope_text=text, source_chunk_uid=doc.get('chunk_uid', doc.get('chunk_id')),
        document_id=doc.get('document_id'), revision_id=doc.get('revision_id'),
        original_sha256=doc.get('original_sha256'), content_sha256=doc.get('content_sha256'),
        payload_sha256=doc.get('payload_sha256'), reference_number=doc.get('reference_number'),
        physical_pages=sorted({r['page'] for r in refs if r.get('kind') == 'pdf' and
            type(r.get('page')) is int and r['page'] > 0}), page_status='exact' if exact else 'unknown',
        rule_id=rule, rule_version=VERSION)
    value['fact_id'] = fingerprint(value)
    return value


def derive_connection_facts(assembly, product_ids, product_labels=None):
    """仅准入完整独立句法。单产品文档标签不能补出句内未出现的主体。"""
    facts = []
    for doc in assembly:
        ids = (doc.get('metadata') or {}).get('product_ids') or []
        if len(ids) != 1 or ids[0] not in product_ids:
            continue
        pid, text = ids[0], doc.get('text') or ''
        protected = _protected(text)
        names = _names(pid, product_labels)
        subjects = '|'.join(re.escape(n) for n in sorted(names, key=lambda n: (-len(n), n)))
        for sentence_match in re.finditer(r'[^。；;\n|]+', text):
            sentence = sentence_match.group().strip()
            start = sentence_match.start() + len(sentence_match.group()) - len(sentence_match.group().lstrip())
            if any(start < b and start + len(sentence) > a for a, b in protected):
                continue
            def add(match, **kwargs):
                facts.append(_source_fact(doc, pid, sentence, start, match, **kwargs))

            path = re.fullmatch(r'(?:请)?(?:确认|检查)(?P<origin>(?:' + subjects +
                r')(?:的)?[A-Za-z0-9/_-]+口)的(?P<medium>' + _MEDIA +
                r')是否(?:插牢|连接正确|接好|连接牢固)[,，]\s*(?P=medium)另一端与'
                r'(?P<destination>[^，,]+?)是否(?:连接正确|接好|连接牢固)', sentence, re.IGNORECASE)
            if path:
                add(path, role='documented_physical_path', speech='diagnostic_instruction',
                    rule='physical_path_v1', interpretation='qualified_path_interpretation')
                continue
            # 融合能力的主体及并列修饰必须在同一句完整语法中；末尾CATV限制
            # 不否定前面的融合描述，也不把配合的集中器算成本机端点。
            capability = re.fullmatch(r'(?P<origin>产品|' + subjects + r')采用[^，,]+[，,]'
                r'并且向前兼容[，,]配合[^，,]+网络集中器[，,]融合了\s*'
                r'(?P<medium>Cable\s*网络)和无线路由器的功能[，,]'
                r'在提供有线客户端接入的同时允许支持802\.11[a-z/]*无线客户端接入'
                r'(?:[，,]组网更灵活[，,]使用更方便)?[，,]同时不影响原有的\s*CATV\s*信号',
                sentence)
            if capability and not _CONDITION.search(sentence[:capability.end('medium')]):
                add(capability, role='capability_description', speech='capability_statement',
                    rule='compound_product_capability_v1')
                continue
            # 一个句子中的条件或否定不被裁成肯定结论；下一独立句的限制不会抹掉此句。
            if _CONDITION.search(sentence):
                continue
            link = re.fullmatch(r'(?:(?:' + subjects + r')[^，,]+提供[^，,]+服务[，,]\s*)?'
                r'(?:(?:为了)(?P<before>[^，,]+)[，,]\s*)?'
                r'(?P<origin>' + subjects + r')\s*(?:需要|可以)?(?P<uplink>上联)?通过\s*'
                r'(?P<medium>' + _MEDIA + r')\s*连接到\s*(?P<destination>[^，,]+?)'
                r'(?:[，,]\s*(?:用于)(?P<after>[^，,]+))?', sentence, re.IGNORECASE)
            if link:
                purpose_name = 'before' if link.group('before') else 'after'
                purpose = link.group(purpose_name)
                a, b = link.span(purpose_name) if purpose else (0, 0)
                purpose_span = _span(text, start + a, start + b) if purpose else None
                role = ('controller_link' if purpose and '管理' in purpose and
                    re.fullmatch(r'[A-Za-z0-9一-龥 ]*(?:无线控制器|控制器|AC)', link.group('destination'))
                    else 'explicit_uplink' if link.group('uplink') else 'unknown')
                add(link, role=role, speech='statement', rule='endpoint_connection_v1',
                    purpose=purpose, purpose_span=purpose_span)
                continue
            capability = re.fullmatch(r'(?P<origin>' + subjects + r')\s*融合了?\s*'
                r'(?P<medium>Cable\s*网络)和无线路由器的功能(?:[,，]并提供无线客户端接入)?', sentence)
            if capability:
                add(capability, role='capability_description', speech='capability_statement',
                    rule='product_capability_v1')
                continue
            access = re.fullmatch(r'(?P<origin>您|用户)(?:可以)?通过'
                r'(?P<medium>有线方式或无线方式|有线或无线的方式|有线方式|无线方式)'
                r'(?:建立网络连接|连接到)\s*(?P<destination>' + subjects + r')', sentence)
            if access:
                add(access, role='client_access', speech='capability_statement', rule='client_access_v1')
    return facts


def compare_connections(target, product_ids, facts):
    if target != 'device_uplink' or len(product_ids) != 2 or len(set(product_ids)) != 2:
        raise ValueError('连接比较只接受两个产品的device_uplink目标')
    observations = {pid: [] for pid in product_ids}
    for original in facts:
        if original.get('product_id') not in observations:
            raise ValueError('连接事实超出冻结比较产品范围')
        item = deepcopy(original)
        item.setdefault('fact_id', fingerprint(item))
        observations[item['product_id']].append(item)
    selected, support, conflicts = {}, [], []
    for pid, items in observations.items():
        usable = [i for i in items if i.get('connection_role') in _ROLES and _canonical(i.get('medium'))]
        if len({_canonical(i['medium']) for i in usable}) > 1:
            conflicts.append(dict(product_id=pid, fact_ids=[i['fact_id'] for i in usable]))
        elif usable:
            selected[pid] = usable[0]
            support.extend(i['fact_id'] for i in usable)
    values = {pid: _canonical(i['medium']) for pid, i in selected.items()}
    status = ('conflict' if conflicts else 'insufficient' if len(selected) != 2 else
        'qualified_medium_same' if len(set(values.values())) == 1 else 'qualified_medium_difference')
    return dict(function_version=VERSION, comparison_target=target, status=status,
        product_ids=list(product_ids), selected={} if conflicts else selected,
        compared=dict(field='medium', canonical_values=values) if len(selected) == 2 and not conflicts else {},
        support_fact_ids=list(dict.fromkeys(support)) if len(selected) == 2 and not conflicts else [],
        conflicts=conflicts, missing=[pid for pid in product_ids if pid not in selected], observations=observations)


def _literal(value):
    from .comparison_answers import _literal_field
    return _literal_field(html.escape(str(value), quote=False))


def _citation(fact):
    page = '、'.join(map(str, fact['physical_pages'])) if fact.get('page_status') == 'exact' else '页码未知'
    reference = fact.get('reference_number')
    return (f'[{reference}]' if type(reference) is int and reference > 0 else '（来源编号未提供）') + f'（物理页：{page}）'


def _fact_text(fact):
    medium = MEDIA_LABELS.get(_canonical(fact.get('medium')), fact.get('medium_original') or '未明确')
    role = fact['connection_role']
    if role == 'controller_link':
        return f"通过{medium}连接到{_literal(fact['destination'])}，用途为{_literal(fact['purpose'])}"
    if role == 'documented_physical_path':
        return (f"排障条目要求检查{_literal(fact.get('origin') or '端口')}经{medium}至"
            f"{_literal(fact.get('destination') or '对端')}的物理路径；这是接入侧路径的限定解释，"
            '不表示现场链路已经建立')
    if role == 'explicit_uplink':
        return f"资料明确记载经{medium}上联至{_literal(fact.get('destination') or '对端')}"
    if role == 'capability_description':
        return '产品介绍记载融合Cable网络和无线路由器功能；这不证明其他未记载的链路能力'
    if role == 'client_access':
        return f"用户可通过{_literal(fact['medium_original'])}连接到{_literal(fact['destination'])}，属于客户端访问"
    return '该句未形成当前程序可判定的上联关系'


def render_connection_comparison(result, product_labels):
    leads = {
        'qualified_medium_difference': '两份资料记载的对外连接介质不同：下面分别说明各自路径与用途，不将其扩大为两台设备所有上联能力的全面结论。',
        'qualified_medium_same': '两份资料所列路径的连接介质相同；各自角色和用途仍需分别理解，不能据此认定上联能力相同。',
        'conflict': '同一产品存在多种介质证据，当前无法唯一确定比较路径；不能任意选择一条作为完整结论。',
        'insufficient': '现有来源尚未形成双方可判定的上联比较依据；这不表示原资料没有说明。',
    }
    if result['status'] not in leads:
        raise ValueError('连接比较结果状态无效')
    lines = [leads[result['status']]]
    for pid in result['product_ids']:
        label = _literal(product_labels.get(pid, pid))
        observations = result['observations'][pid]
        meaningful = [f for f in observations if f['connection_role'] in _ROLES |
            {'capability_description', 'client_access'}]
        if not meaningful:
            lines.append(f'{label}：缺少当前规则可判定的连接证据，不能补写上联方式。')
        scopes = set()
        for f in meaningful:
            lines.append(f'{label}：{_fact_text(f)}。{_citation(f)}')
            scope = f.get('scope_text') or ''
            if scope in scopes:
                continue
            scopes.add(scope)
            qualifiers = []
            for m in re.finditer(r'[^。\n|]+', scope):
                clause = m.group().strip()
                if (f.get('rule_id') == 'compound_product_capability_v1' and clause == f['clause']):
                    # 此完整句法已显式限定三类修饰，逐项呈现，完整原段仍在证据视图。
                    qualifiers.extend(part.strip() for part in re.split(r'[,，]', clause)
                        if re.search(r'向前兼容|配合|不影响', part))
                elif re.search(r'目前|只支持|仅|如果|若|是否|以下描述|缺省配置|不影响', clause):
                    qualifiers.append(clause)
            if qualifiers:
                lines.append('适用条件与限制：' + '；'.join(_literal(q) for q in qualifiers) + '。' + _citation(f))
    lines.append('管理连接、Cable接入侧路径与用户有线/无线或Web访问分别理解；静态资料不能证明现场已连接。')
    return '\n'.join(lines)
