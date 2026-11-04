"""候选镜像/前端的有限凭据与源码身份检查；只读，不宣称全面安全审计。"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tarfile


def inspect(image):
    return json.loads(subprocess.check_output(['docker', 'image', 'inspect', image], text=True))[0]


def audit(env_file, output):
    from dotenv import dotenv_values
    values = dotenv_values(env_file)
    # 仅本轮合成凭据参与匹配，不读真实.env或private-identity。
    assert values['M7_GENERATION_ENABLED'] == 'false' and values['M2_DB_NAME'].startswith('m1_test_m4_')
    secrets = [values[k].encode() for k in ('MINIO_SECRET_KEY', 'M7_PREVIEW_PASSWORD')]
    result = {'passed': False, 'images': {}, 'scope': '候选文件、镜像默认环境与本轮合成秘密；非全面漏洞或法律审计'}
    for name, image, path in [('api', 'zhi-heng-api:m7-r1', '/workspace'), ('web', 'zhi-heng-web:m7-r1', '/usr/share/nginx/html')]:
        metadata = inspect(image)
        for assignment in metadata['Config']['Env']:
            key, _, value = assignment.partition('=')
            if any(part in key for part in ('SECRET', 'PASSWORD', 'API_KEY', 'TOKEN')):
                assert not value, '镜像默认环境包含非空秘密变量'
        command = ['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'tar', image, '-C', path, '-cf', '-', '.']
        archive = subprocess.check_output(command, timeout=60)
        hashes = {}
        with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
            for item in tar:
                if not item.isfile(): continue
                entry = Path(item.name.removeprefix('./')).as_posix()
                assert not any(part in {'.env', '.git', 'output', 'evals', '.venv', 'private-identity'} for part in Path(entry).parts)
                raw = tar.extractfile(item).read()
                assert not any(secret in raw for secret in secrets), '合成秘密进入镜像文件'
                hashes[entry] = hashlib.sha256(raw).hexdigest()
                if name == 'api':
                    assert not entry.lower().endswith(('.pdf', '.safetensors', '.log'))
                    local = Path(entry)
                    assert local.is_file() and hashlib.sha256(local.read_bytes()).hexdigest() == hashes[entry], 'API镜像源码与当前工作树不一致'
        if name == 'web':
            assert 'licenses/index.json' in hashes and 'licenses/NOTICE.md' in hashes
        result['images'][name] = {'id': metadata['Id'], 'files': len(hashes), 'file_manifest_sha256': hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest(),
                                  'synthetic_credentials_absent': True}
    versions = subprocess.check_output(['docker', 'run', '--rm', '--network', 'none', '--entrypoint', 'python', 'zhi-heng-api:m7-r1', '-c',
        'import importlib.metadata as m,json;print(json.dumps({d.metadata["Name"]:d.version for d in m.distributions()},sort_keys=True))'], text=True)
    deps = json.loads(versions)
    assert not any(k.lower() in {'torch', 'flagembedding'} for k in deps)
    result['api_versions'] = deps
    result['passed'] = True
    Path(output).open('x', encoding='utf-8').write(json.dumps(result, ensure_ascii=False, indent=2))
    return {'passed': True, 'images': result['images'], 'api_has_no_torch': True}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--env-file', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(audit(args.env_file, args.output)))
