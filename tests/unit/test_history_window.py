import pytest
def get_recent_messages(*args, **kwargs):
    from app.clients.mongo_history_utils import get_recent_messages as read
    return read(*args, **kwargs)


def test_latest_ten_are_returned_in_chronological_order(history_store):
    history_store.seed([{'_id': f'{i:02}', 'session_id': 's1', 'ts': i, 'text': str(i)} for i in range(1, 21)])
    assert [m['ts'] for m in get_recent_messages('s1', 10)] == list(range(11, 21))
    assert history_store.last_sort == [('ts', -1), ('_id', -1)]


def test_equal_timestamps_are_stable_and_session_isolated(history_store):
    history_store.seed([{'_id': i, 'ts': 1, 'session_id': sid} for sid in ['s1', 's2'] for i in [3, 1, 2]])
    result = get_recent_messages('s1', 2)
    assert [m['_id'] for m in result] == [2, 3]
    assert all(m['session_id'] == 's1' for m in result)


def test_empty_and_small_window(history_store):
    assert get_recent_messages('empty') == []
    history_store.seed([{'_id': 1, 'ts': 1, 'session_id': 's'}])
    assert len(get_recent_messages('s', 10)) == 1


@pytest.mark.parametrize('limit', [0, -1, True, 1.5, '2', None])
def test_invalid_limit_is_rejected_before_io(history_store, limit):
    with pytest.raises(ValueError, match='limit'):
        get_recent_messages('s1', limit)
    assert history_store.last_sort is None
