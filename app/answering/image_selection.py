"""答案显式配图协议v1：上下文资产不自动成为答案图片，不判断语义相关性。"""
from copy import deepcopy
import re


def answer_assets(answer, allowed=None):
    """与Vue markdown-it同源解析；只读取实际image token，不递归图片alt。"""
    from markdown_it import MarkdownIt
    parser = MarkdownIt('default', {'html': False, 'linkify': False, 'breaks': True})
    found = set()
    for block in parser.parse(answer):
        if block.type != 'inline':
            continue
        for token in block.children or []:
            if token.type != 'image':
                continue
            target = token.attrGet('src') or ''
            aid = (target[8:] if target.startswith('asset://') else
                   target[15:] if target.startswith('/api/v1/assets/') else '')
            # 与前端受控image renderer使用相同的ID白名单及大小写规则。
            if re.fullmatch(r'[A-Za-z0-9_-]+', aid) and (allowed is None or aid in allowed):
                found.add(aid)
    return found


def select_answer_images(answer, citations):
    rows = deepcopy(citations)
    used = answer_assets(answer, {aid for c in rows for aid in c.get('asset_ids', [])})
    for c in rows:
        c['answer_asset_ids'] = [aid for aid in c.get('asset_ids', []) if aid in used]
        c['image_selection_version'] = 1
    return rows


def has_review_images(result):
    """旧结果保守保留全部图像；新协议仅答案图参与配图维度。缺标记不跳过。"""
    # 重新解析正文，防止早期选择器错误写入context后让实际图片免审。
    if answer_assets(result.get('answer') or ''):
        return True
    return any((c.get('asset_sha256') or c.get('asset_ids')) and
        not (result.get('image_selection_version') == 1 and c.get('image_usage') == 'context')
        for c in result.get('citations', []))
