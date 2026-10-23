"""M0 图片验收共享边界；请求由调用方显式注入，单元测试保持离线。"""
import re
import hashlib
from io import BytesIO
from urllib.parse import quote, urlsplit

from PIL import Image


def bind_assets(objects, origin, bucket, object_prefix):
    """由可信配置绑定准确 origin/bucket/key；不根据答案 URL 推断允许范围。"""
    parsed = urlsplit(origin)
    if (parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password
            or parsed.path or parsed.query or parsed.fragment or not bucket or '/' in bucket
            or not object_prefix.startswith('m0-test/')):
        raise ValueError('图片验收配置范围无效')
    assets = []
    for obj in objects:
        key = obj['key']
        if not key.startswith(object_prefix) or any(p in ('.', '..', '') for p in key.split('/')):
            raise ValueError('图片对象不在准确隔离范围')
        if not re.fullmatch(r'[0-9a-f]{64}', obj['sha256']):
            raise ValueError('图片对象缺少有效 SHA256')
        assets.append({**obj, 'origin': origin, 'bucket': bucket})
    return assets


def verify_image_answer(answer, final_answer, final_images, assets, expected_sha256, object_prefix, fetch):
    assets = [asset for asset in assets]
    # 重新校验调用方清单；准确 URL 逐字匹配，拒绝 userinfo、编码路径别名、query 与跨 origin。
    allowed = {}
    for asset in assets:
        bind_assets([asset], asset['origin'], asset['bucket'], object_prefix)
        url = asset['origin'] + '/' + quote(asset['bucket'], safe='') + '/' + quote(asset['key'], safe='/')
        if url in allowed:
            raise ValueError('图片对象清单包含重复 URL')
        allowed[url] = asset
    expected = {url for url, asset in allowed.items() if asset['sha256'] == expected_sha256}
    urls = set(re.findall(r'https?://[^\s)<>\]]+', answer))
    final_urls = set(final_images)
    checks = {'expected_object_recorded': len(expected) == 1,
              'body_final_text_equal': answer == final_answer,
              'body_urls_recorded': bool(urls) and urls <= allowed.keys(),
              'final_urls_recorded': bool(final_urls) and final_urls <= allowed.keys(),
              'expected_topology_in_body': len(expected) == 1 and expected <= urls,
              'expected_topology_in_final': len(expected) == 1 and expected <= final_urls,
              'body_final_images_correspond': bool(urls) and urls <= final_urls,
              'downloads_verified': False}
    result = {'checks': checks, 'objects': []}
    if not all(value for key, value in checks.items() if key != 'downloads_verified'):
        return result
    for url in sorted(urls | final_urls):
        asset = allowed[url]
        item = {'key': asset['key'], 'expected_sha256': asset['sha256'], 'verified': False}
        result['objects'].append(item)
        try:
            response = fetch(url)
            mime = response.headers.get('Content-Type', '').split(';')[0].strip().lower()
            item['http_status'] = response.status
            item['content_type'] = mime
            data = response.data
            item['actual_sha256'] = hashlib.sha256(data).hexdigest()
            if response.status != 200 or not mime.startswith('image/') or item['actual_sha256'] != asset['sha256']:
                continue
            with Image.open(BytesIO(data)) as im:
                actual_mime = Image.MIME.get(im.format)
                im.verify()
            with Image.open(BytesIO(data)) as im:
                im.load()
                item['dimensions'] = list(im.size)
            # 既有对象元数据使用 image/jpg；仅将该 JPEG 历史别名归一化，仍以实际格式校验。
            canonical_mime = 'image/jpeg' if mime == 'image/jpg' else mime
            item['decoded_content_type'] = actual_mime
            item['verified'] = actual_mime == canonical_mime and all(n > 0 for n in item['dimensions'])
        except Exception as exc:
            # 不回显异常正文，避免 HTTP 客户端将 URL/凭据写入证据。
            item['error_type'] = type(exc).__name__
    checks['downloads_verified'] = bool(result['objects']) and all(obj['verified'] for obj in result['objects'])
    return result


def http_image_fetcher(pool):
    """只请求校验器已允许的对象，禁止 HTTP 客户端自动跳转到未知站点。"""
    return lambda url: pool.request('GET', url, redirect=False, retries=False)
