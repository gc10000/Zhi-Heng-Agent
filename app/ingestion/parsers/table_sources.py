"""原件字符坐标与完整行关联的保守定位；无法证明时保持未知。"""
from dataclasses import dataclass
import re
import unicodedata
from app.knowledge.models import SourceRef


def normalized(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value)).casefold()


@dataclass(frozen=True)
class NativePage:
    text: str
    boxes: tuple
    breaks: frozenset


def native_page(page):
    chars=[]; boxes=[]; breaks=set()
    for block in page.get_text('rawdict')['blocks']:
        for line in block.get('lines', []):
            breaks.add(len(chars))
            for span in line['spans']:
                for char in span['chars']:
                    for c in unicodedata.normalize('NFKC',char['c']).casefold():
                        if c.isspace():breaks.add(len(chars))
                        else:chars.append(c);boxes.append(tuple(char['bbox']))
    return NativePage(''.join(chars),tuple(boxes),frozenset(breaks))


def _word_edge(page, offset):
    if offset in {0,len(page.text)} or offset in page.breaks:return True
    return not (page.text[offset-1].isascii() and page.text[offset-1].isalnum()
                and page.text[offset].isascii() and page.text[offset].isalnum())


def _associated(parts):
    # 多列应在同一横向行带，且按原顺序分离；单元格自身允许换行。
    if len(parts)<2:return True
    rects=[(min(b[0] for b in boxes),min(b[1] for b in boxes),
            max(b[2] for b in boxes),max(b[3] for b in boxes)) for boxes in parts]
    return (max(r[1] for r in rects)<min(r[3] for r in rects)
            and all(left[2]<=right[0]+.5 for left,right in zip(rects,rects[1:])))


def _matches(cells, pages):
    # 完整行连续匹配，不能略过中间行/限定词，也不能组合页内分散命中。
    text=''.join(p.text for p in pages);row=''.join(cells)
    offset=0;boundaries=[]
    for p in pages:
        boundaries.append((offset,offset+len(p.text),p));offset+=len(p.text)
    start=0
    while row and (start:=text.find(row,start))>=0:
        end=start+len(row);segments=[];cursor=start
        for cell in cells:
            segments.append((cursor,cursor+len(cell)));cursor+=len(cell)
        valid=True
        for lo,hi,p in boundaries:
            if end<=lo or start>=hi:continue
            parts=[]
            for a,b in segments:
                first,last=max(a,lo),min(b,hi)
                if first>=last:continue
                if not (_word_edge(p,first-lo) and _word_edge(p,last-lo)):
                    valid=False;break
                parts.append(p.boxes[first-lo:last-lo])
            if not valid or not _associated(parts):valid=False;break
        if valid:yield start,end
        start+=1


def locate_rows(rows, pages, ref):
    """完整词、连续行及字符版面关联唯一，且页序连续时才授予精确页码。

    扫描件/不可映射、重复、OCR差异或跨列冲突均未知。跨页仅允许同一
    连续单元格穿过物理边界，两侧均检查行关联，不放宽独立子串条件。
    """
    result=[];start=ref.page;frontier=start
    for row in rows:
        cells=[normalized(c) for c in row if normalized(c)];matches=[]
        if start is not None and any(len(c)>=8 for c in cells):
            for page in range(start,len(pages)+1):
                found=list(_matches(cells,[pages[page-1]]));matches.extend([(page,)]*len(found))
            if not matches:
                cuts=[sum(map(len,cells[:i])) for i in range(1,len(cells))]
                for page in range(start,len(pages)):
                    boundary=len(pages[page-1].text)
                    for a,b in _matches(cells,pages[page-1:page+1]):
                        if a<boundary<b and boundary-a not in cuts:matches.append((page,page+1))
        locations=(None,)
        if len(matches)==1 and frontier is not None:
            match=matches[0]
            if frontier<=match[0]<=frontier+1:locations=match;frontier=match[-1]
        result.append(tuple(SourceRef(**(ref.model_dump()|{'page':p})) for p in locations))
    return tuple(result)
