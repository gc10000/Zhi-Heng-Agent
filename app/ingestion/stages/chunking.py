"""结构化切片按同章节相邻正文合并；保留型号、定位、表格及图片边界。"""
import re
from app.knowledge.models import Chunk,SourceRef,stable_id,content_hash
from html.parser import HTMLParser

VERSION = '5'


class _TableReader(HTMLParser):
    def __init__(self):
        super().__init__();self.rows=[];self.row=None;self.cell=None;self.header_rows=set();self.in_header=False
    def handle_starttag(self,tag,attrs):
        if tag=='thead':self.in_header=True
        if tag=='tr':
            self.row=[]
            if self.in_header:self.header_rows.add(len(self.rows))
        if tag in {'th','td'}:self.cell=[]
        if tag=='th' and dict(attrs).get('scope','').lower() not in {'row','rowgroup'}:
            self.header_rows.add(len(self.rows))
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag=='thead':self.in_header=False
        if tag in {'th','td'} and self.cell is not None:
            if self.row is not None:self.row.append(''.join(self.cell).strip())
            self.cell=None
        if tag=='tr' and self.row is not None:self.rows.append(tuple(self.row));self.row=None


def structured_blocks(document):
    """Excel物理行组合成表，单元格引用保持原值；不跨sheet/型号。"""
    output=[];groups={}
    for block in document.blocks:
        if block.cells and block.source_refs and block.source_refs[0].kind=='excel':
            key=(block.source_refs[0].sheet,block.product_ids,block.heading_path)
            if key not in groups:groups[key]=[];output.append(key)
            groups[key].append(block)
        elif block.kind=='table' and not block.rows and '<table' in block.text.lower():
            parser=_TableReader();parser.feed(block.text)
            # 部分解析器把真正表头也输出成td；常见列名仍按表头处理。
            header=tuple(cell.strip().casefold() for cell in parser.rows[0]) if parser.rows else ()
            labels=tuple(re.split(r'[（(]',cell,maxsplit=1)[0].strip() for cell in header)
            labeled_header=(len(labels)==2 and labels[0] in {'参数','项目','名称','接口','parameter','item','name'}
                            and labels[1] in {'说明','描述','含义','值','限制','功率','description','value'})
            if parser.rows and not parser.header_rows and not labeled_header and all(len(row)==2 for row in parser.rows):
                # 无表头的键值/编号说明表：每行都是数据，不能把第一部件当所有后续行的表头。
                for i,row in enumerate(parser.rows):
                    output.append(block.model_copy(update={'block_id':stable_id('table-row',document.revision_id,[block.block_id,i]),'rows':(row,)}))
            else:
                count=max(parser.header_rows)+1 if parser.header_rows else 1
                if parser.header_rows and parser.header_rows!=set(range(count)):
                    raise ChunkBoundaryError('表头不连续，禁止丢失表头条件')
                output.append(block.model_copy(update={'rows':tuple(parser.rows),'table_header_rows':count}))
        else:output.append(block)
    for value in output:
        if not isinstance(value,tuple):yield value;continue
        members=groups[value];grid={};refs=[];assets=[]
        for block in members:
            refs.extend(block.source_refs);assets.extend(block.asset_ids)
            for cell in block.cells:
                match=re.fullmatch(r'([A-Z]+)(\d+)',cell.coordinate)
                if not match:raise ChunkBoundaryError('非法Excel单元格坐标')
                column=0
                for letter in match[1]:column=column*26+ord(letter)-64
                row=int(match[2])
                text=f'{cell.formula} [缓存:{cell.cached_value if cell.cached_value is not None else "未知"}]' if cell.formula else cell.value or ''
                grid[row,column]=text
        numbers=sorted({row for row,col in grid});width=max(col for row,col in grid)
        rows=tuple(tuple(grid.get((row,col),'') for col in range(1,width+1)) for row in numbers)
        yield members[0].model_copy(update={'rows':rows,'row_numbers':tuple(numbers),'source_refs':tuple(refs),'asset_ids':tuple(dict.fromkeys(assets))})


class ChunkBoundaryError(ValueError):pass


def split_text(text,max_chars):
    if max_chars<1:raise ValueError('切片上限必须大于0')
    from app.core.markdown_source import block_code_ranges
    # 固定解析器负责同类/长度、缩进与未闭合围栏；按原始行跨度取值，不重渲染源码。
    ranges=[]
    for start,end in block_code_ranges(text):
        end=start+len(text[start:end].rstrip('\r\n'))
        ranges.append((start,end))
    atoms=[]
    def prose(value):
        for part in re.split(r'(!\[[^\]]*\]\([^)]*\))',value):
            if part:atoms.append((part,part.startswith('![')))
    end=0
    for start,stop in sorted(ranges):
        prose(text[end:start]);atoms.append((text[start:stop],True));end=stop
    prose(text[end:])
    chunks=[];current=''
    for atom,atomic in atoms:
        if not atom:continue
        if atomic:
            if len(atom)>max_chars:raise ChunkBoundaryError('单个图片引用或代码块超过切片上限')
            if len(current)+len(atom)>max_chars:chunks.append(current);current=''
            current+=atom
        else:
            while atom:
                room=max_chars-len(current)
                if not room:chunks.append(current);current='';room=max_chars
                take=min(len(atom),room)
                # 优先在最后半段的句/步骤边界截取；无分隔符最终按字符兜底。
                if len(atom)>room:
                    cut=max(atom.rfind(c,room//2,room) for c in ('\n','。','；',' '))
                    if cut>=0:take=cut+1
                current+=atom[:take];atom=atom[take:]
                if len(current)==max_chars:chunks.append(current);current=''
    if current:chunks.append(current)
    return chunks


def _coalesced_blocks(document,max_chars):
    """同一章节的连续短步骤合并，跨页保留全部定位；不跨结构/型号/页码缺口。"""
    pending=None;members=[]
    def compatible(a,b):
        if a.kind not in {'text','steps'} or b.kind not in {'text','steps'}:return False
        if a.description is not None or b.description is not None or a.asset_ids or b.asset_ids:return False
        if not a.heading_path or a.heading_path!=b.heading_path or a.product_ids!=b.product_ids:return False
        if not a.source_refs or not b.source_refs:return False
        left,right=a.source_refs[-1],b.source_refs[0]
        if (left.document_id,left.revision_id,left.kind)!=(right.document_id,right.revision_id,right.kind):return False
        if left.kind=='pdf':return left.page is not None and right.page is not None and 0<=right.page-left.page<=1
        return False
    for block in structured_blocks(document):
        # 版面图可夹在同一句两段之间。保留独立图块，同时允许正文越过同范围图续接。
        if pending is not None and block.kind=='image' and block.description is None and compatible(pending,block.model_copy(update={'kind':'text','asset_ids':()})):
            yield block
            continue
        if pending is not None and compatible(pending,block) and len(pending.text)+2+len(block.text)<=max_chars:
            members.append(block.block_id)
            refs=tuple(dict.fromkeys((*pending.source_refs,*block.source_refs)))
            pending=pending.model_copy(update={'block_id':stable_id('block-group',document.revision_id,members),
                'text':pending.text+'\n\n'+block.text,'source_refs':refs,
                'kind':'steps' if 'steps' in {pending.kind,block.kind} else 'text'})
        else:
            if pending is not None:yield pending
            pending=block;members=[block.block_id]
    if pending is not None:yield pending


def chunk_document(document,*,max_chars=2000,default_product_ids=()):
    result=[]
    for block in _coalesced_blocks(document,max_chars):
        if any(ref.document_id!=document.document_id or ref.revision_id!=document.revision_id for ref in block.source_refs):
            raise ValueError('切片来源不能跨资料或修订')
        section_id=stable_id('section',document.revision_id,[block.block_id,block.heading_path])
        parts=[]
        if block.kind=='table' and block.rows:
            # 分隔语法由格式解析器处理；此处所有行均为真实数据，表头每片重复。
            rows=list(block.rows)
            count=block.table_header_rows
            if count>len(rows):raise ChunkBoundaryError('表头行数超出表格范围')
            header='\n'.join(' | '.join(row) for row in rows[:count])+'\n'
            if len(header)>=max_chars:raise ChunkBoundaryError('表头超限，请人工结构化处理')
            current=header;start=count;last=count-1
            for i,row in enumerate(rows[count:],count):
                line=' | '.join(row)+'\n'
                if len(header)+len(line)>max_chars:raise ChunkBoundaryError('单行表格超限，禁止截断单元格')
                if len(current)+len(line)>max_chars:
                    parts.append((current.rstrip('\n'),start,last));current=header;start=i
                current+=line;last=i
            if current:parts.append((current.rstrip('\n'),start if len(rows)>count else 0,last))
        else:
            text=block.description if block.description is not None else block.text
            parts=[(text,None,None)] if len(text)<=max_chars else [(part,None,None) for part in split_text(text,max_chars)]
        parent=None
        for index,(text,row_start,row_end) in enumerate(parts):
            if not text.strip():continue
            uid=stable_id('chunk',document.revision_id,[block.block_id,index,content_hash(text.encode()),max_chars])
            refs=block.source_refs
            if row_start is not None:
                if refs:
                    source=refs[0]
                    if block.row_numbers:
                        original_start=block.row_numbers[row_start]
                        original_end=block.row_numbers[row_end]
                    elif source.kind=='excel' and source.row_start is not None:
                        original_start=source.row_start+row_start
                        original_end=source.row_start+row_end
                    else:
                        original_start=original_end=None
                    locations={'cell':None,'row_start':original_start,'row_end':original_end}
                    if source.kind=='markdown' and block.row_numbers:
                        locations.update(line_start=original_start,line_end=original_end)
                    summary=SourceRef(**(source.model_dump()|locations))
                    details=tuple(ref for ref in refs if ref.cell and original_start is not None
                                  and (ref.row_start==(block.row_numbers[0] if block.row_numbers else source.row_start)
                                       or original_start<=ref.row_start<=original_end))
                    if source.kind=='markdown' and block.row_numbers and row_start>0:
                        header=block.row_numbers[0]
                        details+=(SourceRef(**(source.model_dump()|{'line_start':header,'line_end':header,'row_start':header,'row_end':header})),)
                    refs=(summary,)+details
            result.append(Chunk(document_id=document.document_id,revision_id=document.revision_id,section_id=section_id,chunk_uid=uid,
                parent_chunk_uid=parent,ordinal=len(result),text=text,heading_path=block.heading_path,source_refs=refs,
                product_ids=block.product_ids or tuple(default_product_ids),asset_ids=block.asset_ids,
                content_kind='image_description' if block.description is not None else block.kind if block.kind in {'table','warning','steps'} else 'text'))
            if parent is None:parent=uid
    return result
