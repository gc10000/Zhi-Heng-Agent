"""有出处的原文操作摘录；记录自报不代表系统实际执行。"""
import re
from copy import deepcopy
from app.api.errors import APIError
from app.knowledge.models import stable_id


def build_checklist(current, run):
    row = deepcopy(current)
    seen = {operation['operation_id'] for operation in row['operations']}
    for citation in run.get('citations', []):
        text = citation.get('text', '').strip()
        # 保留整段前提而非逐句截断；超长/无动作的证据交给用户查原文。
        if not text or len(text) > 4000 or not re.search('检查|核对|设置|连接|断开|断电|重启|确认', text):
            continue
        identity = stable_id('operation', run['conversation_id'], [citation['document_id'], citation['revision_id'], citation['chunk_uid'], text])
        if identity in seen:
            continue
        if len(row['operations']) >= 20:
            break
        seen.add(identity)
        row['operations'].append({'operation_id': identity, 'run_id': run['run_id'],
            'context_version': current['context_version'], 'suggestion': text,
            'origin': 'evidence_excerpt', 'prerequisites': text,
            'risk': '操作前请核对原文适用前提与设备状态；涉及电气、复位或停机时请由合格人员人工确认。',
            'citation_ids': [citation['citation_id']], 'citations': [deepcopy(citation)],
            'status': 'not_tried', 'reports': []})
    return row


def record_result(current, operation_id, data, *, at, user_id):
    row = deepcopy(current)
    step = next((s for s in row['operations'] if s['operation_id'] == operation_id), None)
    if step is None:
        raise APIError(404, 'not_found', '操作步骤不存在。')
    if not data.note.strip():
        raise APIError(422, 'result_required', '请记录实际观察结果。')
    if len(step['reports']) >= 100:
        raise APIError(409, 'report_limit', '本步骤记录已达上限，请转交人工支持。')
    step['reports'].append({'status': data.status, 'note': data.note.strip(), 'recorded_at': at,
                            'source': 'user_report', 'user_id': user_id})
    step['status'] = data.status
    row['context_version'] += 1
    if all(step['status'] == 'ineffective' for step in row['operations']):
        row.update(state='handoff', reason='all_steps_ineffective', requested_slot=None,
                   prompt='已有可追溯步骤均被用户记录为无效，停止重复建议并转交人工支持。')
    return row
