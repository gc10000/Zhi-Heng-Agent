"""只读备份显式隔离小样，清单最后落盘，输出hash而非密钥。"""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.operations.connections import connections, environment, namespace
from scripts.operations.snapshot import backup


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file')
    parser.add_argument('--output', required=True)
    parser.add_argument('--source-commit', required=True)
    args = parser.parse_args()
    environment(args.env_file)
    try:
        with connections() as clients:
            receipt = backup(args.output, namespace(), *clients, source_commit=args.source_commit)
        print(json.dumps(receipt))
    except Exception as error:
        print('备份失败，异常类型=' + type(error).__name__, file=sys.stderr)
        raise SystemExit(1)
