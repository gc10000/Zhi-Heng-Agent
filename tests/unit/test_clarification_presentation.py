"""澄清审核快照应等于产品端和审核端的公开呈现。"""
from copy import deepcopy
import hashlib
from pathlib import Path

from app.evaluation.query_adapter import RealQueryExecutor
from app.knowledge.repository import fingerprint


def test_clarification_projection_freezes_both_visible_surfaces_and_source_identity():
    adapter = object.__new__(RealQueryExecutor)
    adapter.products = {'合成型号': 'p-1'}
    adapter.config = {
        'metric_schema_version': 1,
        'corpus': {'snapshot': {'products': [
            dict(product_id='p-1', model='合成型号', series='合成系列'),
        ]}},
    }
    candidates = [dict(
        product_id='p-1', model='合成型号', series='错误系列', worker_token='private',
    )]

    result = adapter.project_result(dict(
        run_id='run-1', state='awaiting_input', candidates=deepcopy(candidates),
    ))
    snapshot = result['presentation_snapshot']

    assert snapshot['state'] == 'awaiting_input'
    assert snapshot['behavior'] == 'clarify'
    assert snapshot['chat'] == {
        'heading': '请选择适用型号',
        'body': '不同型号可能使用不同参数。确认后才会在对应资料中检索。',
        'candidates': [dict(product_id='p-1', model='合成型号', series='合成系列')],
        'source': {
            'component': 'frontend/src/features/chat/components/ProductClarification.vue',
            'sha256': 'e336c172351bdefe42a03543ab12764ff87e7e517c4a597f647ba46d0090001b',
        },
    }
    assert snapshot['review'] == {
        'state_line': '运行状态：awaiting_input',
        'heading': '请选择适用型号',
        'body': '本轮请求确认设备型号，未生成答案。不同型号可能使用不同参数。确认后才会在对应资料中检索。',
        'candidates': [dict(product_id='p-1', model='合成型号')],
        'empty_candidates_note': None,
        'source': {
            'component': 'frontend/src/features/evaluation/ResultPresentation.vue',
            'sha256': 'bba73261ebf64252eb769447c7f777d796770f6390cc9aa7338bc8fc0ba5b741',
        },
    }
    unsigned = {key: value for key, value in snapshot.items() if key != 'sha256'}
    assert snapshot['sha256'] == fingerprint(unsigned)
    assert 'private' not in str(snapshot)
    assert '错误系列' not in str(snapshot)


def test_review_storage_keeps_the_frozen_presentation_snapshot():
    from types import SimpleNamespace
    from app.evaluation.repository import EvaluationRepository
    from app.evaluation.result_presentation import clarification_presentation_snapshot

    saved = []
    repo = object.__new__(EvaluationRepository)
    repo.experiments = SimpleNamespace(find_one=lambda _: {})
    repo.results = SimpleNamespace(replace_one=lambda query, value, **kw: saved.append(value))
    candidates = [dict(product_id='p-1', model='合成型号')]
    snapshot = clarification_presentation_snapshot(
        candidates, [dict(product_id='p-1', model='合成型号')],
    )
    repo.save_results('experiment', 1,
        [dict(id='question', category='clarification', question='合成问题')],
        [dict(id='question', status='completed', result=dict(
            state='awaiting_input', behavior='clarify', answer='', citations=[],
            candidates=candidates,
            presentation_snapshot=snapshot,
        ))],
    )

    assert saved[0]['result']['presentation_snapshot'] == snapshot


def test_result_storage_rejects_a_modified_clarification_snapshot():
    from types import SimpleNamespace
    import pytest
    from app.evaluation.repository import EvaluationRepository
    from app.evaluation.result_presentation import clarification_presentation_snapshot

    repo = object.__new__(EvaluationRepository)
    repo.experiments = SimpleNamespace(find_one=lambda _: {})
    repo.results = SimpleNamespace(replace_one=lambda *args, **kwargs: pytest.fail('损坏快照不得持久化'))
    candidates = [dict(product_id='p-1', model='合成型号')]
    snapshot = clarification_presentation_snapshot(
        candidates, [dict(product_id='p-1', model='合成型号')],
    )
    snapshot['review']['body'] = '被改写的审核文案'

    with pytest.raises(ValueError, match='澄清呈现快照哈希不匹配'):
        repo.save_results('experiment', 1,
            [dict(id='question', category='clarification', question='合成问题')],
            [dict(id='question', status='completed', result=dict(
                state='awaiting_input', behavior='clarify', candidates=candidates,
                presentation_snapshot=snapshot,
            ))],
        )


def test_result_read_rejects_a_modified_clarification_snapshot():
    from types import SimpleNamespace
    import pytest
    from app.evaluation.repository import EvaluationRepository
    from app.evaluation.result_presentation import clarification_presentation_snapshot

    candidates = [dict(product_id='p-1', model='合成型号')]
    snapshot = clarification_presentation_snapshot(
        candidates, [dict(product_id='p-1', model='合成型号')],
    )
    snapshot['review']['heading'] = '伪造呈现标题'

    class Cursor:
        def sort(self, *_):
            return self

        def limit(self, _):
            return self

        def __iter__(self):
            return iter([dict(question_id='question', result=dict(
                state='awaiting_input', behavior='clarify', candidates=candidates,
                presentation_snapshot=snapshot,
            ))])

    repo = object.__new__(EvaluationRepository)
    repo.experiments = SimpleNamespace(find_one=lambda _: {'result_attempt': 1})
    repo.results = SimpleNamespace(find=lambda _: Cursor())

    with pytest.raises(ValueError, match='澄清呈现快照哈希不匹配'):
        repo.results_page('experiment')


def test_presentation_component_hashes_bind_lf_normalized_source():
    from app.evaluation.result_presentation import (
        CHAT_COMPONENT, CHAT_SHA256, REVIEW_COMPONENT, REVIEW_SHA256,
    )

    root = Path(__file__).resolve().parents[2]
    for component, expected in (
        (CHAT_COMPONENT, CHAT_SHA256),
        (REVIEW_COMPONENT, REVIEW_SHA256),
    ):
        source = (root / component).read_bytes().replace(b'\r\n', b'\n').replace(b'\r', b'\n')
        assert hashlib.sha256(source).hexdigest() == expected


def test_clarification_snapshot_rejects_candidate_model_drift_from_frozen_catalog():
    from app.evaluation.result_presentation import clarification_presentation_snapshot

    try:
        clarification_presentation_snapshot(
            [dict(product_id='p-1', model='伪造型号')],
            [dict(product_id='p-1', model='冻结型号')],
        )
    except ValueError as error:
        assert str(error) == '澄清候选型号与冻结产品目录不一致'
    else:
        raise AssertionError('型号漂移不得进入产品显示或盲审呈现快照')


def test_empty_candidate_snapshot_includes_review_only_fallback_text():
    from app.evaluation.result_presentation import clarification_presentation_snapshot

    snapshot = clarification_presentation_snapshot([], [])

    assert snapshot['state'] == 'awaiting_input'
    assert snapshot['chat']['candidates'] == []
    assert snapshot['review']['state_line'] == '运行状态：awaiting_input'
    assert snapshot['review']['empty_candidates_note'] == (
        '本轮没有可展示的型号候选；需核对关联Run的只读材料，不能据此认定已选择具体型号。'
    )
