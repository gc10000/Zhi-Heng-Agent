"""合成图片字节与 fake HTTP；不读取真实对象、配置或联网。"""
import hashlib
from io import BytesIO
from types import SimpleNamespace

from PIL import Image
import pytest


@pytest.fixture
def image_case():
    from scripts.verification.image_acceptance import verify_image_answer
    def png(color):
        output = BytesIO()
        Image.new('RGB', (3, 2), color).save(output, format='PNG')
        return output.getvalue()
    good, other = png('red'), png('blue')
    origin, bucket, prefix = 'http://127.0.0.1:19000', 'test-bucket', 'm0-test/review/'
    urls = [f'{origin}/{bucket}/{prefix}{name}.png' for name in ('topology', 'panel')]
    assets = [{'origin': origin, 'bucket': bucket, 'key': prefix + name + '.png',
               'sha256': hashlib.sha256(data).hexdigest()} for name, data in [('topology', good), ('panel', other)]]
    calls = []
    response = SimpleNamespace(status=200, data=good, headers={'Content-Type': 'image/png'})
    def fetch(url):
        calls.append(url)
        return response
    def run(answer=None, final_answer=None, images=None, **kw):
        answer = f'拓扑如下：![拓扑]({urls[0]})' if answer is None else answer
        return verify_image_answer(answer, answer if final_answer is None else final_answer,
                                   [urls[0]] if images is None else images, assets,
                                   assets[0]['sha256'], prefix, fetch, **kw)
    return SimpleNamespace(run=run, calls=calls, response=response, urls=urls,
                           assets=assets, good=good, other=other)


def test_correct_expected_object_is_accepted(image_case):
    result = image_case.run()
    assert all(result['checks'].values())


@pytest.mark.parametrize('scenario', ['wrong_image', 'html_200', 'cross_origin', 'unknown_object',
                                    'body_final_mismatch', 'final_missing_expected', 'wrong_bucket',
                                    'bad_hash', 'undecodable_image', 'redirect', 'mime_mismatch'])
def test_invalid_image_evidence_is_rejected(image_case, scenario):
    c = image_case
    args = {}
    if scenario == 'wrong_image':
        args = {'answer': f'![图]({c.urls[1]})', 'images': [c.urls[1]]}
        c.response.data = c.other
    elif scenario == 'html_200':
        c.response.data = b'<html>success</html>'
        c.response.headers['Content-Type'] = 'text/html'
    elif scenario == 'cross_origin':
        url = c.urls[0].replace('http://127.0.0.1:19000', 'https://example.invalid')
        args = {'answer': f'![图]({url})', 'images': [url]}
    elif scenario == 'unknown_object':
        url = c.urls[0].replace('topology.png', 'unknown.png')
        args = {'answer': f'![图]({url})', 'images': [url]}
    elif scenario == 'body_final_mismatch':
        args = {'final_answer': f'![图]({c.urls[1]})'}
    elif scenario == 'final_missing_expected':
        args = {'images': [c.urls[1]]}
    elif scenario == 'wrong_bucket':
        url = c.urls[0].replace('/test-bucket/', '/other-bucket/')
        args = {'answer': f'![图]({url})', 'images': [url]}
    elif scenario == 'bad_hash':
        c.response.data = c.other
    elif scenario == 'undecodable_image':
        c.response.data = b'not a png'
        c.assets[0]['sha256'] = hashlib.sha256(c.response.data).hexdigest()
    elif scenario == 'redirect':
        c.response.status = 302
        c.response.headers['Location'] = 'https://example.invalid/wrong.png'
    elif scenario == 'mime_mismatch':
        c.response.headers['Content-Type'] = 'image/jpeg'
    assert not all(c.run(**args)['checks'].values())
    if scenario in ('cross_origin', 'unknown_object', 'wrong_bucket'):
        assert c.calls == []


def test_final_can_include_additional_recorded_images(image_case):
    from scripts.verification.image_acceptance import verify_image_answer
    c = image_case
    def fetch(url):
        return SimpleNamespace(status=200, data=c.good if url == c.urls[0] else c.other,
                               headers={'Content-Type': 'image/png'})
    answer = f'![拓扑]({c.urls[0]})'
    result = verify_image_answer(answer, answer, c.urls, c.assets, c.assets[0]['sha256'], 'm0-test/review/', fetch)
    assert all(result['checks'].values())
    assert len(result['objects']) == 2


def test_redirects_are_disabled_in_http_adapter():
    from scripts.verification.image_acceptance import http_image_fetcher
    calls = []
    pool = SimpleNamespace(request=lambda *a, **kw: calls.append((a, kw)))
    http_image_fetcher(pool)('http://127.0.0.1:19000/test-bucket/m0-test/review/topology.png')
    assert calls[0][1] == {'redirect': False, 'retries': False}


@pytest.mark.parametrize('tail', ['?token=not-used', '#fragment', '/../topology.png', '%2e%2e/topology.png'])
def test_url_aliases_fail_before_download(image_case, tail):
    c = image_case
    url = c.urls[0] + tail
    assert not all(c.run(answer=f'![拓扑]({url})', images=[url])['checks'].values())
    assert not c.calls


def test_http_exception_is_safe_and_failed(image_case):
    from scripts.verification.image_acceptance import verify_image_answer
    c = image_case
    def fetch(url):
        raise TimeoutError('sensitive-marker')
    answer = f'![拓扑]({c.urls[0]})'
    result = verify_image_answer(answer, answer, [c.urls[0]], c.assets, c.assets[0]['sha256'], 'm0-test/review/', fetch)
    assert not all(result['checks'].values())
    assert result['objects'][0]['error_type'] == 'TimeoutError'
    assert 'sensitive-marker' not in str(result)


def test_legacy_image_jpg_mime_matches_decodable_jpeg_and_exact_hash(image_case):
    c = image_case
    output = BytesIO()
    Image.new('RGB', (3, 2), 'red').save(output, format='JPEG')
    c.response.data = output.getvalue()
    c.response.headers['Content-Type'] = 'image/jpg'
    c.assets[0]['sha256'] = hashlib.sha256(c.response.data).hexdigest()
    assert all(c.run()['checks'].values())


def test_legacy_jpg_mime_cannot_disguise_png(image_case):
    c = image_case
    c.response.headers['Content-Type'] = 'image/jpg'
    assert not all(c.run()['checks'].values())
