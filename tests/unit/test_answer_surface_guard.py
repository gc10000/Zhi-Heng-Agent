"""来源约束回答不能发布把内部规则写成产品依据的文本。"""
from types import SimpleNamespace

import pytest

from app.answering.errors import AnswerGenerationError
from app.query_process.agent.nodes.node_answer_output import step_3_generate_response
from tests.unit.test_source_relations import case


def state_for_source_answer():
    from app.answering.evidence_attribution import evidence_labels, payload

    policy, doc = case('设备甲通过介质乙连接到网关丙。')
    policy = payload(policy)
    reference_map = [dict(evidence_labels([doc], policy)[0], reference_number=1)]
    return dict(
        is_stream=True,
        session_id='synthetic-source-answer',
        evidence_attribution=policy,
        prompt_used_docs=[doc],
        prompt_reference_map=reference_map,
        answer_max_tokens=128,
        answer_token_field='max_tokens',
    )


class StreamClient:
    def __init__(self, parts):
        self.parts = parts

    def stream(self, prompt, **options):
        for part in self.parts:
            yield SimpleNamespace(
                content=part,
                response_metadata={},
                additional_kwargs={},
                usage_metadata={},
            )


def test_internal_rule_reference_is_rejected_before_any_streamed_or_saved_answer(monkeypatch):
    from app.query_process.agent.nodes import node_answer_output as node

    sent = []
    monkeypatch.setattr(node, 'push_to_session', lambda *args: sent.append(args))
    state = state_for_source_answer()

    with pytest.raises(AnswerGenerationError) as error:
        step_3_generate_response(
            state,
            '合成提示',
            client=StreamClient(['根据合同第', '7条，静态手册不能判断当前状态。']),
        )

    assert error.value.partial_answer == ''
    assert sent == []
    assert 'answer' not in state
    assert state['answer_surface_failure']['failure_code'] == 'internal_rule_leak'
    assert '根据合同第7条' not in str(state['answer_surface_failure'])


def test_source_relation_stream_is_released_only_after_surface_validation(monkeypatch):
    from app.query_process.agent.nodes import node_answer_output as node
    from app.utils.sse_utils import SSEEvent

    sent = []
    monkeypatch.setattr(node, 'push_to_session', lambda *args: sent.append(args))
    state = state_for_source_answer()

    result = step_3_generate_response(
        state,
        '合成提示',
        client=StreamClient(['设备甲通过介质乙', '连接到网关丙。[1]']),
    )

    assert result['answer'] == '设备甲通过介质乙连接到网关丙。[1]'
    assert sent == [(
        'synthetic-source-answer',
        SSEEvent.DELTA,
        {'delta': '设备甲通过介质乙连接到网关丙。[1]'},
    )]


def test_real_source_clause_can_be_quoted_without_being_mistaken_for_internal_rules():
    from app.answering.answer_surface_guard import failure_code

    assert failure_code('合同第7条规定保修期限。[1]', [dict(text='合同第7条规定保修期限。')]) is None
    assert failure_code('根据内部规则不能回答。', [dict(text='产品使用说明。')]) == 'internal_rule_leak'


def test_interrupted_source_answer_never_releases_unchecked_partial_content(monkeypatch):
    from app.query_process.agent.nodes import node_answer_output as node

    sent = []
    monkeypatch.setattr(node, 'push_to_session', lambda *args: sent.append(args))

    class Interrupted(StreamClient):
        def stream(self, prompt, **options):
            yield from super().stream(prompt, **options)
            raise TimeoutError('合成中断')

    with pytest.raises(AnswerGenerationError) as error:
        step_3_generate_response(state_for_source_answer(), '合成提示',
            client=Interrupted(['根据合同第7条']))
    assert error.value.partial_answer == '' and sent == []


def test_nonstream_source_answer_uses_the_same_rejection_boundary():
    state = state_for_source_answer() | dict(is_stream=False)

    class Client:
        def invoke(self, prompt, **options):
            return SimpleNamespace(content='依据内部规则不回答。', response_metadata={})

    with pytest.raises(AnswerGenerationError) as error:
        step_3_generate_response(state, '合成提示', client=Client())
    assert error.value.partial_answer == '' and 'answer' not in state
