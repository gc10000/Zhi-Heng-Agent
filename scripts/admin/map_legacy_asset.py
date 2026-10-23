"""按显式本地清单只读核验旧图，并登记受控ID；不改变源桶或策略。"""
import argparse
import asyncio
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))


async def run(args):
    from app.settings import Settings
    from app.main import open_resources
    from app.identity.models import Principal
    from app.knowledge.legacy_assets import map_legacy_image
    settings = Settings.load()
    manifest = json.loads(Path(args.manifest).read_text(encoding='utf-8'))
    required = {'document_id', 'revision_id', 'bucket', 'object_key', 'expected_sha256'}
    if set(manifest) != required or any(not isinstance(v, str) or not v for v in manifest.values()):
        raise ValueError('清单必须包含document_id/revision_id/bucket/object_key/expected_sha256五个非空字段。')
    async with open_resources(settings) as resources:
        user = Principal(user_id='local-administrator', username='本机维护', role='admin', kb_ids=(args.kb,))
        aid = await asyncio.to_thread(map_legacy_image, resources['knowledge'](), user, **manifest)
        print('旧图核验并映射成功，asset_id=' + aid)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--kb', required=True)
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except Exception as exc:
        print('映射失败，异常类型=' + type(exc).__name__, file=sys.stderr)
        raise SystemExit(1)
