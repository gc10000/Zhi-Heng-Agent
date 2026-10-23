"""运行状态允许边；终态不得复活，确认与取消均需版本CAS。"""
from app.api.errors import APIError

EDGES = {
    'pending': {'running', 'cancel_requested', 'failed', 'interrupted'},
    'running': {'awaiting_input', 'cancel_requested', 'completed', 'failed', 'interrupted'},
    'awaiting_input': {'pending', 'cancel_requested', 'interrupted'},
    'cancel_requested': {'cancelled', 'interrupted'},
}


def check(source, target):
    if target not in EDGES.get(source, set()):
        raise APIError(409, 'state_conflict', '当前运行状态不接受此操作。')
