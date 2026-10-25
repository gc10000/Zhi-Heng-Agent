"""确定性支持状态机；不从模型猜测补写事实。"""
from copy import deepcopy
from app.api.errors import APIError
from .models import SLOTS

QUESTIONS = {'question': '请描述需要解决的问题。', 'device': '请确认设备型号。', 'symptom': '请描述实际观察到的现象。'}


def initial():
    return {'version': 0, 'context_version': 0, 'state': 'awaiting_input', 'requested_slot': 'question',
            'prompt': QUESTIONS['question'], 'reason': 'missing_slot', 'rounds': 0, 'no_progress': 0,
            'slots': {s: {'value': None, 'confirmed': False, 'source': 'unknown'} for s in SLOTS},
            'citations': [], 'run_id': None, 'history': [], 'operations': [], 'tool_calls': []}


def decide(row):
    row['requested_slot'] = None
    if row['state'] in {'cancelled', 'resolved', 'handoff'}:
        row['prompt'] = '已结束；可保存转交草稿。'
        return row
    if row['no_progress'] >= 3:
        row.update(state='handoff', reason='no_progress', prompt='没有获得新信息，请转交人工支持。')
        return row
    for slot in QUESTIONS:
        fact = row['slots'][slot]
        if not fact['confirmed'] or not fact['value']:
            if row['rounds'] >= 3:
                row.update(state='handoff', reason='round_budget', prompt='补充信息已达上限，请转交人工支持。')
                return row
            row.update(state='awaiting_input', requested_slot=slot, prompt=QUESTIONS[slot], reason='missing_slot')
            return row
    if row.get('needs_evidence'):
        row.update(state='awaiting_input', reason='needs_fresh_evidence', prompt='上下文已纠正，请新建问答核对证据后继续。')
    elif not row['citations']:
        row.update(state='handoff', reason='missing_evidence', prompt='缺少可追溯证据，请补充资料或转交人工支持。')
    else:
        row.update(state='ready', reason='evidence_available', prompt='可依据资料生成待核对的操作清单；执行结果须由用户记录。')
    return row


def advance(current, data, *, at, run=None):
    row = deepcopy(current)
    if row['state'] in {'cancelled', 'resolved', 'handoff'}:
        raise APIError(409, 'support_terminal', '支持流程已结束，请从新的会话继续。')
    if data.expected_version != row['version']:
        raise APIError(409, 'version_conflict', '支持上下文已改变，请刷新后重试。')
    if any(not value.strip() or len(value) > 4000 for value in data.values.values()):
        raise APIError(422, 'invalid_slot', '补充信息不能为空且每项最多4000字。')
    row['history'].append({k: deepcopy(row[k]) for k in ('version', 'context_version', 'slots', 'run_id', 'state')})
    progress = False
    for key, value in data.values.items():
        value = value.strip()
        old = row['slots'][key]
        progress |= data.confirmed and (old['value'] != value or not old['confirmed'])
        row['slots'][key] = {'value': value, 'confirmed': data.confirmed, 'source': 'user_report' if data.confirmed else 'unconfirmed', 'recorded_at': at}
    if run:
        row['run_id'] = run['run_id']
        row['citations'] = deepcopy(run.get('citations', []))
        row['product_snapshot'] = deepcopy(run.get('product_snapshot', {}))
        if not row['slots']['question']['value']:
            row['slots']['question'] = {'value': run['question'], 'confirmed': True, 'source': 'user_question', 'recorded_at': at}
        progress = True
        row['evidence_slots'] = deepcopy(row['slots'])
        row['needs_evidence'] = False
    elif current['citations'] and any(current['slots'][key].get('confirmed') and current['slots'][key].get('value') != value.strip() for key, value in data.values.items()):
        row['needs_evidence'] = True
    row['no_progress'] = 0 if progress else row['no_progress'] + 1
    if current['state'] == 'awaiting_input':
        row['rounds'] += 1
    row['context_version'] += 1
    if data.action != 'update':
        row['state'] = {'handoff': 'handoff', 'resolve': 'resolved', 'cancel': 'cancelled'}[data.action]
        row['reason'] = 'user_' + data.action
    return decide(row)
