"""缓存表格对本地原件的保守行级定位；不调用解析供应商，不改正文。"""
import re
import unicodedata
from app.knowledge.models import SourceRef


def normalized(value):
    return re.sub(r'\s+', '', unicodedata.normalize('NFKC', value)).casefold()


def locate_rows(rows, pages, ref):
    """完整单元格唯一匹配，且整表行序只能沿原起点连续前进。

    重复/短文本、OCR差异、单元格冲突均返回未知；不以远处的相同句子
    纠正本表。邻接caption的page_idx也可能沿用起始页，因此不能将它当
    跨页表的终点。跨页完整单元格仅在连续拼接精确且唯一时保留两页。
    """
    result=[]
    start=ref.page
    frontier=start
    for row in rows:
        cells=[normalized(c) for c in row if normalized(c)]
        matches=[]
        # 长单元格提供区分度，短型号/数字/版本也必须同页出现，不能略去限定。
        if start is not None and any(len(cell)>=8 for cell in cells):
            for page in range(start, len(pages)+1):
                if all(cell in pages[page-1] for cell in cells):matches.append((page,))
            if not matches:
                for page in range(start, len(pages)):
                    joined=pages[page-1]+pages[page]
                    if (all(cell in joined for cell in cells)
                            and any(cell not in pages[page-1] and cell not in pages[page] for cell in cells)):
                        matches.append((page,page+1))
        locations=(None,)
        if len(matches)==1 and frontier is not None:
            match=matches[0]
            if frontier<=match[0]<=frontier+1:
                locations=match;frontier=match[-1]
        result.append(tuple(SourceRef(**(ref.model_dump()|{'page':p})) for p in locations))
    return tuple(result)
