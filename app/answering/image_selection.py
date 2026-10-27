"""答案显式配图协议v1：上下文资产不自动成为答案图片，不判断语义相关性。"""
from copy import deepcopy
import re


def answer_assets(answer, allowed):
    """只认受控行内图片；代码块、代码跨度、转义语法不构成图片使用。"""
    lines, fence = [], None
    for line in answer.splitlines(keepends=True):
        marker = re.match(r' {0,3}(`{3,}|~{3,})(.*)', line)
        if fence:
            if marker and marker[1][0] == fence[0] and len(marker[1]) >= len(fence) and not marker[2].strip():
                fence = None
            lines.append('\n')
        elif marker:
            fence = marker[1]
            lines.append('\n')
        elif line.startswith(('    ', '\t')):
            lines.append('\n')
        else:
            lines.append(line)
    text = ''.join(lines)
    # 仅成对等长反引号是代码跨度；未闭合反引号不吞掉后续正常正文。
    text = re.sub(r'(`+)(?!`)(.*?)(?<!`)\1(?!`)', '', text, flags=re.S)
    found = set()
    for match in re.finditer(r'!\[[^\]\n]*\]\((?:asset://|/api/v1/assets/)([^\s)]+)\)', text):
        before = text[:match.start()]
        slashes = len(before) - len(before.rstrip('\\'))
        if slashes % 2 == 0 and match[1] in allowed:
            found.add(match[1])
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
    return any((c.get('asset_sha256') or c.get('asset_ids')) and
        not (result.get('image_selection_version') == 1 and c.get('image_usage') == 'context')
        for c in result.get('citations', []))
