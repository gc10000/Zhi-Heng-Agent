"""反馈题集的不可变派生；入口最后发布，半写文件可按相同身份恢复。"""
from copy import deepcopy
import hashlib
import json
import os
from uuid import uuid4

from .datasets import is_label_eligible, serialize_dataset
from .validate_dataset import fingerprint, validate_dataset


def immutable_file(path, content):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / ('.p-' + uuid4().hex[:12])
    try:
        with temporary.open('xb') as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != content:
                raise ValueError('不可变题集文件冲突') from None
    finally:
        temporary.unlink(missing_ok=True)


def json_bytes(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode('utf-8')


def derive_version(catalog, parent, question, *, dataset_id, parent_version, kb_id):
    if question['split'] != 'dev' or not is_label_eligible(question):
        raise ValueError('只允许已审dev题派生反馈版本')
    rows = validate_dataset(parent['dataset_path'], manifest=parent['manifest_path'])
    old = next((r for r in rows if r['id'] == question['id']), None)
    if old and (old['split'] != 'dev' or old['group_id'] != question['group_id']):
        raise ValueError('反馈不得改变已有题目族或接触heldout')
    if any(r['split'] != 'dev' and r['group_id'] == question['group_id'] for r in rows):
        raise ValueError('反馈题目族不能跨入heldout')
    if old == question:
        raise ValueError('未变题目应直接绑定原冻结版本')
    rows = [question if r['id'] == question['id'] else r for r in rows]
    if old is None:
        rows.append(question)
    frozen = json.loads(parent['manifest_path'].read_text(encoding='utf-8'))
    digest = fingerprint([dataset_id, parent_version, parent['dataset_sha256'], parent['manifest_sha256'],
                          parent['config_sha256'], question])
    version = 'fb-' + digest[:40]
    # Windows宿主路径预算：目录用128bit短名，完整256bit身份仍在entry/config及不可变内容中校验。
    version_root = catalog.root / 'regression-versions'
    version_root.mkdir(parents=True,exist_ok=True)
    version_root = version_root.resolve(strict=True)
    if not version_root.is_relative_to(catalog.root):
        raise ValueError('派生目录越界')
    directory = version_root / digest[:32]
    directory.mkdir(exist_ok=True)
    if not directory.resolve(strict=True).is_relative_to(version_root):
        raise ValueError('派生目录越界')
    raw = serialize_dataset(rows)
    frozen.update(version=version, parent_version=parent_version,
        parent_dataset_sha256=parent['dataset_sha256'], parent_manifest_sha256=parent['manifest_sha256'],
        dataset_sha256=hashlib.sha256(raw).hexdigest(),
        rows=[dict(id=r['id'], split=r['split'], group_id=r['group_id'], sha256=fingerprint(r)) for r in rows])
    frozen['revision_changes'] = [dict(question_id=question['id'],previous_question_sha256=fingerprint(old) if old else None,
        current_question_sha256=fingerprint(question),reason='已确认反馈的独立标签审核；详见不可变来源绑定')]
    if old is None and 'evaluation_cohorts' in frozen:
        frozen['evaluation_cohorts']['fresh_dev_ids'].append(question['id'])
        frozen['evaluation_cohorts']['fresh_dev_ids'].sort()
    immutable_file(directory/'questions.jsonl', raw)
    immutable_file(directory/'manifest.json', json_bytes(frozen))
    validate_dataset(directory/'questions.jsonl', manifest=directory/'manifest.json')
    config = deepcopy(parent['config'])
    config.update(dataset_sha256=frozen['dataset_sha256'],
                  split_manifest_sha256=hashlib.sha256(json_bytes(frozen)).hexdigest())
    # 派生版本完整dev范围，不继承父配置的受影响题子集。
    config.pop('question_ids', None)
    immutable_file(directory/'config.json', json_bytes(config))
    prefix = directory.relative_to(catalog.root).as_posix()
    entry = dict(datasets=[dict(id=dataset_id, version=version, dataset=prefix+'/questions.jsonl',
        manifest=prefix+'/manifest.json', kb_ids=[kb_id])],
        configs=[dict(id='reg-'+digest, version=version, path=prefix+'/config.json')])
    # 可见性提交点；只接受完整且经校验的文件，旧catalog及父文件均不改。
    immutable_file(directory/'entry.json', json_bytes(entry))
    return dict(dataset_id=dataset_id, dataset_version=version, config_id='reg-'+digest, config_version=version)
