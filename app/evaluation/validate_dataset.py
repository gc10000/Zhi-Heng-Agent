"""本机JSONL题集的来源、冻结指纹及分组划分校验；不触发模型或服务。"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(strict=True, min_length=1)]
Digest = Annotated[str, Field(pattern=r'^[0-9a-f]{64}$', strict=True)]


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def file_sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class Evidence(Strict):
    document_sha256: Digest
    page: int = Field(ge=1)
    quote: Text
    asset_sha256: Digest | None = None


class Message(Strict):
    role: Literal['user', 'assistant']
    text: Text


class Expected(Strict):
    behavior: Literal['answer', 'clarify', 'insufficient', 'partial', 'compare']
    key_points: list[Text]
    forbidden_claims: list[Text]


class Annotation(Strict):
    method: Literal['source_checked_assistant_draft', 'human_reviewed']
    status: Literal['draft', 'reviewed']
    reviewer: Text | None = None

    @model_validator(mode='after')
    def human_status(self):
        if self.status == 'reviewed' and (self.method != 'human_reviewed' or not self.reviewer):
            raise ValueError('人工复核状态须明确真实复核人，辅助草稿不能冒充通过')
        return self


class Question(Strict):
    id: Text
    category: Literal['parameter', 'configuration', 'troubleshooting', 'ambiguity', 'diagram', 'cross_model', 'unanswerable']
    group_id: Text
    split: Literal['dev', 'heldout']
    question: Text
    product_names: list[Text]
    history: list[Message]
    expected: Expected
    allowed_evidence: list[list[Evidence]]
    source_scope: list[Digest] = Field(min_length=1)
    annotation: Annotation

    @model_validator(mode='after')
    def support(self):
        if not self.question.strip() or not self.expected.key_points:
            raise ValueError('问题及验收关键点不能为空')
        if self.expected.behavior in {'answer', 'partial', 'compare'} and not self.allowed_evidence:
            raise ValueError('有依据回答必须标注允许证据')
        if any(not group for group in self.allowed_evidence):
            raise ValueError('每个必需证据组至少有一个可替代的正确来源')
        if any(e.document_sha256 not in self.source_scope for g in self.allowed_evidence for e in g):
            raise ValueError('允许证据超出题目来源范围')
        return self


def validate_dataset(path, *, manifest=None, minimum=50):
    path = Path(path)
    if path.stat().st_size > 32_000_000:
        raise ValueError('题集超过32MB，须显式分版本整理')
    raw = [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    if len(raw) < minimum:
        raise ValueError('题集数量不足')
    groups, ids, requests = {}, set(), set()
    for row in raw:
        Question.model_validate(row)
        if row['id'] in ids:
            raise ValueError('题目ID重复')
        ids.add(row['id'])
        request = fingerprint([''.join(row['question'].split()).casefold(), row['product_names'], row['history']])
        if request in requests:
            raise ValueError('相同问题/主体/历史重复，不能跨组制造独立样本')
        requests.add(request)
        if groups.setdefault(row['group_id'], row['split']) != row['split']:
            raise ValueError('同一问题族跨dev/heldout，存在泄漏')
    if manifest is not None:
        frozen = json.loads(Path(manifest).read_text(encoding='utf-8'))
        if frozen['dataset_sha256'] != file_sha(path):
            raise ValueError('题集字节指纹与冻结版本不一致')
        declared = frozen['rows']
        expected = [{'id': r['id'], 'split': r['split'], 'group_id': r['group_id'], 'sha256': fingerprint(r)} for r in raw]
        if declared != expected:
            raise ValueError('逐题指纹或划分与冻结版本不一致')
        sources = {s['sha256']: s['pages'] for s in frozen['sources']}
        if len(sources) != len(frozen['sources']):
            raise ValueError('来源清单重复')
        for row in raw:
            if not set(row['source_scope']) <= sources.keys():
                raise ValueError('来源未登记到冻结清单')
            for group in row['allowed_evidence']:
                if any(e['page'] > sources[e['document_sha256']] for e in group):
                    raise ValueError('证据物理页码超出原件')
    return raw


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('dataset', type=Path)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    manifest = args.manifest or args.dataset.with_name('split-manifest.json')
    try:
        rows = validate_dataset(args.dataset, manifest=manifest)
    except (ValueError, KeyError, OSError):
        parser.exit(1, '题集校验失败：请核对JSONL字段、来源清单、冻结指纹与分组划分；不输出题目或私有路径。\n')
    print(json.dumps({'passed': True, 'questions': len(rows), 'splits': dict(Counter(r['split'] for r in rows)),
                      'categories': dict(Counter(r['category'] for r in rows)),
                      'annotation_status': dict(Counter(r['annotation']['status'] for r in rows))}, ensure_ascii=False))


if __name__ == '__main__':
    main()
