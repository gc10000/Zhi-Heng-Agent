"""连接比较模式的稳定导出接口。"""
from .connection_semantics import (
    VERSION, compare_connections, derive_connection_facts,
    render_connection_comparison,
)

__all__ = ['VERSION', 'derive_connection_facts', 'compare_connections',
    'render_connection_comparison']
