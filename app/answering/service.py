"""完整渲染后计数；模板、问题、历史和输出预留共同受模型窗口限制。"""
import os
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from app.api.errors import APIError
from .context_budget import pack_prompt_inputs


class AnswerBudget(BaseModel):
    model_config=ConfigDict(extra='forbid',frozen=True)
    context_window:int=Field(default=32768,ge=256,le=2_000_000,strict=True)
    output_tokens:int=Field(default=4096,ge=1,le=262144,strict=True)
    reserve_tokens:int=Field(default=256,ge=0,le=8192,strict=True)
    max_chars:int=Field(default=12000,ge=0,le=12000,strict=True)
    output_token_field:Literal['max_tokens','max_completion_tokens']='max_tokens'

    @model_validator(mode='after')
    def available(self):
        if self.output_tokens+self.reserve_tokens>=self.context_window:raise ValueError('输出及安全预留超过模型窗口')
        return self

    @classmethod
    def load(cls):
        raw=os.getenv('ANSWER_BUDGET_JSON','').strip()
        if not raw:return cls()
        try:return cls.model_validate_json(raw)
        except ValueError:raise ValueError('ANSWER_BUDGET_JSON须为有效有界JSON，详见配置文档') from None


def count_tokens(text,counter=None):
    # 无准确生成模型tokenizer时每UTF-8字节计1，另留协议安全余量；不是精确使用量。
    count=counter(text) if counter is not None else len(text.encode('utf-8'))
    if type(count) is not int or count<0:raise ValueError('token计数器须返回非负整数')
    return count


def _atomic_groups(docs,groups):
    parents=list(range(len(docs)))
    def root(i):
        while parents[i]!=i:i=parents[i]
        return i
    ids={str(d.get('chunk_uid',d.get('chunk_id'))):i for i,d in enumerate(docs)}
    for group in groups:
        if not group:continue
        if any(uid not in ids for uid in group):raise APIError(422,'evidence_group_invalid','完整证据组缺少前提。')
        first=root(ids[group[0]])
        for uid in group:parents[root(ids[uid])]=first
    result={}
    for i in range(len(docs)):result.setdefault(root(i),[]).append(i)
    return list(result.values())


def build_budgeted_prompt(docs,history,*,question,items,render,budget,groups=(),counter=None,attributions=None):
    budget=AnswerBudget.model_validate(budget)
    limit=budget.context_window-budget.output_tokens-budget.reserve_tokens
    def pack(indices,messages):
        packed=pack_prompt_inputs([docs[i] for i in indices],messages,budget.max_chars,
            attributions=[attributions[i] for i in indices] if attributions is not None else None)
        prompt=render(context=packed['context'],history=packed['history'],question=question,item_names=items)
        return packed,prompt,count_tokens(prompt,counter)
    _,base,fixed=pack([],[])
    if fixed>limit:raise APIError(422,'prompt_budget_exceeded','问题或固定提示内容超过模型输入预算，请缩短问题。')
    chosen=[]
    for group in _atomic_groups(docs,groups):
        trial=chosen+group
        packed,prompt,tokens=pack(trial,[])
        if len(packed['used_doc_indices'])==len(trial) and tokens<=limit:chosen=trial
    messages=[]
    for message in reversed(history):
        if message.get('role') not in ('user','assistant') or not message.get('text'):continue
        trial=[message]+messages
        packed,prompt,tokens=pack(chosen,trial)
        expected=''.join(('用户' if m['role']=='user' else '助手')+': '+m['text']+'\n' for m in trial)
        if packed['history']==expected and tokens<=limit:messages=trial
    packed,prompt,tokens=pack(chosen,messages)
    if tokens>limit:raise APIError(422,'prompt_budget_exceeded','提示内容超过模型输入预算。')
    return packed|dict(prompt=prompt,used_doc_indices=chosen,
        budget=dict(policy=budget.model_dump(),counter='provided_tokenizer' if counter else 'utf8_bytes_upper_bound',
            input_tokens=tokens,fixed_tokens=fixed,input_limit=limit,output_tokens=budget.output_tokens,
            omitted_documents=len(docs)-len(chosen),omitted_history=len(history)-len(messages)))
