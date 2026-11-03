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


def _sentences(text):
    return [m.group().strip() for m in re.finditer(r'[^。；;\n|]+', text) if m.group().strip()]


def _scope_status(text):
    """只识别完整的语境声明句，不从其中截出后续的肯定关系。"""
    for clause in _sentences(text):
        clause = clause.rstrip('：:').strip()
        if re.fullmatch(r'(?:(?:以下|下列|下面)(?:仅)?(?:为|是))?(?:一个)?(?:错误|假设|配置|历史|演示|正确)?(?:示例|场景|记录)', clause):
            return 'non_assertive_scope'
        if re.fullmatch(r'(?:该|上述|此|本设备的)?(?:上联方式|管理链路|连接方式|链路)(?:已经|已)(?:废弃|停用|失效)', clause):
            return 'noncurrent_scope'
    return 'source_statement'


def _single_endpoint(value):
    """连接和排障共用对象边界，不把复合关系当作一个对端名称。"""
    return not re.search(r'或|和|与|及|并|通过|连接|上联|提供|[,，:：;；]', value)


def derive_source_contexts(assembly, product_ids):
    """每份已核验来源都进入结果，包含没有可分类连接事实的条件子段。"""
    contexts = []
    for doc in assembly:
        ids = (doc.get('metadata') or {}).get('product_ids') or []
        if len(ids) != 1 or ids[0] not in product_ids:
            continue
        refs = (doc.get('metadata') or {}).get('source_refs', doc.get('source_refs', [])) or []
        text = doc.get('text') or ''
        exact = bool(refs) and all(r.get('kind') == 'pdf' and type(r.get('page')) is int and r['page'] > 0 for r in refs)
        contexts.append(dict(product_id=ids[0], source_chunk_uid=doc.get('chunk_uid', doc.get('chunk_id')),
            document_id=doc.get('document_id'), revision_id=doc.get('revision_id'),
            original_sha256=doc.get('original_sha256'), payload_sha256=doc.get('payload_sha256'),
            scope_text=text, context_sha256=fingerprint(text), scope_status=_scope_status(text),
            reference_number=doc.get('reference_number'),
            physical_pages=sorted({r['page'] for r in refs if r.get('kind') == 'pdf' and type(r.get('page')) is int and r['page'] > 0}),
            page_status='exact' if exact else 'unknown'))
    return contexts


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
        metadata = doc.get('metadata') or {}
        refs = metadata.get('source_refs', doc.get('source_refs', [])) or []
        # 描述块保留为带出处资料，但只有PDF原文text/table能形成强关系；
        # 未知或混合来源类型也不能靠纯文本外形升级。
        if (metadata.get('content_kind') not in {'text', 'table'} or not refs or
                any(r.get('kind') != 'pdf' for r in refs) or
                _scope_status(text) != 'source_statement' or
                any(_scope_status(h) != 'source_statement' for h in metadata.get('heading_path', []))):
            continue
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
                if not _single_endpoint(path.group('destination')):
                    continue
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
                # 对端只能是一个对象，不能把另一关系或并列介质吞入对端字段。
                if (len(re.findall(_MEDIA, sentence, re.IGNORECASE)) != 1 or
                        not _single_endpoint(link.group('destination'))):
                    continue
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


def compare_connections(target, product_ids, facts, *, source_contexts=None):
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
    if source_contexts is None:
        source_contexts = []
        seen_contexts = set()
        for fact in facts:
            key = fact['product_id'], fact.get('source_chunk_uid'), fact.get('scope_text')
            if key not in seen_contexts:
                seen_contexts.add(key)
                source_contexts.append({k: deepcopy(fact.get(k)) for k in (
                    'product_id','source_chunk_uid','document_id','revision_id','original_sha256',
                    'payload_sha256','scope_text','reference_number','physical_pages','page_status')} |
                    dict(context_sha256=fingerprint(fact.get('scope_text') or ''),
                         scope_status=_scope_status(fact.get('scope_text') or '')))
    return dict(function_version=VERSION, comparison_target=target, status=status,
        product_ids=list(product_ids), selected={} if conflicts else selected,
        compared=dict(field='medium', canonical_values=values) if len(selected) == 2 and not conflicts else {},
        support_fact_ids=list(dict.fromkeys(support)) if len(selected) == 2 and not conflicts else [],
        conflicts=conflicts, missing=[pid for pid in product_ids if pid not in selected], observations=observations,
        source_contexts=deepcopy(source_contexts))


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
        # 不能只遍历有连接事实的来源：未分类子条件及相邻语境也必须独立呈现。
        # 不猜其用途、不将它并到另一引用的断言字段，也不按几个条件关键词筛选。
        for context in result.get('source_contexts', []):
            if context['product_id'] != pid:
                continue
            related = [f for f in meaningful if f.get('source_chunk_uid') == context['source_chunk_uid']]
            already = {f.get('clause') for f in related}
            remainder = [clause for clause in _sentences(context.get('scope_text') or '')
                if clause not in already and not any(
                    re.search(r'目前|只支持|仅|如果|若|是否|以下描述|缺省配置|不影响', clause)
                    for f in related)]
            if remainder:
                lines.append(f'{label}来源语境（保留原文，不新增连接关系）：' +
                    '；'.join(_literal(clause) for clause in remainder) + '。' + _citation(context))
    lines.append('以上按各条来源的连接角色与用途分别解释；静态资料不能证明现场已连接。')
    return '\n'.join(lines)
