"""解析器协议不承担全局客户端初始化或发布。"""
from pathlib import Path
from typing import Protocol
from app.ingestion.models import ParsedDocument


class Parser(Protocol):
    def parse(self,path:Path,*,document_id:str,revision_id:str) -> ParsedDocument: ...
