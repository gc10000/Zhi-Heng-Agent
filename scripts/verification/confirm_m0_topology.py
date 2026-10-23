"""只读核对已目视确认的 LA2608 图1与既有复制清单；不访问存储或修改解析缓存。"""
import hashlib
import json
from pathlib import Path
import shutil

import fitz
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]


def main():
    original = next((ROOT / 'doc').glob('*LA2608*.pdf'))
    excerpt = ROOT / 'output/e2e/H3C-LA2608-用户手册-联调节选.pdf'
    image = ROOT / ('output/20261021/ad96482a-6961-4850-b2d5-6b43c2a4b569/'
                    'H3C-LA2608-用户手册-联调节选/images/243f4d938c0c934ef7bea19e500c303b83762b45656092bcef57845096010a5e.jpg')
    evidence = ROOT / 'docs/development/evidence'
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    report = json.loads((evidence / 'M0-09-live-first.json').read_text(encoding='utf-8'))
    matches = [obj for obj in report['objects'] if obj['sha256'] == digest]
    assert len(matches) == 1 and matches[0]['bytes'] == image.stat().st_size
    with Image.open(image) as im:
        im.verify()
    with Image.open(image) as im:
        im.load()
        size = list(im.size)
    for source, page_idx, target in [(original, 3, 'M0-r2-topology-original-page.png'),
                                      (excerpt, 0, 'M0-r2-topology-page.png')]:
        with fitz.open(source) as doc:
            assert '3G/4G' in doc[page_idx].get_text()
            doc[page_idx].get_pixmap(matrix=fitz.Matrix(1.5, 1.5)).save(evidence / target)
    shutil.copy2(image, evidence / 'M0-r2-expected-topology.jpg')
    expectation = {
        'description': '图1 配置 LA2608 与无线控制器互通；LA2608→3G/4G→Internet→AC，左侧 Host A/B/C 经 WiFi 接入',
        'visual_confirmation': '2026-10-23 执行会话已目视原手册物理第4页/印刷第1页、节选物理第1页与缓存图，结构和标签一致',
        'sha256': digest, 'dimensions': size, 'bytes': image.stat().st_size,
        'copied_key': matches[0]['key'], 'object_prefix': report['scope']['object_prefix'],
        'origin_binding': '执行时由 MINIO_SECURE/MINIO_ENDPOINT/MINIO_BUCKET_NAME 绑定；不从答案推断允许 origin',
        'source_pdf': original.relative_to(ROOT).as_posix(),
        'source_pdf_sha256': hashlib.sha256(original.read_bytes()).hexdigest(), 'source_pdf_page': 4,
        'excerpt_pdf': excerpt.relative_to(ROOT).as_posix(),
        'excerpt_pdf_sha256': hashlib.sha256(excerpt.read_bytes()).hexdigest(), 'excerpt_pdf_page': 1,
        'source_cached_image': image.relative_to(ROOT).as_posix(),
        'evidence_image': 'docs/development/evidence/M0-r2-expected-topology.jpg',
        'evidence_source_page': 'docs/development/evidence/M0-r2-topology-original-page.png',
        'object_http_status': '本轮未请求；只读缓存哈希对照不能替代真实 HTTP 验收'}
    path = ROOT / 'evals/datasets/m0-image-expectation.json'
    path.write_text(json.dumps(expectation, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'status': 'matched_local_cache_to_copied_manifest', 'sha256': digest,
                      'dimensions': size, 'bytes': image.stat().st_size, 'http_verified': False}))


if __name__ == '__main__':
    main()
