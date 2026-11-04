"""有界原句关系索引：只抽取逐字跨度，不推断网络拓扑或来源没有的能力。"""
import json
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.knowledge.models import content_hash
from app.knowledge.repository import fingerprint


VERSION = 'source_relation_spans_v1'
SHA = r'^[a-f0-9]{64}$'


class SourceRelationPolicy(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    enabled: bool = Field(default=False, strict=True)
    function_version: Literal['source_relation_spans_v1'] = VERSION
    frozen_payloads: dict[str, str] = Field(default_factory=dict, max_length=1000)

    @model_validator(mode='after')
    def complete(self):
        if (self.enabled and not self.frozen_payloads) or any(
                not k or not re.fullmatch(SHA, v) for k, v in self.frozen_payloads.items()):
            raise ValueError('来源关系须绑定完整冻结载荷hash')
        return self


def validate_snapshot(policy, snapshot):
    """绑定正式完整快照，不接受客户端自报reviewed或自定义关系断言。"""
    if policy is None or not policy.enabled:
        return
    members = [c for d in snapshot.get('documents', []) for c in d.get('chunks', [])]
    expected = {c['chunk_uid']: c['payload_sha256'] for c in members}
    if len(expected) != len(members) or expected != policy.frozen_payloads:
        raise ValueError('来源关系与完整冻结语料成员不一致')


def _span(text, start, end):
    literal = text[start:end]
    return dict(start=start, end=end, text=literal, sha256=content_hash(literal.encode('utf-8')))


def _group(text, match, name):
    start, end = match.span(name)
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    return _span(text, start, end) if start < end else None


# 只覆盖有明确句法标记的原句。缺少主语时不从型号、标题、前一子句或产品标签补齐。
_CONNECT = re.compile(r'(?P<origin>[^，,。；;\n|]*?)(?:可以|需要)?通过\s*'
    r'(?P<medium>[^，,。；;\n|]+?)连接到\s*(?P<destination>[^，,。；;\n|]+)')
_SERVICE = re.compile(r'(?P<origin>[^，,。；;\n|]*?)(?:可以)?(?:为|向)'
    r'(?P<destination>[^，,。；;\n|]+?)提供(?P<purpose>[^，,。；;\n|]+)')
_CHECK = re.compile(r'(?:请)?(?:确认|检查)(?P<origin>[^，,。；;\n|]+?口)的'
    r'(?P<medium>[^，,。；;\n|]+?)是否[^，,。；;\n|]+[,，]'
    r'(?P=medium)另一端与(?P<destination>[^，,。；;\n|]+?)是否[^，,。；;\n|]+')
_ACCESS = re.compile(r'通过(?P<medium>[^，,。；;\n|]+?)建立网络连接')
_LOGIN = re.compile(r'(?:登录|登陆)(?P<destination>[^，,。；;\n|”]+?Web页面)')


def _role_ambiguity(kind, clause):
    """只准入直接单动作句；先看完整候选，不能只看已被正则切短的发起端。"""
    if re.search(r'不|未|若|如果|是否|只有|除非|仅', clause):
        return 'negation_or_condition'
    # 关系从句、名词化或使役需要另一套解析；本索引不把其中片段提升为端点。
    if re.search(r'的|将|把', clause):
        return 'relative_or_disposal_clause'
    # 逗号后独立的“并向…”仍可保留部分角色；无标点复合动作不猜切句或继承主语。
    body = re.sub(r'^(?:并且|并|且|再)\s*', '', clause.strip())
    if re.search(r'并且|并|且|同时|然后|再', body):
        return 'unpunctuated_coordination'
    if kind == 'service' and clause.count('为') + clause.count('向') != 1:
        return 'non_unique_service_marker'
    if (clause.count('提供') > (kind == 'service') or
            clause.count('通过') > (kind == 'connection') or
            clause.count('连接到') > (kind == 'connection')):
        return 'nested_action'
    return None


def extract_frames(text):
    """返回同一原文内的半开字符坐标；原段落是所有否定、条件、时态的解释范围。"""
    from app.core.markdown_source import block_code_ranges, inline_code_ranges
    protected = block_code_ranges(text) + inline_code_ranges(text)
    result = []
    for kind, pattern in [('connection', _CONNECT), ('service', _SERVICE),
                          ('physical_check', _CHECK), ('access', _ACCESS), ('login', _LOGIN)]:
        for match in pattern.finditer(text):
            if any(match.start() < end and match.end() > start for start, end in protected):
                continue
            fields = {name: _group(text, match, name) if name in match.groupdict() else None
                      for name in ('origin', 'medium', 'destination', 'purpose')}
            reason = _role_ambiguity(kind, match.group()) if kind in {'connection', 'service'} else None
            if reason:
                # 同一复合句可能被两种模式命中，只保留一条完整原句及未知角色。
                if not any(f['kind'] == 'unresolved' and f['clause']['start'] == match.start()
                           and f['clause']['end'] == match.end() for f in result):
                    result.append(dict(kind='unresolved', direction='unknown',
                        fields=dict.fromkeys(fields), role_boundary_reason=reason,
                        clause=_span(text, match.start(), match.end()), scope=_span(text, 0, len(text)),
                        assertion='literal_only_not_capability_or_live_state'))
                continue
            origin = fields['origin']
            if origin and (origin['text'] in {'并', '并且', '再', '且'} or
                    re.search(r'若|如果|是否|不|未|仅|只有|除非|请|为了', origin['text'])):
                fields['origin'] = None
            if kind == 'connection':
                prefix = text[:match.start()]
                purpose = re.search(r'为了([^，,。；;\n|]+)[，,]$', prefix)
                if purpose:
                    fields['purpose'] = _span(text, purpose.start(1), purpose.end(1))
            direction = ('undirected_check' if kind == 'physical_check' else
                         'origin_to_destination' if fields['origin'] and fields['destination'] else 'unknown')
            result.append(dict(kind=kind, direction=direction, fields=fields,
                clause=_span(text, match.start(), match.end()), scope=_span(text, 0, len(text)),
                assertion='literal_only_not_capability_or_live_state'))
    # 未覆盖的语法只定位相关原句，未知不等于不支持；不执行其中的资料内指令。
    if not result:
        for match in re.finditer(r'[^。；\n]+[。；]?', text):
            if (re.search(r'连接|网络|上联|回传|传输|充电|服务|互通', match.group()) and
                    not any(match.start() < end and match.end() > start for start, end in protected)):
                result.append(dict(kind='unresolved', direction='unknown',
                    fields=dict.fromkeys(('origin', 'medium', 'destination', 'purpose')),
                    clause=_span(text, match.start(), match.end()), scope=_span(text, 0, len(text)),
                    assertion='literal_only_not_capability_or_live_state'))
    return sorted(result, key=lambda f: (f['clause']['start'], f['clause']['end'], f['kind']))


def attach_relations(doc, policy):
    """与正式冻结载荷逐字匹配；呈现转换改变原文也拒绝，不按相似文本找替代。"""
    relation = policy.source_relations
    if relation is None or not relation.enabled:
        return None
    uid = doc.get('chunk_uid', doc.get('chunk_id'))
    text = doc.get('text') or ''
    meta = doc.get('metadata') or {}
    raw = dict(chunk_uid=uid, document_id=doc.get('document_id'), revision_id=doc.get('revision_id'),
        owner_id=policy.scope.owner_id, kb_id=policy.scope.kb_id, ordinal=doc.get('ordinal'),
        text=text, metadata=meta, content_sha256=content_hash(text.encode('utf-8')))
    if (fingerprint(raw) != relation.frozen_payloads.get(uid) or
            doc.get('source_refs', meta.get('source_refs')) != meta.get('source_refs')):
        raise ValueError('来源关系原句、元数据或冻结成员漂移')
    source = next(d for d in policy.documents if d.document_id == doc['document_id'])
    return dict(function_version=VERSION, source=dict(document_id=source.document_id,
        revision_id=source.revision_id, original_sha256=source.original_sha256, chunk_uid=uid,
        content_sha256=raw['content_sha256'], payload_sha256=fingerprint(raw),
        source_refs_sha256=fingerprint(meta.get('source_refs'))), frames=extract_frames(text))


def render_relations(relation):
    """完整证明留正式引用映射；输入中紧邻各引用呈现可读槽位和原文坐标。"""
    if not relation['frames']:
        return ''
    names = dict(origin='发起端', destination='目的端', medium='经由', purpose='用途')
    lines = ['[来源中的关系与条件定位；以下范围仅解释相邻原文]']
    for frame in relation['frames']:
        fields = []
        for key in ('origin', 'destination', 'medium', 'purpose'):
            span = frame['fields'][key]
            literal = (json.dumps(span['text'], ensure_ascii=False) + f"@{span['start']}:{span['end']}"
                       if span else 'unknown')
            fields.append(names[key] + '=' + literal)
        clause, scope = frame['clause'], frame['scope']
        lines.append(f"原句@{clause['start']}:{clause['end']} 方向={frame['direction']} " +
                     '；'.join(fields) + f"；条件/否定须同读原文@{scope['start']}:{scope['end']}")
    return '\n' + '\n'.join(lines)
