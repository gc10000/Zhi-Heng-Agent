"""人工核对原件后登记的完整型号等价关系；禁止由后缀规则推导新型号。"""
from dataclasses import dataclass


@dataclass(frozen=True)
class SourceEquivalence:
    canonical_model: str
    brand: str
    variant: str
    source_file: str
    source_sha256: str
    physical_page: int
    section: str
    excerpt: str


# 只确认原文中的完整 GM/GU 写法，不推导 GM、GU 或其他任意后缀。
SOURCE_EQUIVALENCES = (
    SourceEquivalence(
        canonical_model='H3C LA2608',
        brand='H3C',
        variant='LA2608-GM/GU',
        source_file='H3C LA2608室内无线网关 用户手册-6W100-整本手册.pdf',
        source_sha256='72983cc9b60f7f165bf89d3f6cbe39d56c4db148fd4b894c70c37378f8be5c8e',
        physical_page=4,
        section='1.1 概述',
        excerpt='H3C LA2608-GM/GU 室内无线网关（以下简称LA2608）',
    ),
)
