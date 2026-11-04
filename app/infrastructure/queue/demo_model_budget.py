"""本轮宿主专用持久预留；失败不退款，重启不恢复额度。"""
import hashlib
import json
import os
import sqlite3
from pathlib import Path
from app.knowledge.repository import fingerprint


def reserve(kind, values):
    path=os.getenv('M7_DEMO_LOCAL_LEDGER')
    if not path:
        return
    auth=json.loads(Path(os.environ['M7_DEMO_LOCAL_AUTHORIZATION']).read_text('utf-8'))
    if auth.get('kind')!='m7_explicit_local_model_authorization_v1' or auth.get('limits')!={'texts':64,'reranks':8,'pairs':512}:
        raise ValueError('宿主授权缺失或范围漂移')
    if str(Path(path).resolve())!=auth['ledger_path']:
        raise ValueError('不能更换宿主账本领取新额度')
    if any(os.getenv(k)!=v for k,v in auth['model_configuration'].items()):
        raise ValueError('宿主模型配置漂移')
    identity=fingerprint(auth)
    counts=(len(values),0,0) if kind=='embedding' else (0,1,len(values))
    with sqlite3.connect(path,timeout=15) as db:
        db.execute('BEGIN IMMEDIATE')
        db.execute('CREATE TABLE IF NOT EXISTS account (id INTEGER PRIMARY KEY, identity TEXT, texts INTEGER, reranks INTEGER, pairs INTEGER)')
        db.execute('CREATE TABLE IF NOT EXISTS receipts (id INTEGER PRIMARY KEY, kind TEXT, count INTEGER, input_sha256 TEXT)')
        db.execute('INSERT OR IGNORE INTO account VALUES (1,?,0,0,0)',(identity,))
        row=db.execute('SELECT identity,texts,reranks,pairs FROM account WHERE id=1').fetchone()
        totals=tuple(a+b for a,b in zip(row[1:],counts))
        if row[0]!=identity or any(n>lim for n,lim in zip(totals,(64,8,512))):
            raise ValueError('宿主调用累计预留超限或身份冲突')
        db.execute('UPDATE account SET texts=?,reranks=?,pairs=? WHERE id=1',totals)
        db.execute('INSERT INTO receipts(kind,count,input_sha256) VALUES (?,?,?)',(kind,len(values),fingerprint(values)))
