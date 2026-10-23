"""结构化切片不跨块/型号合并；标题作为元数据，表格及图片边界明确。"""
import re
from app.knowledge.models import Chunk,SourceRef,stable_id,content_hash
from html.parser import HTMLParser


class _TableReader(HTMLParser):
    def __init__(self):
        super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr':self.row=[]
        if tag in {'th','td'}:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
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
            output.append(block.model_copy(update={'rows':tuple(parser.rows)}))
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
    # Markdown图片表达式保持原子；超限明确失败而非截断URL。
    atoms=re.split(r'(!\[[^\]]*\]\([^)]*\))',text)
    chunks=[];current=''
    for atom in atoms:
        if not atom:continue
        if atom.startswith('!['):
            if len(atom)>max_chars:raise ChunkBoundaryError('单个图片引用超过切片上限')
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


def chunk_document(document,*,max_chars=2000,default_product_ids=()):
    result=[]
    for block in structured_blocks(document):
        if any(ref.document_id!=document.document_id or ref.revision_id!=document.revision_id for ref in block.source_refs):
            raise ValueError('切片来源不能跨资料或修订')
        section_id=stable_id('section',document.revision_id,[block.block_id,block.heading_path])
        parts=[]
        if block.kind=='table' and block.rows:
            # Markdown分隔行不是数据；Excel保留原行号，表头每片重复。
            rows=list(block.rows)
            if len(rows)>1 and all(re.fullmatch(r':?-+:?',c.strip()) for c in rows[1]):rows.pop(1)
            header=' | '.join(rows[0])+'\n'
            if len(header)>=max_chars:raise ChunkBoundaryError('表头超限，请人工结构化处理')
            current=header;start=1;last=0
            for i,row in enumerate(rows[1:],1):
                line=' | '.join(row)+'\n'
                if len(header)+len(line)>max_chars:raise ChunkBoundaryError('单行表格超限，禁止截断单元格')
                if len(current)+len(line)>max_chars:
                    parts.append((current.rstrip('\n'),start,last));current=header;start=i
                current+=line;last=i
            if current:parts.append((current.rstrip('\n'),start if len(rows)>1 else 0,last))
        else:
            text=block.description if block.description is not None else block.text
            parts=[(text,None,None)] if len(text)<=max_chars else [(part,None,None) for part in split_text(text,max_chars)]
        parent=None
        for index,(text,row_start,row_end) in enumerate(parts):
            if not text.strip():continue
            uid=stable_id('chunk',document.revision_id,[block.block_id,index,content_hash(text.encode()),max_chars])
            refs=block.source_refs
            if row_start is not None:
                original_start=block.row_numbers[row_start] if block.row_numbers else (refs[0].row_start or 1)+row_start if refs else row_start+1
                original_end=block.row_numbers[row_end] if block.row_numbers else (refs[0].row_start or 1)+row_end if refs else row_end+1
                if refs:
                    summary=SourceRef(**(refs[0].model_dump()|{'cell':None,'row_start':original_start,'row_end':original_end}))
                    refs=(summary,)+tuple(ref for ref in refs if ref.cell and (ref.row_start==block.row_numbers[0] or original_start<=ref.row_start<=original_end))
            result.append(Chunk(document_id=document.document_id,revision_id=document.revision_id,section_id=section_id,chunk_uid=uid,
                parent_chunk_uid=parent,ordinal=len(result),text=text,heading_path=block.heading_path,source_refs=refs,
                product_ids=block.product_ids or tuple(default_product_ids),asset_ids=block.asset_ids,
                content_kind='image_description' if block.description is not None else block.kind if block.kind in {'table','warning','steps'} else 'text'))
            if parent is None:parent=uid
    return result
