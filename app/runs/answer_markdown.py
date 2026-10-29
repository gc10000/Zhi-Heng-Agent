"""仅为答案过滤映射实际inline容器；不改变语料处理的源码坐标契约。"""
import re

from markdown_it import MarkdownIt

from app.core.markdown_source import inline_code_ranges


def _map_paragraph_lines(rule, original_positions):
    """在列表/引用恢复缩进状态之前，记录解析器实际getLines的坐标。"""
    def mapped_rule(state, start, end, silent):
        previous = len(state.tokens)
        accepted = rule(state, start, end, silent)
        if not accepted or silent:
            return accepted
        for token in state.tokens[previous:]:
            if token.type != 'inline' or not token.map:
                continue
            lines, positions = [], []
            for row in range(*token.map):
                line = state.getLines(row, row + 1, state.blkIndent, False)
                # getLines只消费前缀并可能添加虚拟空格；其余字符是截止eMarks
                # 的原文后缀。固定尾坐标核对，不以模糊搜索猜测容器起点。
                suffix = line.lstrip(' ')
                stop = state.eMarks[row]
                begin = stop - len(suffix)
                if begin < state.bMarks[row] or state.src[begin:stop] != suffix:
                    break
                virtual = len(line) - len(suffix)
                lines.append(line)
                positions.extend([None] * virtual + original_positions[begin:stop])
                positions.append(None)
            else:
                content = '\n'.join(lines)
                if content.strip() == token.content:
                    left = len(content) - len(content.lstrip())
                    token.meta['answer_positions'] = positions[left:left + len(token.content)]
        return accepted
    return mapped_rule


def code_ranges(source, *, blocks_only=False, stable_openers=False):
    offsets = [0] + [m.end() for m in re.finditer(r'\r\n?|\n', source)]
    if offsets[-1] != len(source):
        offsets.append(len(source))
    md = MarkdownIt('default', {'html': False})
    if not blocks_only:
        from markdown_it.rules_block import lheading, paragraph
        # 核心normalize把CRLF/CR变为LF；字符坐标仍指向未改写的原始流。
        original_positions = [m.start() for m in re.finditer(r'\r\n?|[^\r]', source)]
        for name, rule in (('paragraph', paragraph), ('lheading', lheading)):
            md.block.ruler.at(name, _map_paragraph_lines(rule, original_positions))
    tokens = md.parse(source)
    ranges, cursors = [], {}
    for index, token in enumerate(tokens):
        if not token.map:
            continue
        start, end = token.map
        if token.type in {'fence', 'code_block'}:
            # 反引号围栏info尚可在同一行被追加字符判为无效；不能提前放行。
            opening = source[offsets[start]:offsets[start + 1]]
            if stable_openers and token.type == 'fence' and not opening.endswith(('\r', '\n')):
                continue
            ranges.append((offsets[start], offsets[end]))
            continue
        if blocks_only or token.type != 'inline':
            continue
        if 'answer_positions' in token.meta:
            positions = token.meta['answer_positions']
            for left, right in inline_code_ranges(token.content, html=False):
                ranges.extend((pos, pos + 1) for pos in positions[left:right] if pos is not None)
            continue
        # 行map只限定查找窗口；代码识别始终针对实际token.content，尤其不能
        # 将表格不同单元格的反引号拿到整行上重新配对。
        table_cell = index > 0 and tokens[index - 1].type in {'td_open', 'th_open'}
        positions = []
        valid = True
        for row, content in enumerate(token.content.split('\n'), start):
            if row >= end:
                valid = False
                break
            begin, stop = offsets[row], offsets[row + 1]
            raw = source[begin:stop].rstrip('\r\n')
            mapped = [(char, begin + pos) for pos, char in enumerate(raw)
                      if not (table_cell and char == '\\' and raw[pos + 1:pos + 2] == '|')]
            text = ''.join(char for char, _ in mapped)
            # 容器仅去掉引用/列表前缀、表格转义和缩进；精确查找而非模糊猜坐标。
            minimum = cursors.get(row, begin) if table_cell else begin
            cursor = next((i for i, (_, pos) in enumerate(mapped) if pos >= minimum), len(mapped))
            found = text.find(content, cursor)
            if found < 0:
                valid = False
                break
            line_positions = [pos for _, pos in mapped[found:found + len(content)]]
            positions.extend(line_positions)
            positions.append(None)  # token内的换行不属于需放行的特殊字符。
            if table_cell and line_positions:
                cursors[row] = line_positions[-1] + 1
        if not valid:
            continue  # 无法精确映射时不授予代码豁免。
        for left, right in inline_code_ranges(token.content, html=False):
            ranges.extend((pos, pos + 1) for pos in positions[left:right] if pos is not None)
    return ranges
