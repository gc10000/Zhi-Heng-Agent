from types import SimpleNamespace
import pytest


@pytest.fixture
def llm_options(monkeypatch):
    from app.lm import lm_utils
    calls = []
    config = SimpleNamespace(api_key='synthetic-key', base_url='https://api.example.invalid/v1',
                             llm_model='synthetic-model', llm_temperature=0,
                             provider='auto', enable_thinking=False)
    monkeypatch.setattr(lm_utils, 'lm_config', config)
    monkeypatch.setattr(lm_utils, '_llm_client_cache', {})
    def construct(**kwargs):
        calls.append(kwargs)
        return SimpleNamespace(options=kwargs)
    monkeypatch.setattr(lm_utils, 'ChatOpenAI', construct)
    return lm_utils, config, calls


def test_temperature_zero_is_preserved(llm_options):
    lm, config, calls = llm_options
    lm.get_llm_client()
    assert calls[-1]['temperature'] == 0


def test_generic_compatible_provider_omits_private_field(llm_options):
    lm, config, calls = llm_options
    lm.get_llm_client(json_mode=True)
    assert not calls[-1].get('extra_body')
    assert calls[-1]['model_kwargs']['response_format'] == {'type': 'json_object'}


def test_dashscope_capability_and_cache_scope(llm_options):
    lm, config, calls = llm_options
    first = lm.get_llm_client()
    assert lm.get_llm_client() is first
    config.provider = 'dashscope'
    second = lm.get_llm_client()
    assert second is not first
    assert calls[-1]['extra_body'] == {'enable_thinking': False}
    config.enable_thinking = True
    assert lm.get_llm_client().options['extra_body'] == {'enable_thinking': True}


def test_auto_provider_checks_hostname_not_substring(llm_options):
    lm, config, calls = llm_options
    config.base_url = 'https://dashscope.aliyuncs.com/compatible-mode/v1'
    assert lm.get_llm_client().options['extra_body'] == {'enable_thinking': False}
    config.base_url = 'https://dashscope.aliyuncs.com.evil.invalid/v1'
    assert not lm.get_llm_client().options.get('extra_body')


@pytest.mark.parametrize('field,name', [('api_key', 'OPENAI_API_KEY'), ('base_url', 'OPENAI_BASE_URL')])
def test_missing_config_only_names_variable(llm_options, field, name):
    lm, config, calls = llm_options
    setattr(config, field, '')
    with pytest.raises(ValueError, match=name):
        lm.get_llm_client()
    assert calls == []


def test_prompt_images_and_provider_errors_are_not_logged(monkeypatch, answer_node, session):
    from app.core.logger import logger
    node = answer_node.module
    sid, _ = session
    logs = []
    sink = logger.add(lambda msg: logs.append(str(msg)), level='DEBUG')
    marker = 'SYNTHETIC-PRIVATE-KNOWLEDGE'
    signed = 'https://example.invalid/img.png?X-Amz-Signature=SYNTHETIC-SECRET'
    try:
        state = {'session_id': sid, 'reranked_docs': [{'text': f'{marker} ![图]({signed})'}]}
        prompt = node.step_2_construct_prompt(state)
        node._extract_images_from_docs(state['reranked_docs'])
        def fail():
            raise ValueError(marker + signed)
        monkeypatch.setattr(node, 'get_llm_client', fail)
        with pytest.raises(Exception):
            node.step_3_generate_response(state, prompt)
        logger.complete()
    finally:
        logger.remove(sink)
    output = ''.join(logs)
    assert marker not in output
    assert signed not in output
    assert 'SYNTHETIC-SECRET' not in output
    assert str(len(prompt)) in output


def test_parser_download_does_not_log_signed_url(monkeypatch, tmp_path):
    from app.import_process.agent.nodes import node_pdf_to_md as parser
    from app.core.logger import logger
    signed = 'https://example.invalid/zip?X-Amz-Signature=SYNTHETIC-PARSER-SECRET'
    logs = []
    sink = logger.add(lambda msg: logs.append(str(msg)), level='DEBUG')
    monkeypatch.setattr(parser.requests, 'get', lambda *a, **kw: SimpleNamespace(status_code=503))
    try:
        with pytest.raises(RuntimeError, match='503'):
            parser.step_3_download_and_extract(signed, tmp_path, '合成文件')
        logger.complete()
    finally:
        logger.remove(sink)
    assert signed not in ''.join(logs)
    assert 'SYNTHETIC-PARSER-SECRET' not in ''.join(logs)
