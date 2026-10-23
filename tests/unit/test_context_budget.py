import pytest


def capture_inputs(monkeypatch, node, **state):
    captured = {}
    def template(name, **kwargs):
        captured.update(kwargs)
        return str(kwargs)
    monkeypatch.setattr(node, 'load_prompt', template)
    node.step_2_construct_prompt(state)
    return captured


def test_oversize_first_document_does_not_hide_later_evidence(monkeypatch, answer_node):
    state = {'reranked_docs': [{'chunk_id': 'long', 'text': '长' * 12001}, {'chunk_id': 'short', 'text': '短证据'}]}
    packed = capture_inputs(monkeypatch, answer_node.module, **state)
    assert '短证据' in packed['context']
    assert '长' not in packed['context']


def test_oversize_history_is_not_appended_before_checking(monkeypatch, answer_node):
    packed = capture_inputs(monkeypatch, answer_node.module, history=[{'role': 'user', 'text': '长' * 13000}, {'role': 'user', 'text': '最近的问题'}])
    assert len(packed['context']) + len(packed['history']) <= 12000
    assert '最近的问题' in packed['history']


def test_history_does_not_count_previous_messages_repeatedly(monkeypatch, answer_node):
    history = [{'role': 'user', 'text': str(i) + '中' * 1900} for i in range(6)]
    packed = capture_inputs(monkeypatch, answer_node.module, history=history)
    assert all(m['text'] in packed['history'] for m in history)


def test_exact_boundary_metadata_and_separators():
    from app.answering.context_budget import pack_prompt_inputs
    docs = [{'chunk_id': 0, 'title': '标题', 'score': 0.5, 'text': '甲'}, {'chunk_id': 'b', 'text': '乙'}]
    full = pack_prompt_inputs(docs, [])
    exact = pack_prompt_inputs(docs, [], full['used_chars'])
    assert exact == full
    assert full['used_chars'] == len(full['context']) + len(full['history'])
    assert full['used_chunk_ids'] == ['0', 'b']
    assert pack_prompt_inputs(docs, [], full['used_chars'] - 1)['used_chunk_ids'] == ['0']


def test_recent_complete_messages_and_images_remain_intact():
    from app.answering.context_budget import pack_prompt_inputs
    url = 'https://example.invalid/a.png?signature=synthetic'
    docs = [{'chunk_id': 'image', 'text': f'【图片】\n![图]({url})'}]
    result = pack_prompt_inputs(docs, [{'role': 'user', 'text': '旧' * 200}, {'role': 'assistant', 'text': '新1'}, {'role': 'user', 'text': '新2'}], 150)
    assert url in result['context']
    assert result['history'] == '助手: 新1\n用户: 新2\n'
    assert result['used_chars'] == len(result['context']) + len(result['history']) <= 150


@pytest.mark.parametrize('limit', [-1, True, 0.5, None])
def test_invalid_budget(limit):
    from app.answering.context_budget import pack_prompt_inputs
    with pytest.raises(ValueError):
        pack_prompt_inputs([], [], limit)


def test_empty_zero_and_unknown_roles():
    from app.answering.context_budget import pack_prompt_inputs
    result = pack_prompt_inputs([{'text': 'a'}], [{'role': 'system', 'text': 'secret'}], 0)
    assert result == {'context': '', 'history': '', 'used_chars': 0, 'used_chunk_ids': [], 'used_doc_indices': []}


def test_output_images_only_come_from_packed_documents(monkeypatch, answer_node, session):
    from types import SimpleNamespace
    node = answer_node.module
    sid, _ = session
    monkeypatch.setattr(node, 'get_llm_client', lambda: SimpleNamespace(invoke=lambda p: SimpleNamespace(content='答案')))
    excluded = 'https://example.invalid/excluded.png'
    included = 'https://example.invalid/included.png'
    state = {'session_id': sid, 'is_stream': False, 'reranked_docs': [
        {'text': '长' * 12001 + f'![图]({excluded})'}, {'text': f'![图]({included})'}]}
    node.node_answer_output(state)
    assert answer_node.saved[-1]['image_urls'] == [included]
