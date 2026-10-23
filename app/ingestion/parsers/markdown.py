"""Markdown结构和物理行来源；图片只登记，远程地址不自动下载。"""
from pathlib import Path
import re
from app.knowledge.models import SourceRef,content_hash,stable_id
from app.ingestion.models import Block,ParsedDocument,ParsedImage


class MarkdownParser:
    version = '2'
    def __init__(self,*,purpose='unknown'): self.purpose=purpose

    def parse(self,path,*,document_id,revision_id):
        path=Path(path);lines=path.read_text(encoding='utf-8-sig').splitlines()
        blocks,images,flags,headings=[],[],[],[]
        buffer=[];start=1;fence=None;heading_stack=[];table_mode=False
        def flush():
            if not buffer: return
            text='\n'.join(buffer)
            kind='warning' if text.lstrip().startswith(('>','警告','注意')) else 'steps' if re.match(r'\s*(?:\d+[.)、]|[-*])\s*',text) else 'table' if re.search(r'^\s*\|?.*\|.*\n\s*\|?\s*:?-+',text) else 'text'
            ref=SourceRef(document_id=document_id,revision_id=revision_id,kind='markdown',section_path=tuple(headings),line_start=start,line_end=start+len(buffer)-1)
            bid=stable_id('block',revision_id,[start,text]);asset_ids=[]
            for image_index,match in enumerate(re.finditer(r'!\[([^\]]*)\]\(([^)]+)\)',text)):
                target=match[2].split(' "',1)[0].strip('<>')
                if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:',target): flags.append('external_image_unresolved');continue
                target_path=(path.parent/target).resolve()
                if not target_path.is_relative_to(path.parent.resolve()) or not target_path.is_file(): flags.append('missing_image');continue
                iid=stable_id('image',revision_id,[bid,image_index])
                asset_ids.append(iid);images.append(ParsedImage(image_id=iid,local_path=str(target_path),context=text,source_refs=(ref,)))
            rows=();row_numbers=()
            if table_mode:
                kind='table'
                # 只有已识别的Markdown表格第二物理行是语法；数据中的短横线原样保留。
                data_rows=[(start+i,row) for i,row in enumerate(buffer) if i!=1]
                rows=tuple(tuple(c.strip() for c in row.strip().strip('|').split('|')) for _,row in data_rows)
                row_numbers=tuple(number for number,_ in data_rows)
            blocks.append(Block(block_id=bid,kind=kind,text=text,heading_path=tuple(headings),source_refs=(ref,),asset_ids=tuple(asset_ids),rows=rows,row_numbers=row_numbers))
            buffer.clear()
        for index,line in enumerate(lines,1):
            is_table_start=(fence is None and '|' in line and index<len(lines)
                            and all(re.fullmatch(r':?-+:?',c.strip()) for c in lines[index].strip().strip('|').split('|'))
                            and '|' in lines[index])
            if is_table_start and not table_mode:
                flush();table_mode=True
            elif table_mode and ('|' not in line or not line.strip()):
                flush();table_mode=False
            marker=re.match(r'^\s*(`{3,}|~{3,})',line)
            if marker:
                if fence is None: fence=marker[1][0]
                elif marker[1][0]==fence: fence=None
            heading=re.match(r'^(#{1,6})\s+(.+?)\s*#*$',line) if fence is None and not marker else None
            if heading:
                flush();level=len(heading[1])
                while heading_stack and heading_stack[-1][0]>=level:
                    heading_stack.pop()
                heading_stack.append((level,heading[2]))
                headings=[title for _,title in heading_stack]
                ref=SourceRef(document_id=document_id,revision_id=revision_id,kind='markdown',section_path=tuple(headings),line_start=index,line_end=index)
                blocks.append(Block(block_id=stable_id('block',revision_id,[index,line]),kind='heading',text=line,heading_path=tuple(headings),source_refs=(ref,)))
            elif not line.strip() and fence is None: flush()
            else:
                if not buffer: start=index
                buffer.append(line)
        flush()
        if fence: flags.append('unclosed_code_fence')
        return ParsedDocument(document_id=document_id,revision_id=revision_id,original_sha256=content_hash(path.read_bytes()),parser='markdown',parser_version=self.version,
                              purpose=self.purpose,quality_flags=tuple(sorted(set(flags))),blocks=tuple(blocks),images=tuple(images))
