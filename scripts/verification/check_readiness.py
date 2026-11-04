"""显式同源地址的只读探针，不请求模型。"""
import argparse
import json
import requests


def check(base):
    with requests.Session() as session:
        session.trust_env = False
        live = session.get(base.rstrip('/') + '/health/live', timeout=15)
        ready = session.get(base.rstrip('/') + '/health/ready', timeout=20)
        return {'live_status': live.status_code, 'ready_status': ready.status_code, 'checks': ready.json()}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', required=True)
    result = check(parser.parse_args().url)
    print(json.dumps(result, ensure_ascii=False))
    raise SystemExit(0 if result['live_status'] == result['ready_status'] == 200 else 1)
