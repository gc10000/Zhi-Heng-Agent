"""固定CommonMark解析器的源码跨度，坐标始终相对未改写的原始字符串。"""
import re
from markdown_it import MarkdownIt


def block_code_ranges(text):
    # CommonMark只将CRLF/CR/LF当换行；splitlines还识别分页符等，不能用于token.map。
    offsets=[0]+[m.end() for m in re.finditer(r'\r\n?|\n',text)]
    if offsets[-1]!=len(text):offsets.append(len(text))
    return [(offsets[t.map[0]],offsets[t.map[1]]) for t in MarkdownIt('default').parse(text)
            if t.type in {'fence','code_block'} and t.map]


def inline_code_ranges(text):
    from markdown_it.rules_inline.backticks import backtick
    from markdown_it.rules_inline.image import image
    md=MarkdownIt('default');ranges=[];base=0
    def code_span(state,silent):
        start=state.pos;count=len(state.tokens)
        accepted=backtick(state,silent)
        if not silent and len(state.tokens)>count and state.tokens[-1].type=='code_inline':
            ranges.append((base+start,base+state.pos))
        return accepted
    def image_span(state,silent):
        nonlocal base
        # 固定image规则只递归解析原src[labelStart:labelEnd]，labelStart=pos+2。
        # 其子状态坐标必须逐层叠加；失败/静默规则也必须恢复父坐标。
        parent=base;base+=state.pos+2
        try:return image(state,silent)
        finally:base=parent
    md.inline.ruler.at('backticks',code_span)
    md.inline.ruler.at('image',image_span)
    md.inline.parse(text,md,{},[])
    return ranges
