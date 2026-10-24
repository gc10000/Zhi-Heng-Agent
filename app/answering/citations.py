"""引用编号在流式边界即核验，来源和资产在模型调用前核验。"""
import re
from app.api.errors import APIError


def validate_citation_sources(citations,revisions,*,asset_lookup):
    allowed={(r['document_id'],r['active_revision_id']) for r in revisions}
    for citation in citations:
        identity=(citation['document_id'],citation['revision_id'])
        if identity not in allowed:raise APIError(422,'citation_scope_invalid','引用超出本轮已授权修订。')
        for ref in citation['source_refs']:
            if ref.get('document_id') not in (None,identity[0]) or ref.get('revision_id') not in (None,identity[1]):
                raise APIError(422,'citation_scope_invalid','引用位置与资料修订不一致。')
        for aid in citation['asset_ids']:
            asset=asset_lookup(aid)
            if not asset or (asset['document_id'],asset['revision_id'])!=identity:
                raise APIError(422,'citation_scope_invalid','引用图片与资料修订不一致。')


class CitationGuard:
    def __init__(self,allowed_numbers,send):
        self.allowed=set(allowed_numbers)
        self.send=send
        self.pending=''
        self.last=''
        self.code_delimiter=0
        self.ticks=0
        self.image=False

    def _send(self,text):
        if text:self.send(text);self.last=text[-1]

    def _validate(self,value):
        body=value[1:-1].strip()
        if not re.fullmatch(r'\d+(?:\s*(?:[,，、-]|–)\s*\d+)*',body):
            if re.search(r'\d',body) and re.fullmatch(r'[\d\s,，、–-]+',body):
                raise APIError(422,'answer_citation_invalid','回答引用编号格式无效。')
            return
        numbers=[int(n) for n in re.findall(r'\d+',body)]
        if any(n not in self.allowed for n in numbers):
            raise APIError(422,'answer_citation_invalid','回答包含本轮未提供的引用编号。')
        if re.search('[-–]',body):
            if len(numbers)!=2 or numbers[0]>numbers[1] or any(n not in self.allowed for n in range(numbers[0],numbers[1]+1)):
                raise APIError(422,'answer_citation_invalid','回答引用范围无效。')

    def write(self,text,*,final=False):
        for char in text:
            if self.pending:
                if char=='[':
                    self._send(self.pending);self.pending='[';self.image=False;continue
                self.pending+=char
                if char==']':
                    if not self.image:self._validate(self.pending)
                    self._send(self.pending);self.pending=''
                elif len(self.pending)>128:
                    if re.fullmatch(r'\[[\d\s,，、–-]*',self.pending):
                        raise APIError(422,'answer_citation_invalid','回答引用编号格式过长。')
                    self._send(self.pending);self.pending=''
                elif not self.image and not (char.isdecimal() or char.isspace() or char in ',，、–-'):
                    self._send(self.pending);self.pending=''
                continue
            if char=='`':
                self.ticks+=1;self._send(char);continue
            if self.ticks:
                if self.code_delimiter==0:self.code_delimiter=self.ticks
                elif self.code_delimiter==self.ticks:self.code_delimiter=0
                self.ticks=0
            if char=='[' and not self.code_delimiter:
                self.pending='[';self.image=self.last=='!'
            else:self._send(char)
        if final and self.pending:
            if re.fullmatch(r'\[[\d\s,，、–-]+',self.pending) and not self.image:
                raise APIError(422,'answer_citation_invalid','回答引用编号未完成。')
            self._send(self.pending);self.pending=''
