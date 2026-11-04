"""创建/查询独立预览；不读取真实.env，不启动模型，不覆盖已有目录或卷。"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
ROOT = Path(__file__).resolve().parents[2]


def compose(env_file, *args):
    command = ['docker', 'compose', '--env-file', str(Path(env_file).resolve()), '-f', str(ROOT / 'compose.delivery.yaml'), *args]
    subprocess.run(command, cwd=ROOT, check=True)


def ensure_minio(env_file):
    # 不覆写旧镜像tag；可复用已核固定源码构建，干净主机没有该镜像时才构建。
    tag = 'zhi-heng-minio:2025-10-15'
    for source in (tag, 'product-knowledge-minio:2025-10-15'):
        result = subprocess.run(['docker', 'image', 'inspect', source], capture_output=True, text=True)
        if result.returncode:
            continue
        image = json.loads(result.stdout)[0]
        if image['Config'].get('Labels', {}).get('org.opencontainers.image.revision') != '9e49d5e7a648f00e26f2246f4dc28e6b07f8c84a':
            raise ValueError('MinIO镜像来源身份不符，不覆盖或隐式替换')
        if source != tag:
            subprocess.run(['docker', 'tag', image['Id'], tag], check=True)
        print('复用固定源码MinIO镜像：' + image['Id'])
        return
    compose(env_file, 'build', 'minio')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('action', choices=['create', 'status', 'copy-password'])
    p.add_argument('--output', default='output/local-preview')
    p.add_argument('--env-file')
    p.add_argument('--no-build', action='store_true', help='仅复用已构建候选镜像，不能称为重新构建')
    args = p.parse_args()
    if args.action == 'create':
        from scripts.operations.prepare_preview import prepare
        info = prepare(ROOT / args.output)
        env_file = info['env_file']
        compose(env_file, 'config', '--quiet')
        if not args.no_build:
            compose(env_file, 'build', 'api', 'web')
        ensure_minio(env_file)
        compose(env_file, 'up', '-d', '--wait', '--wait-timeout', '360')
        compose(env_file, 'exec', '-T', 'api', 'python', '-m', 'scripts.operations.bootstrap_preview')
        print(json.dumps({'url': info['url'], 'username': 'preview_admin', 'env_file': env_file,
                          'generation': 'disabled', 'password': '仅保存在私有环境文件；copy-password可复制'}, ensure_ascii=False))
        return
    if not args.env_file:
        p.error('status/copy-password要求显式提供本轮--env-file')
    if args.action == 'status':
        compose(args.env_file, 'ps')
    else:
        if os.name != 'nt':
            p.error('自动剪贴板仅支持Windows；其他平台在本机私有环境文件取用，不写共享日志')
        from dotenv import dotenv_values
        values = dotenv_values(args.env_file)
        if values.get('M7_GENERATION_ENABLED') != 'false' or not values.get('M2_DB_NAME', '').startswith('m1_test_m4_'):
            p.error('只能复制隔离预览凭据')
        subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command', '$input | Set-Clipboard'],
                       input=values['M7_PREVIEW_PASSWORD'], text=True, check=True, capture_output=True)
        print('合成预览密码已复制到本机剪贴板；用户名preview_admin。请勿粘贴到共享日志。')


if __name__ == '__main__':
    main()
