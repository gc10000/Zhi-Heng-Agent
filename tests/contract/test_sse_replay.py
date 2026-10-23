"""SSE入口遵循同一身份及游标契约。"""
from tests.contract.test_auth import auth_client


def test_events_require_authentication(auth_client):
    client, _, _ = auth_client
    response = client.get('/api/v1/runs/unknown/events')
    assert response.status_code == 401


def test_delta_merges_by_time_and_flush_preserves_all_text():
    from app.runs.events import DeltaBuffer
    now, received = [0.0], []
    buffer = DeltaBuffer(lambda kind, payload: received.append((kind, payload)), clock=lambda: now[0])
    buffer.add('甲')
    now[0] = .05
    buffer.add('乙')
    assert received == []
    now[0] = .08
    buffer.add('丙')
    assert received == [('answer.delta', {'text': '甲乙丙'})]
    buffer.add('丁')
    buffer.flush()
    assert ''.join(p['text'] for _, p in received) == '甲乙丙丁'
