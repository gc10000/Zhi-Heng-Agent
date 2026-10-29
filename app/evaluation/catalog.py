"""维护者预置的本机评测目录；HTTP调用只使用固定ID，不接受文件路径。"""
import json
from pathlib import Path, PurePosixPath

from .validate_dataset import file_sha, validate_dataset
from .runner import check_split


class EvaluationCatalog:
    def __init__(self, catalog_path):
        configured = Path(catalog_path)
        self.catalog_path = configured.resolve()
        self.root = self.catalog_path.parent.resolve()

    def _catalog(self):
        if not self.catalog_path.is_file():
            raise ValueError('未配置M6_EVALUATION_CATALOG')
        value = json.loads(self.catalog_path.read_text(encoding='utf-8'))
        if not isinstance(value, dict) or set(value) != {'datasets', 'configs'}:
            raise ValueError('评测目录结构无效')
        if not isinstance(value['datasets'], list) or not isinstance(value['configs'], list):
            raise ValueError('评测目录项必须为列表')
        # 正式派生入口最后原子发布；未完成目录没有entry，不参与解析。
        for entry in sorted((self.root / 'regression-versions').glob('*/entry.json')):
            generated = json.loads(self._file(entry.relative_to(self.root).as_posix()).read_text(encoding='utf-8'))
            if set(generated) != {'datasets', 'configs'}:
                raise ValueError('派生目录结构无效')
            for key in ('datasets', 'configs'):
                value[key].extend(generated[key])
        self._unique(value['datasets'], 'id', 'version')
        self._unique(value['configs'], 'id', 'version')
        return value

    @staticmethod
    def _unique(rows, *keys):
        seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('评测目录项无效')
            identity = tuple(row.get(key) for key in keys)
            if any(not isinstance(value, str) or not value.strip() for value in identity) or identity in seen:
                raise ValueError('评测目录身份缺失或重复')
            seen.add(identity)

    def _file(self, relative):
        if not isinstance(relative, str) or not relative or '\\' in relative or '%' in relative:
            raise ValueError('目录路径必须是规范相对路径')
        path = PurePosixPath(relative)
        if path.is_absolute() or any(part in {'', '.', '..'} or ':' in part for part in path.parts):
            raise ValueError('目录路径不能离开评测根目录')
        resolved = (self.root / Path(*path.parts)).resolve(strict=True)
        if not resolved.is_relative_to(self.root) or not resolved.is_file():
            raise ValueError('目录文件不在受控评测根目录内')
        return resolved

    @staticmethod
    def _load_config(path):
        import yaml
        value = yaml.safe_load(path.read_text(encoding='utf-8'))
        if not isinstance(value, dict):
            raise ValueError('评测配置必须为对象')
        return value

    def _dataset(self, item):
        dataset = self._file(item.get('dataset'))
        manifest = self._file(item.get('manifest'))
        frozen = json.loads(manifest.read_text(encoding='utf-8'))
        if frozen.get('dataset_sha256') != file_sha(dataset):
            raise ValueError('题集文件与冻结manifest指纹不一致')
        rows = validate_dataset(dataset, manifest=manifest, minimum=50)
        return dataset, manifest, rows, frozen

    def list_datasets(self, kb_id):
        catalog = self._catalog()
        configs = []
        for row in catalog['configs']:
            config = self._load_config(self._file(row.get('path')))
            configs.append((row, config))
        result = []
        for item in catalog['datasets']:
            allowed = item.get('kb_ids')
            if not isinstance(allowed, list) or kb_id not in allowed:
                continue
            dataset, manifest, rows, frozen = self._dataset(item)
            dataset_sha256, manifest_sha256 = file_sha(dataset), file_sha(manifest)
            compatible = []
            for definition, config in configs:
                # 只能执行冻结开发集。heldout无论如何不能从此工作台派发。
                if (config.get('dataset_sha256') == dataset_sha256 and
                        config.get('split_manifest_sha256') == manifest_sha256 and
                        config.get('split') == 'dev' and config.get('phase') == 'development' and
                        config.get('execution_mode') == 'real_query_runner' and
                        config.get('metric_schema_version') == 1):
                    try:
                        check_split(config, frozen)
                    except (ValueError, KeyError, OSError):
                        continue
                    compatible.append({'id': definition['id'], 'version': definition['version'],
                                       'strategy': config['strategy']})
            result.append({'id': item['id'], 'version': item['version'], 'kb_id': kb_id,
                           'dataset_sha256': dataset_sha256, 'manifest_sha256': manifest_sha256,
                           'question_count': len(rows), 'dev_count': sum(r['split'] == 'dev' for r in rows),
                           'review_eligible_count': sum(self._eligible(r) for r in rows if r['split'] == 'dev'),
                           'configs': compatible})
        return result

    @staticmethod
    def _eligible(question):
        from .datasets import is_label_eligible
        return is_label_eligible(question)

    def resolve(self, dataset_id, dataset_version, config_id, config_version, *, kb_id):
        catalog = self._catalog()
        dataset_row = next((r for r in catalog['datasets'] if r.get('id') == dataset_id and
                            r.get('version') == dataset_version and kb_id in r.get('kb_ids', [])), None)
        config_row = next((r for r in catalog['configs'] if r.get('id') == config_id and
                           r.get('version') == config_version), None)
        if dataset_row is None or config_row is None:
            raise ValueError('评测目录版本不存在或不在授权知识范围')
        dataset, manifest, rows, frozen = self._dataset(dataset_row)
        config_path = self._file(config_row.get('path'))
        config = self._load_config(config_path)
        check_split(config, frozen)
        if (config['dataset_sha256'] != file_sha(dataset) or
                config['split_manifest_sha256'] != file_sha(manifest) or
                config.get('split') != 'dev' or config.get('phase') != 'development' or
                config.get('execution_mode') != 'real_query_runner' or
                config.get('metric_schema_version') != 1):
            raise ValueError('评测配置与冻结开发题集不匹配')
        from .runner import select_questions
        selected = select_questions(rows, config)
        return {'dataset_path': dataset, 'manifest_path': manifest, 'config_path': config_path,
                'dataset_sha256': file_sha(dataset), 'manifest_sha256': file_sha(manifest),
                'config_sha256': file_sha(config_path), 'config': config,
                'selected_questions': len(selected), 'eligible_questions': sum(self._eligible(r) for r in selected)}
