"""扩展名归一并验证实际文件结构，路由不暗中降级成成功。"""
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET


class UnsupportedFormatError(ValueError):
    pass


def detect_format(path) -> str:
    path=Path(path)
    kind=path.suffix.lower().lstrip('.')
    if kind not in {'pdf','md','xlsx'}:
        raise UnsupportedFormatError('仅支持PDF、Markdown、XLSX')
    if not path.is_file():
        raise ValueError('原件文件不存在')
    try:
        if kind=='pdf':
            import fitz
            try:
                with fitz.open(path) as pdf:
                    if not pdf.is_pdf or pdf.is_encrypted or pdf.page_count<1:
                        raise ValueError('PDF不可读取或加密')
            except fitz.FileDataError as exc:
                raise ValueError('PDF结构损坏') from exc
        elif kind=='xlsx':
            with zipfile.ZipFile(path) as book:
                for name in ('[Content_Types].xml','xl/workbook.xml','xl/_rels/workbook.xml.rels'):
                    ET.fromstring(book.read(name))
        else:
            data=path.read_bytes()
            if b'\x00' in data or data.startswith((b'%PDF-',b'PK\x03\x04')):
                raise ValueError('Markdown必须为文本')
            data.decode('utf-8-sig')
    except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.ParseError) as exc:
        raise ValueError('原件实际结构与声明格式不符') from exc
    return kind


class ParserRouter:
    def __init__(self,parsers):
        self.parsers=parsers

    def parse(self,path,*,document_id,revision_id):
        kind=detect_format(path)
        if kind not in self.parsers:
            raise UnsupportedFormatError('该格式解析器尚未配置')
        return self.parsers[kind].parse(Path(path),document_id=document_id,revision_id=revision_id)
