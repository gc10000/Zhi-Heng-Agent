"""从实际安装元数据和锁生成许可候选；不是完整法律审核或SPDX合规签署。"""
import argparse
import hashlib
from importlib import metadata
import json
from pathlib import Path
import re


def installed():
    rows=[]
    for d in metadata.distributions():
        files=[]
        for entry in d.files or []:
            if '.dist-info/' not in str(entry).replace('\\','/'):
                continue
            if re.match(r'^(licen[cs]e|copying|notice)(\.|$)',Path(entry).name,re.I):
                p=d.locate_file(entry)
                if p.is_file():
                    files.append(dict(name=Path(entry).name,sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
        license=d.metadata.get('License-Expression') or d.metadata.get('License') or 'unknown'
        # 有些历史包把整份LICENSE填入元数据；原文hash留证，摘要不复制任意长文本。
        if len(license)>240:license='原文随包；sha256:'+hashlib.sha256(license.encode()).hexdigest()
        rows.append(dict(name=d.metadata.get('Name'),version=d.version,declared_license=license,
            classifiers=[x for x in d.metadata.get_all('Classifier',[]) if x.startswith('License ::')],
            license_files=files))
    return sorted(rows,key=lambda x:((x['name'] or '').lower(),x['version'] or ''))


def inventory(root):
    root=Path(root)
    result=dict(kind='dependency_license_inventory_candidate_v1',legal_approval=False,
        limitations=['安装及锁的库存，不代表许可义务已履行','课程底座授权未核清','AGPL/SSPL及模型许可需发布审阅'],
        sources={},api_lock=[],frontend_lock={},installed_environment=installed())
    for name in ['uv.lock','deploy/api/requirements.lock','frontend/pnpm-lock.yaml','frontend/package.json']:
        data=(root/name).read_bytes();result['sources'][name]=hashlib.sha256(data).hexdigest()
    lock=(root/'deploy/api/requirements.lock').read_text('utf-8')
    result['api_lock']=[dict(name=a,version=b) for a,b in re.findall(r'^([\w.-]+)==([^\s\\]+)',lock,re.M)]
    package=json.loads((root/'frontend/package.json').read_text('utf-8'))
    result['frontend_lock']=dict(runtime=package['dependencies'],development=package['devDependencies'])
    index=root/'frontend/public/licenses/index.json'
    result['frontend_installed_licenses']=json.loads(index.read_text('utf-8')) if index.exists() else None
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',default=str(Path(__file__).resolve().parents[2]))
    p.add_argument('--output',required=True)
    a=p.parse_args()
    value=inventory(a.root)
    with Path(a.output).open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2)
