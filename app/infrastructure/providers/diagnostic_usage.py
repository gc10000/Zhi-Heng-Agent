"""显式诊断的安全原始计量快照；在SDK归一化前保留非法与缺失的区别。"""
from contextlib import contextmanager
from contextvars import ContextVar
from functools import lru_cache
from copy import deepcopy
import hashlib
import math
import re
import json

_SINK=ContextVar('diagnostic_usage_sink',default=None)
ABSENT=object()


def _field(path,value):
    valid=type(value) is int and value>=0
    # 只保留计量标量，不保存供应商任意嵌套对象或错误正文。
    safe=value
    if not (value is None or type(value) in (bool,int) or
            type(value) is float and math.isfinite(value) or
            type(value) is str and len(value)<=64 and re.fullmatch(r'[-+0-9.eE ]*',value)):
        safe={'sha256':hashlib.sha256(repr(value).encode()).hexdigest()}
    return dict(path=path,raw_type=type(value).__name__,value=safe,
        status='valid' if valid else 'null' if value is None else 'invalid')


def observe_usage(usage,*,source,reasoning=ABSENT):
    fields={k:[] for k in ('input','output','total','reasoning')};errors=[];containers=[]
    if usage is None:usage={}
    elif not isinstance(usage,dict):errors.append('usage_not_object');usage={}
    for name,keys in [('input',('input_tokens','prompt_tokens','input')),
                      ('output',('output_tokens','completion_tokens','output')),('total',('total_tokens',))]:
        fields[name]=[_field(key,usage[key]) for key in keys if key in usage]
    for container,keys in [('output_token_details',('reasoning','priority_reasoning','flex_reasoning')),
                           ('completion_tokens_details',('reasoning_tokens',))]:
        if container not in usage:continue
        detail=usage[container]
        containers.append(dict(path=container,raw_type=type(detail).__name__,present=True))
        if detail is None:continue  # 明确空明细不同于非法明细；可信总量不依赖可选明细。
        if not isinstance(detail,dict):errors.append('detail_not_object');continue
        fields['reasoning'].extend(_field(container+'.'+key,detail[key]) for key in keys if key in detail)
    if reasoning is not ABSENT:fields['reasoning'].append(_field('argument.reasoning',reasoning))
    counts={}
    for name,values in fields.items():
        counts[name]=None
        if any(v['status']=='invalid' for v in values):errors.append(name+'_invalid_count')
        numbers=[v['value'] for v in values if v['status']=='valid']
        if numbers and (len(set(numbers))>1 or any(v['status']=='null' for v in values)):
            errors.append(name+'_alias_conflict')
        elif numbers:counts[name]=numbers[0]
    if counts['reasoning'] is not None and counts['output'] is not None and counts['reasoning']>counts['output']:
        errors.append('reasoning_exceeds_output')
    if all(counts[k] is not None for k in ('input','output','total')) and counts['total']!=counts['input']+counts['output']:
        errors.append('total_sum_conflict')
    return dict(source=source,fields=fields,containers=containers,counts=counts,errors=errors,
        complete=counts['input'] is not None and counts['output'] is not None,valid=not errors)


def summarize(observations):
    observations=deepcopy(observations)
    errors=[e for o in observations for e in o['errors']]
    # 本合同使用请求累计usage；已知总量倒退同样不能被最后一片洗掉。
    for key in ('input','output'):
        known=[o['counts'][key] for o in observations if o['counts'][key] is not None]
        if any(a>b for a,b in zip(known,known[1:])):errors.append(key+'_regressed')
    counts=observations[-1]['counts'] if observations else dict(input=None,output=None,total=None,reasoning=None)
    return dict(valid=not errors,complete=counts['input'] is not None and counts['output'] is not None,
        errors=sorted(set(errors)),reported=counts,observations=observations,
        raw_coverage='sdk_raw' if observations and all(o['source']=='sdk_raw' for o in observations) else 'normalized_or_direct')


@contextmanager
def capture_usage(observations):
    token=_SINK.set(observations)
    try:yield
    finally:_SINK.reset(token)


def record_raw(usage):
    target=_SINK.get()
    if target is not None:target.append(observe_usage(usage,source='sdk_raw'))


def instrument_sdk_stream(client):
    """固定SDK的SSE解码口，在其类型强制转换之前读取同一事件，不增加请求。"""
    if getattr(client,'_diagnostic_decoder_v2',False):return
    original=client._make_sse_decoder
    class Decoder:
        def __init__(self,base):self.base=base

        def iter_bytes(self,iterator):
            for event in self.base.iter_bytes(iterator):
                if event.data and event.data!='[DONE]':
                    try:raw=event.json()
                    except (ValueError,TypeError):record_raw('malformed_sse_event')
                    else:
                        if isinstance(raw,dict) and 'usage' in raw and raw['usage'] is not None:record_raw(raw['usage'])
                yield event
    client._make_sse_decoder=lambda:Decoder(original())
    def json_usage(response):
        if 'application/json' in response.headers.get('content-type',''):
            try:raw=json.loads(response.read())
            except (ValueError,TypeError):record_raw('malformed_json_response')
            else:
                if isinstance(raw,dict) and 'usage' in raw:record_raw(raw['usage'])
    client._client.event_hooks['response'].append(json_usage)
    client._diagnostic_decoder_v2=True


def record_response(response,observations,previous):
    if len(observations)>previous:return  # 同一分片已有归一化前快照，禁止用后值覆盖。
    meta=getattr(response,'response_metadata',None) or {}
    if 'token_usage' in meta:
        observations.append(observe_usage(meta['token_usage'],source='response_metadata'))
    elif getattr(response,'usage_metadata',None) is not None:
        observations.append(observe_usage(response.usage_metadata,source='sdk_normalized'))


@lru_cache(maxsize=1)
def preserving_chat_class():
    # 仅显式诊断创建该子类；旧非诊断客户端及全局配置不改变。
    from langchain_openai.chat_models.base import ChatOpenAI
    class UsagePreservingChatOpenAI(ChatOpenAI):
        def _stream(self,*args,**kwargs):
            self._ensure_sync_client_available()
            instrument_sdk_stream(self.root_client)
            yield from super()._stream(*args,**kwargs)

        def _generate(self,*args,**kwargs):
            self._ensure_sync_client_available()
            instrument_sdk_stream(self.root_client)
            return super()._generate(*args,**kwargs)
    return UsagePreservingChatOpenAI
