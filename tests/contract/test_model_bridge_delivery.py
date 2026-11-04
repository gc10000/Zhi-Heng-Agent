"""容器重排沿受控宿主复用，不在轻量API中隐式加载CUDA。"""
from fastapi.testclient import TestClient
import pytest
from types import SimpleNamespace


def test_model_ready_does_not_load_weights(monkeypatch):
    from app.infrastructure.model_host import app
    monkeypatch.setenv('MODEL_HOST_TOKEN', 'synthetic-model-token')
    with TestClient(app) as client:
        assert client.get('/health/ready').status_code == 401
        response = client.get('/health/ready', headers={'X-Model-Token': 'synthetic-model-token'})
        assert response.status_code == 503
        assert response.json()['ready'] is False


def test_rerank_bridge_uses_existing_normalized_implementation(monkeypatch):
    from app.infrastructure.model_host import app
    from app.lm import reranker_utils
    monkeypatch.setenv('MODEL_HOST_TOKEN', 'synthetic-model-token')
    seen = []
    def scores(pairs, **options):
        seen.append((pairs, options))
        return [0.8, 0.2]
    monkeypatch.setattr(reranker_utils, 'compute_rerank_scores', scores)
    with TestClient(app) as client:
        response = client.post('/rerank', headers={'X-Model-Token': 'synthetic-model-token'},
                               json={'pairs': [['问题', '原文1'], ['问题', '原文2']]})
        assert response.status_code == 200 and response.json() == {'scores': [0.8, 0.2]}
        assert seen[0][1] == {'normalize': True}


@pytest.mark.parametrize('scores', [[.8, .2], [True, .2], [float('nan'), .2], ['.8', .2], [.8]])
def test_host_client_preserves_pairs_disables_redirect_and_rejects_invalid_scores(monkeypatch, scores):
    from app.infrastructure.queue import model_client
    monkeypatch.setenv('MODEL_HOST_URL', 'http://synthetic.invalid')
    monkeypatch.setenv('MODEL_HOST_TOKEN', 'synthetic-token')
    monkeypatch.setenv('PROVIDER_POLICY_ENABLED', 'false')
    seen = []
    class HTTP:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            seen.append(kwargs)
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'scores': scores})
    monkeypatch.setattr(model_client.requests, 'Session', HTTP)
    if scores == [.8, .2] and type(scores[0]) is float:
        assert model_client.HostReranker()([['q', 'a'], ['q', 'b']]) == scores
    else:
        with pytest.raises(ValueError): model_client.HostReranker()([['q', 'a'], ['q', 'b']])
    assert seen[0]['json'] == {'pairs': [['q', 'a'], ['q', 'b']]}
    assert seen[0]['allow_redirects'] is False


@pytest.mark.parametrize('remote', [False, True])
def test_query_runner_rerank_keeps_title_pairs_and_order_across_bridge(monkeypatch, remote):
    from app.runs.query_runner import rerank
    from app.infrastructure.queue.model_client import HostReranker
    from app.lm import reranker_utils
    seen = []
    monkeypatch.setenv('MODEL_HOST_URL', 'http://synthetic.invalid' if remote else '')
    monkeypatch.setenv('MODEL_HOST_TOKEN', 'synthetic' if remote else '')
    def local(pairs, **options):
        assert not remote and options == {'normalize': True}
        seen.append(pairs)
        return [.2, .8]
    def host(self, pairs):
        assert remote
        seen.append(pairs)
        return [.2, .8]
    monkeypatch.setattr(reranker_utils, 'compute_rerank_scores', local)
    monkeypatch.setattr(HostReranker, '__call__', host)
    values = rerank('q', [{'text': 'a', 'title': '机身', 'chunk_uid': 'a'}, {'text': 'b', 'metadata': {'heading_path': ['配件']}, 'chunk_uid': 'b'}])
    assert [v['chunk_uid'] for v in values] == ['b', 'a']
    assert seen == [[['q', '章节：机身\na'], ['q', '章节：配件\nb']]]


@pytest.mark.parametrize('count, passage_length', [(65, 8), (1000, 8), (4, 100000)])
def test_host_rerank_batches_by_protocol_without_losing_order(monkeypatch, count, passage_length):
    from app.infrastructure.queue import model_client
    monkeypatch.setenv('MODEL_HOST_URL', 'http://synthetic.invalid')
    monkeypatch.setenv('MODEL_HOST_TOKEN', 'synthetic-token')
    monkeypatch.setenv('PROVIDER_POLICY_ENABLED', 'false')
    pairs = [[str(n), 'a' * passage_length] for n in range(count)]
    observed = []
    class HTTP:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, url, **kwargs):
            batch = kwargs['json']['pairs']
            assert 1 <= len(batch) <= 64
            assert sum(len(q) + len(p) for q, p in batch) <= 256000
            assert kwargs['allow_redirects'] is False and 0 < kwargs['timeout'] <= 300
            observed.extend(batch)
            return SimpleNamespace(raise_for_status=lambda: None,
                                   json=lambda: {'scores': [float(q) for q, _ in batch]})
    monkeypatch.setattr(model_client.requests, 'Session', HTTP)
    assert model_client.HostReranker()(pairs) == list(map(float, range(count)))
    assert observed == pairs


def test_oversized_late_pair_is_rejected_before_any_host_request(monkeypatch):
    from app.infrastructure.queue import model_client
    monkeypatch.setenv('MODEL_HOST_URL', 'http://synthetic.invalid')
    monkeypatch.setenv('MODEL_HOST_TOKEN', 'synthetic-token')
    sent = []
    class HTTP:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def post(self, *args, **kwargs):
            sent.append(kwargs)
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: {'scores': [1.0]})
    monkeypatch.setattr(model_client.requests, 'Session', HTTP)
    with pytest.raises(ValueError):
        model_client.HostReranker()([['q', 'valid']] * 64 + [['q', 'x' * 256000]])
    assert not sent
