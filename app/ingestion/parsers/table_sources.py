"""原件文本行、分隔线与跨页列关系的保守定位；不能证明时保持未知。"""
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
    line_ids: tuple
    baselines: tuple
    horizontal: tuple
    rules: tuple
    width: float
    height: float


def native_page(page):
    chars, boxes, line_ids, baselines, horizontal = [], [], [], [], []
    breaks = set()
    line_number = 0
    for block in page.get_text('rawdict')['blocks']:
        for line in block.get('lines', []):
            breaks.add(len(chars))
            line_number += 1
            direction = line.get('dir', (1, 0))
            for span in line['spans']:
                for char in span['chars']:
                    for c in unicodedata.normalize('NFKC', char['c']).casefold():
                        if c.isspace():
                            breaks.add(len(chars))
                        else:
                            chars.append(c)
                            boxes.append(tuple(char['bbox']))
                            line_ids.append(line_number)
                            baselines.append(char['origin'][1])
                            horizontal.append(abs(direction[0]-1)<.001 and abs(direction[1])<.001)
    rules = []
    for drawing in page.get_drawings():
        for item in drawing['items']:
            if item[0] == 'l':
                a, b = item[1:3]
                if abs(a.y-b.y)<.5:
                    rules.append((min(a.x,b.x), (a.y+b.y)/2, max(a.x,b.x)))
            elif item[0] == 're':
                rect = item[1]
                rules.extend(((rect.x0,rect.y0,rect.x1), (rect.x0,rect.y1,rect.x1)))
    return NativePage(''.join(chars), tuple(boxes), frozenset(breaks), tuple(line_ids),
                      tuple(baselines), tuple(horizontal), tuple(rules), page.rect.width, page.rect.height)


def _word_edge(page, offset):
    if offset in {0, len(page.text)} or offset in page.breaks:
        return True
    return not (page.text[offset-1].isascii() and page.text[offset-1].isalnum()
                and page.text[offset].isascii() and page.text[offset].isalnum())


@dataclass(frozen=True)
class Fragment:
    line_id: int
    left: float
    right: float
    baseline: float
    height: float


def _fragments(page, first, last):
    """逐原件文本行检查，不能让整体矩形掩盖行内跳列或远处续文。"""
    fragments = []
    cursor = first
    while cursor < last:
        end = cursor+1
        while end < last and page.line_ids[end] == page.line_ids[cursor]:
            end += 1
        boxes = page.boxes[cursor:end]
        height = max(b[3]-b[1] for b in boxes)
        baseline = page.baselines[cursor]
        if (not all(page.horizontal[cursor:end]) or
                any(abs(y-baseline)>height*.2 for y in page.baselines[cursor:end]) or
                any(b[0]-a[2]>height for a,b in zip(boxes,boxes[1:]))):
            return None
        fragments.append(Fragment(page.line_ids[cursor], min(b[0] for b in boxes),
                                  max(b[2] for b in boxes), baseline, height))
        cursor = end
    return fragments


def _separated(page, first, last):
    low, high = sorted((first.baseline, last.baseline))
    left, right = min(first.left,last.left), max(first.right,last.right)
    return any(low<y<high and x0<right and x1>left for x0,y,x1 in page.rules)


def _associated(page, parts):
    # 仅在同一原件行内的前缀单元格，才允许后续正文回到整行左边界换行。
    anchors = {}
    for index, fragments in parts:
        first = fragments[0]
        allowed = [first.left]
        for _, preceding in parts:
            if preceding[0].line_id == first.line_id:
                allowed.append(preceding[0].left)
        anchors[index] = tuple(allowed)
        for previous, following in zip(fragments, fragments[1:]):
            height = min(previous.height,following.height)
            if (not 0<following.baseline-previous.baseline<=height*1.8 or
                    min(abs(following.left-x) for x in allowed)>height*.5 or
                    _separated(page,previous,following)):
                return None
    # 真实文本行基线须对齐，不以字体bbox的少量交集认同一表行。
    for (_, left), (_, right) in zip(parts,parts[1:]):
        height = min(left[0].height,right[0].height)
        if (abs(left[0].baseline-right[0].baseline)>height*.25 or
                max(f.right for f in left)>min(f.left for f in right)+.5 or
                _separated(page,left[0],right[0])):
            return None
    return anchors


def _crosspage_associated(segments, regions, pages):
    boundary = len(pages[0].text)
    crossing = [i for i,(a,b) in enumerate(segments) if a<boundary<b]
    if len(crossing) != 1 or abs(pages[0].width-pages[1].width)>1:
        return False
    cell = crossing[0]
    left_parts, left_anchors = regions[0]
    right_parts, _ = regions[1]
    before = dict(left_parts)[cell]
    after = dict(right_parts)[cell]
    height = min(before[-1].height,after[0].height)
    # 必须接在同列/同段落列位；续页还须进入正常页首区域，不能接页内远处区域。
    return (min(abs(after[0].left-x) for x in left_anchors[cell])<=height*.5
            and after[0].baseline<=min(pages[1].height*.3,before[0].baseline+height*2))


def _matches(cells, pages):
    text = ''.join(p.text for p in pages)
    row = ''.join(cells)
    offset, boundaries = 0, []
    for p in pages:
        boundaries.append((offset,offset+len(p.text),p))
        offset += len(p.text)
    start = 0
    while row and (start := text.find(row,start)) >= 0:
        end = start+len(row)
        segments, cursor = [], start
        for cell in cells:
            segments.append((cursor,cursor+len(cell)))
            cursor += len(cell)
        regions = []
        valid = True
        for lo,hi,p in boundaries:
            if end<=lo or start>=hi:
                continue
            parts = []
            for index,(a,b) in enumerate(segments):
                first,last = max(a,lo),min(b,hi)
                if first>=last:
                    continue
                if not (_word_edge(p,first-lo) and _word_edge(p,last-lo)):
                    valid = False
                    break
                fragments = _fragments(p,first-lo,last-lo)
                if not fragments:
                    valid = False
                    break
                parts.append((index,fragments))
            anchors = _associated(p,parts) if valid else None
            if anchors is None:
                valid = False
                break
            regions.append((parts,anchors))
        if valid and len(regions)==2:
            valid = _crosspage_associated(segments,regions,pages)
        if valid:
            yield start,end
        start += 1


def locate_rows(rows, pages, ref):
    """完整词/行片段及页序唯一才定位；跨页还须证明同列和续页区域。"""
    result, start, frontier = [], ref.page, ref.page
    for row in rows:
        cells = [normalized(c) for c in row if normalized(c)]
        matches = []
        if start is not None and any(len(c)>=8 for c in cells):
            for page in range(start,len(pages)+1):
                matches.extend([(page,)]*len(list(_matches(cells,[pages[page-1]]))))
            if not matches:
                for page in range(start,len(pages)):
                    matches.extend([(page,page+1)]*len(list(_matches(cells,pages[page-1:page+1]))))
        locations = (None,)
        if len(matches)==1 and frontier is not None:
            match = matches[0]
            if frontier<=match[0]<=frontier+1:
                locations, frontier = match, match[-1]
        result.append(tuple(SourceRef(**(ref.model_dump()|{'page':p})) for p in locations))
    return tuple(result)
