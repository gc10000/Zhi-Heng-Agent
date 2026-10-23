"""分段只写新缓存目录，原件只读；检查点原子落盘。"""
import json
from pathlib import Path
from uuid import uuid4
from app.knowledge.models import content_hash


def save_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    temporary=path.with_name(path.name+'.'+uuid4().hex+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,sort_keys=True),encoding='utf-8')
    temporary.replace(path)


def split_pdf(path,directory,*,max_pages=50,max_bytes=100_000_000):
    import fitz
    if max_pages<1 or max_bytes<1: raise ValueError('分段上限必须大于0')
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    segments=[]
    with fitz.open(path) as pdf:
        start=0
        while start<len(pdf):
            stop=min(start+max_pages,len(pdf))
            while True:
                with fitz.open() as part:
                    part.insert_pdf(pdf,from_page=start,to_page=stop-1)
                    # 固定文档ID避免同内容重试的PDF序列化随机ID导致缓存失效。
                    data=part.tobytes(garbage=3,deflate=True,no_new_id=True)
                if len(data)<=max_bytes: break
                if stop-start==1: raise ValueError('单页超过供应商字节上限')
                stop=start+max(1,(stop-start)//2)
            digest=content_hash(data)
            target=directory/f'{start:06d}-{stop:06d}-{digest[:16]}.pdf'
            if not target.exists(): target.write_bytes(data)
            elif content_hash(target.read_bytes())!=digest: raise ValueError('分段缓存hash不符')
            segments.append({'path':str(target),'sha256':digest,'segment_offset':start,'pages':stop-start,'bytes':len(data)})
            start=stop
    return segments
