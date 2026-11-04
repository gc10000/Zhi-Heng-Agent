"""恢复必须显式指定三个独立目标和已核清单hash，不覆盖或删除已有目标。"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.operations.connections import connections, environment
from scripts.operations.snapshot import Namespace, restore


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file')
    parser.add_argument('--input', required=True)
    parser.add_argument('--manifest-sha256', required=True)
    parser.add_argument('--target-database', required=True)
    parser.add_argument('--target-bucket', required=True)
    parser.add_argument('--target-collection', required=True)
    parser.add_argument('--prefix', required=True)
    args = parser.parse_args()
    environment(args.env_file)
    target = Namespace(args.target_database, args.target_bucket, args.target_collection, args.prefix)
    try:
        with connections() as clients:
            receipt = restore(args.input, target, *clients, expected_sha256=args.manifest_sha256)
        print(json.dumps(receipt))
    except Exception as error:
        print('恢复失败，异常类型=' + type(error).__name__ + '；保留现场，禁止自动重试或清理目标', file=sys.stderr)
        raise SystemExit(1)
