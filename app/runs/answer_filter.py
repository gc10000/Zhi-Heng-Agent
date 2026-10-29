"""保留技术文字；代码外HTML只作可见文本，图片仅放行本轮入选资产。"""
import re


class AnswerFilter:
    def __init__(self, allowed_assets, send):
        self.allowed = set(allowed_assets)
        self.send, self.pending, self.answer = send, '', ''
        self.source = ''

    def _code_ranges(self):
        from app.runs.answer_markdown import code_ranges
        return code_ranges(self.source)

    def _block_code_ranges(self):
        from app.runs.answer_markdown import code_ranges
        return code_ranges(self.source, blocks_only=True, stable_openers=True)

    def write(self, text, *, final=False):
        self.source += text
        self.pending += text
        code_ranges = None
        block_ranges = None
        while self.pending:
            positions = [i for i in (self.pending.find('!'), self.pending.find('<')) if i >= 0]
            if not positions:
                self._send(self.pending)
                self.pending = ''
                break
            first = min(positions)
            if first:
                self._send(self.pending[:first])
                self.pending = self.pending[first:]
            if self.pending.startswith('<'):
                if block_ranges is None:
                    block_ranges = self._block_code_ranges()
                position = len(self.source) - len(self.pending)
                if any(start <= position < end for start, end in block_ranges):
                    self._send('<')
                    self.pending = self.pending[1:]
                    continue
                # 未闭合的行内代码可能由后续分段闭合；空行边界或final才确定解释。
                normalized = self.pending.replace('\r\n', '\n').replace('\r', '\n')
                if not final and not re.search(r'\n[ \t]*\n', normalized):
                    break
                if code_ranges is None:
                    code_ranges = self._code_ranges()
                position = len(self.source) - len(self.pending)
                in_code = any(start <= position < end for start, end in code_ranges)
                # 用CommonMark转义保留可见字符，禁止将其解释为HTML标签。
                backslashes = len(re.search(r'\\*$', self.source[:position]).group())
                self._send('<' if in_code or backslashes % 2 else r'\<')
                self.pending = self.pending[1:]
            else:
                if block_ranges is None:
                    block_ranges = self._block_code_ranges()
                position = len(self.source) - len(self.pending)
                if any(start <= position < end for start, end in block_ranges):
                    self._send('!')
                    self.pending = self.pending[1:]
                    continue
                if not self.pending.startswith('!['):
                    if len(self.pending) == 1 and not final:
                        break
                    self._send('!')
                    self.pending = self.pending[1:]
                    continue
                # 未闭合的行内代码在后续反引号到达前可能包含image样式文本；
                # 等段落定型后再解析一次，避免代码被改写和逐字符重复解析。
                normalized = self.pending.replace('\r\n', '\n').replace('\r', '\n')
                if not final and not re.search(r'\n[ \t]*\n', normalized):
                    break
                if code_ranges is None:
                    code_ranges = self._code_ranges()
                position = len(self.source) - len(self.pending)
                in_code = any(start <= position < end for start, end in code_ranges)
                if in_code:
                    self._send('!')
                    self.pending = self.pending[1:]
                    continue
                match = re.match(r'!\[([^\]\n]*)\]\(([^\n)]*)\)', self.pending)
                if match:
                    target = match.group(2).strip()
                    aid = target[8:] if target.startswith('asset://') else target.removeprefix('/api/v1/assets/')
                    if aid in self.allowed and target in {'asset://' + aid, '/api/v1/assets/' + aid}:
                        self._send('![' + match.group(1) + '](/api/v1/assets/' + aid + ')')
                    else:
                        self._send('（图片未在授权来源中登记）')
                    self.pending = self.pending[match.end():]
                elif final or '\n' in self.pending or len(self.pending) > 8192:
                    # 引用式/残缺图片不交给浏览器解释；正文后续行仍保留。
                    end = self.pending.find('\n')
                    self._send('（图片语法未通过来源检查）')
                    self.pending = self.pending[end:] if end >= 0 else ''
                else:
                    break

    def _send(self, value):
        if value:
            self.send(value)
            self.answer += value
