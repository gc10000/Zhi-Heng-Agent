"""按字符打包完整证据与最近历史；模板、问题及输出 token 另行管理。"""
import re


def readable_evidence(text):
    """只改变生成用投影；原始证据/引用保持不变，不猜测丢失图标的含义。"""
    from markdown_it import MarkdownIt
    protected=set()
    for token in MarkdownIt('default').parse(text):
        if token.type in {'fence','code_block'} and token.map:
            protected.update(range(*token.map))
    def prose(value):
        value=re.sub(r'\\(?:emptyset|varnothing)\b','〔未识别图标〕',value)
        return re.sub(r'(?:>\s*){2,}', '〔未识别图标路径〕',value)
    result=[]
    for i,line in enumerate(text.splitlines(keepends=True)):
        if i in protected:result.append(line);continue
        start=0;parts=[]
        for match in re.finditer(r'(?<!`)(`+)(?!`)[^\n]*?(?<!`)\1(?!`)',line):
            parts.extend((prose(line[start:match.start()]),match[0]));start=match.end()
        result.append(''.join(parts)+prose(line[start:]))
    return ''.join(result)


def pack_prompt_inputs(docs, history, max_chars=12000):
    if type(max_chars) is not int or max_chars < 0:
        raise ValueError('max_chars 必须是非负整数')
    context_blocks, messages, ids, indices = [], [], [], []
    used = 0
    for index, doc in enumerate(docs):
        text = readable_evidence((doc.get('text') or '').strip())
        if not text:
            continue
        # 编号按实际入选证据连续生成，元信息和分隔符计入预算。
        meta = [f'[{len(context_blocks) + 1}]']
        if doc.get('source'):
            meta.append(f"[{doc['source']}]")
        if doc.get('chunk_id') is not None:
            meta.append(f"[chunk_id={doc['chunk_id']}]")
        if doc.get('url'):
            meta.append(f"[url={doc['url']}]")
        if doc.get('score') is not None:
            meta.append(f"[score={float(doc['score']):.4f}]")
        if doc.get('title'):
            meta.append(f"[title={doc['title']}]")
        block = ' '.join(meta) + '\n' + text
        cost = len(block) + (2 if context_blocks else 0)
        if used + cost > max_chars:
            continue
        context_blocks.append(block)
        indices.append(index)
        if doc.get('chunk_id') is not None:
            ids.append(str(doc['chunk_id']))
        used += cost
    roles = {'user': '用户', 'assistant': '助手'}
    # 输入历史为正序；从最近向前选完整消息，最后再恢复正序。
    for msg in reversed(history):
        role, text = msg.get('role'), msg.get('text')
        if role not in roles or not text:
            continue
        block = f'{roles[role]}: {text}\n'
        if used + len(block) > max_chars:
            continue
        messages.append(block)
        used += len(block)
    return {'context': '\n\n'.join(context_blocks), 'history': ''.join(reversed(messages)),
            'used_chars': used, 'used_chunk_ids': ids, 'used_doc_indices': indices}
