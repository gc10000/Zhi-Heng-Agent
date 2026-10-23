"""在分段输出边界保留完整图片语法，仅放行本轮入选资产。"""
import re


class AnswerFilter:
    def __init__(self, allowed_assets, send):
        self.allowed = set(allowed_assets)
        self.send, self.pending, self.answer = send, '', ''

    def write(self, text, *, final=False):
        self.pending += text
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
                end = self.pending.find('>')
                if end < 0:
                    if final:
                        self.pending = ''
                    break
                # 模型不应在答案中输出HTML；统一去除，避免img/src和事件属性绕过。
                self.pending = self.pending[end + 1:]
            elif len(self.pending) == 1 and not final:
                break
            elif not self.pending.startswith('!['):
                self._send('!')
                self.pending = self.pending[1:]
            else:
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
