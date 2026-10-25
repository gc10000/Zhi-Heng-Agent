"""仅导出用户确认快照；所有动态文本转义，URL由服务端固定生成。"""
import html
import re
from urllib.parse import quote
from app.api.errors import APIError


def escape(value):
    text = html.escape(str(value), quote=False).replace('\r\n','\n').replace('\r','\n')
    text = re.sub(r'([\\`*_{}\[\]()#+.!|>~])', r'\\\1', text)
    text = re.sub(r'(?m)^(-)(?=\s)', r'\\\1', text)
    return text.replace('\n', '  \n    ')


def export_markdown(case):
    if case['status'] != 'confirmed':
        raise APIError(409, 'case_unconfirmed', '请先由用户确认保存草稿，再导出。')
    lines = ['# 用户确认的技术支持记录', '', '系统未实际执行设备操作；操作结果均为用户自报。', '',
             '记录：' + escape(case['case_id']), '确认时间：' + escape(case['confirmed_at']),
             '来源运行：' + escape(case['run_id']), '']
    labels = {'question':'问题','device':'设备','symptom':'现象','environment':'环境','error_code':'错误码','tried':'已尝试','summary':'处理摘要','handoff_reason':'转交原因'}
    for key, value in case['fields'].items():
        lines.extend(['## ' + labels.get(key, '用户字段'), '', escape(value), ''])
    lines.extend(['## 实际操作与用户自报', ''])
    for operation in case['operations']:
        lines.extend(['资料建议（不表示已执行）：' + escape(operation['suggestion']),
            '前提：' + escape(operation['prerequisites']), '风险：' + escape(operation['risk']),
            '用户记录状态：' + escape(operation['status'])])
        for report in operation['reports']:
            lines.append('用户自报 ' + escape(report['recorded_at']) + '：' + escape(report['status']) + ' · ' + escape(report['note']))
        lines.append('')
    lines.extend(['## 资料修订与引用', ''])
    for citation in case['citations']:
        lines.append('资料 ' + escape(citation['document_id']) + ' / 修订 ' + escape(citation['revision_id']) + ' / 切片 ' + escape(citation['chunk_uid']))
        lines.append('来源定位：' + escape(citation.get('source_refs', [])))
        lines.append('原文：' + escape(citation.get('text','')))
    return {'filename': 'support-case-' + case['case_id'] + '.md', 'markdown': '\n'.join(lines), 'case_version': case['version']}
