"""已封存表格归属的旁挂消费。只认来源坐标和冻结成员，不按词语猜对象。"""
import json
import re
import subprocess
from pathlib import Path
from typing import Literal
from functools import lru_cache

from pydantic import BaseModel, ConfigDict, Field
from app.knowledge.models import content_hash, stable_id
from app.knowledge.repository import fingerprint

SHA = r'^[a-f0-9]{64}$'


class GitEvidence(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    commit: str = Field(pattern=r'^[a-f0-9]{40}$')
    path: str = Field(min_length=1, max_length=300)
    sha256: str = Field(pattern=SHA)


@lru_cache(maxsize=64)
def _git_bytes(commit, path, sha256):
    # 不执行shell、不读取工作树中的同名可变文件，不接受任意Git revision表达式。
    if not re.fullmatch(r'[a-f0-9]{40}', commit) or not path.startswith('docs/') or any(
            p in {'', '.', '..'} for p in path.split('/')) or '\\' in path or ':' in path:
        raise ValueError('受审证据Git来源非法')
    root = Path(__file__).resolve().parents[2]
    result = subprocess.run(['git', 'show', f'{commit}:{path}'], cwd=root, capture_output=True, timeout=10)
    if result.returncode or content_hash(result.stdout) != sha256:
        raise ValueError('受审证据Git内容或hash不匹配')
    return result.stdout


def evidence_bytes(value):
    ref = GitEvidence.model_validate(value)
    return _git_bytes(ref.commit, ref.path, ref.sha256)


class SubjectMember(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    table_index: int = Field(ge=0)
    row_index: int = Field(ge=0)
    chunk_uid: str = Field(min_length=1)
    content_sha256: str = Field(pattern=SHA)
    section_id: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    metadata_sha256: str = Field(pattern=SHA)
    frozen_payload_sha256: str = Field(pattern=SHA)


class ReviewedSubjects(BaseModel):
    model_config = ConfigDict(extra='forbid', frozen=True)
    enabled: Literal[True] = True
    function_version: Literal['reviewed_table_subjects_v1'] = 'reviewed_table_subjects_v1'
    proof: GitEvidence
    review: GitEvidence
    proof_payload_sha256: str = Field(pattern=SHA)
    frozen_manifest_file_sha256: str = Field(pattern=SHA)
    corpus_snapshot_sha256: str = Field(pattern=SHA)
    document_id: str = Field(min_length=1)
    revision_id: str = Field(min_length=1)
    original_sha256: str = Field(pattern=SHA)
    cache_sha256: str = Field(pattern=SHA)
    segment_offset: int = Field(default=0, ge=0)
    max_chars: int = Field(default=2000, ge=1, le=2000)
    members: list[SubjectMember] = Field(min_length=1, max_length=100)


def checked_proof(value):
    policy = ReviewedSubjects.model_validate(value)
    evidence_bytes(policy.review)
    proof = json.loads(evidence_bytes(policy.proof))
    raw = {k: v for k, v in proof.items() if k != 'payload_sha256'}
    if (proof.get('kind') != 'independent_source_subject_table_review' or
            fingerprint(raw) != proof.get('payload_sha256') or
            proof['payload_sha256'] != policy.proof_payload_sha256 or
            proof.get('source') != {k: getattr(policy, k) for k in
                ('document_id', 'revision_id', 'original_sha256', 'cache_sha256')} or
            proof.get('frozen_manifest_file_sha256') != policy.frozen_manifest_file_sha256 or
            proof.get('page_scope') != 'physical_table_and_heading_pages_only_not_existing_row_page_override'):
        raise ValueError('受审对象证明身份不符')
    members = {(m.table_index, m.row_index): m for m in policy.members}
    expected = {(t['table']['cache_block_index'], row['row_index_zero_based'])
                for t in proof['relations'] for row in t['table']['rows']}
    if len(members) != len(policy.members) or set(members) != expected or len({m.chunk_uid for m in policy.members}) != len(members):
        raise ValueError('受审表格成员缺失、重复或冲突')
    # chunk UID派生依赖表block坐标，不因相同正文串绑到另一张表。
    for t in proof['relations']:
        table = t['table']
        if t.get('assertion') != 'table_rows_describe_named_accessory' or not t.get('no_model_compatibility_or_other_revision_claim'):
            raise ValueError('受审对象断言超出范围')
        for row in table['rows']:
            member = members[table['cache_block_index'], row['row_index_zero_based']]
            bid = stable_id('block', policy.revision_id, [policy.segment_offset, member.table_index])
            bid = stable_id('table-row', policy.revision_id, [bid, member.row_index])
            uid = stable_id('chunk', policy.revision_id, [bid, 0, member.content_sha256, policy.max_chars])
            if member.chunk_uid != uid:
                raise ValueError('受审成员不是冻结表行的真实切片身份')
    return policy, proof


def row_chunk_identity(revision, *, segment_offset, table_index, row_index, cells, max_chars):
    text = ' | '.join(cells)
    if len(text) + 1 >= max_chars:
        raise ValueError('旁挂消费仅接受未拆分的键值表行')
    bid = stable_id('block', revision, [segment_offset, table_index])
    bid = stable_id('table-row', revision, [bid, row_index])
    sha = content_hash(text.encode())
    return dict(chunk_uid=stable_id('chunk', revision, [bid, 0, sha, max_chars]), content_sha256=sha, block_id=bid)


def compile_binding(*, proof_ref, review_ref, original_bytes, cache_bytes, frozen_manifest_bytes,
                    frozen_rows, corpus_snapshot, corpus_snapshot_sha256, max_chars=2000, segment_offset=0):
    """本机受控准备：校验原件/缓存/审阅/全量冻结载荷，不写数据库或修订。"""
    from app.ingestion.stages.chunking import _TableReader
    from app.knowledge.index import V2Index
    proof = json.loads(evidence_bytes(proof_ref))
    source = proof['source']
    if (content_hash(original_bytes) != source['original_sha256'] or content_hash(cache_bytes) != source['cache_sha256'] or
            content_hash(frozen_manifest_bytes) != proof['frozen_manifest_file_sha256']):
        raise ValueError('原件、解析缓存或冻结清单漂移')
    manifest = json.loads(frozen_manifest_bytes)
    if not any(all(d.get(k) == source[k] for k in source) for d in manifest['documents']):
        raise ValueError('来源不在已审冻结清单')
    rows = {r['chunk_uid']: r for r in frozen_rows}
    if len(rows) != len(frozen_rows):raise ValueError('冻结切片重复')
    if fingerprint(corpus_snapshot)!=corpus_snapshot_sha256:raise ValueError('冻结快照hash漂移')
    snapshot_doc=next((d for d in corpus_snapshot.get('documents',[]) if d['document_id']==source['document_id'] and
        d['revision_id']==source['revision_id'] and d['original_sha256']==source['original_sha256']),None)
    frozen_hashes={c['chunk_uid']:c['payload_sha256'] for c in snapshot_doc.get('chunks',[])} if snapshot_doc else {}
    raw = json.loads(cache_bytes);members = []
    for relation in proof['relations']:
        title, table = relation['title'], relation['table']
        tb, block = raw[title['cache_block_index']], raw[table['cache_block_index']]
        if (fingerprint(tb) != title['cache_block_sha256'] or fingerprint(tb['text']) != title['text_sha256'] or
                tb['type'] != title['cache_kind'] or tb['page_idx'] + 1 != title['physical_page'] or
                fingerprint(block) != table['cache_block_sha256'] or block['type'] != 'table' or
                block['page_idx'] + 1 != table['physical_page'] or
                content_hash(block['table_body'].encode()) != table['body_utf8_sha256']):
            raise ValueError('受审标题、表体或物理页来源漂移')
        parser = _TableReader();parser.feed(block['table_body'])
        if parser.header_rows or len(parser.rows) != table['row_count'] or any(len(row) != 2 for row in parser.rows):
            raise ValueError('旁挂消费只支持已审无显式表头的完整键值行')
        for row in table['rows']:
            i = row['row_index_zero_based'];cells = parser.rows[i]
            if fingerprint(list(cells)) != row['cells_sha256']:raise ValueError('受审行成员漂移')
            identity = row_chunk_identity(source['revision_id'], segment_offset=segment_offset,
                table_index=table['cache_block_index'], row_index=i, cells=cells, max_chars=max_chars)
            frozen = rows.get(identity['chunk_uid'])
            if (not frozen or frozen['document_id'] != source['document_id'] or frozen['revision_id'] != source['revision_id'] or
                    content_hash(frozen['text'].encode()) != identity['content_sha256'] or frozen['content_sha256'] != identity['content_sha256'] or
                    frozen_hashes.get(frozen['chunk_uid'])!=fingerprint(V2Index.payload(frozen)) or
                    frozen['metadata']['section_id'] != stable_id('section', source['revision_id'],
                        [identity['block_id'], frozen['metadata']['heading_path']])):
                raise ValueError('缺少精确冻结表行成员，拒绝按正文或最近标题匹配')
            members.append(dict(table_index=table['cache_block_index'],row_index=i,chunk_uid=frozen['chunk_uid'],
                content_sha256=identity['content_sha256'],section_id=frozen['metadata']['section_id'],ordinal=frozen['ordinal'],
                metadata_sha256=fingerprint(frozen['metadata']),frozen_payload_sha256=fingerprint(V2Index.payload(frozen))))
    policy = ReviewedSubjects(proof=proof_ref,review=review_ref,proof_payload_sha256=proof['payload_sha256'],
        frozen_manifest_file_sha256=proof['frozen_manifest_file_sha256'],corpus_snapshot_sha256=corpus_snapshot_sha256,
        **source,members=members,max_chars=max_chars,segment_offset=segment_offset)
    checked_proof(policy)
    return policy


def authorize_members(value, rows, *, owner_id, kb_id):
    from app.knowledge.index import V2Index
    policy, _ = checked_proof(value)
    current = {r['chunk_uid']: r for r in rows}
    if len(current)!=len(rows):raise ValueError('受审授权载荷存在重复切片')
    for m in policy.members:
        row = current.get(m.chunk_uid)
        if (not row or row.get('owner_id') != owner_id or row.get('kb_id') != kb_id or
                row.get('document_id') != policy.document_id or row.get('revision_id') != policy.revision_id or
                fingerprint(V2Index.payload(row)) != m.frozen_payload_sha256):
            raise ValueError('受审对象成员不属于当前授权冻结载荷')


def attach_subject(doc, value):
    policy, proof = checked_proof(value)
    uid = doc.get('chunk_uid', doc.get('chunk_id'))
    member = next((m for m in policy.members if m.chunk_uid == uid), None)
    if member is None:return None  # 未绑定行不猜对象；文档产品不是配件主体。
    meta = doc.get('metadata') or {}
    if (doc.get('document_id') != policy.document_id or doc.get('revision_id') != policy.revision_id or
            content_hash(doc['text'].encode()) != member.content_sha256 or doc.get('ordinal') != member.ordinal or
            fingerprint(meta) != member.metadata_sha256 or meta.get('section_id')!=member.section_id or
            doc.get('source_refs',meta.get('source_refs'))!=meta.get('source_refs')):
        raise ValueError('受审对象正文、切片或出处漂移')
    relation = next(t for t in proof['relations'] if t['table']['cache_block_index'] == member.table_index)
    return dict(subject=relation['subject'],kind='reviewed_accessory_table_member',
        title_physical_page=relation['title']['physical_page'],table_physical_page=relation['table']['physical_page'],
        page_scope='table_only_not_row_location',proof_payload_sha256=policy.proof_payload_sha256,
        proof_git_commit=policy.proof.commit,table_block_index=member.table_index,row_index=member.row_index)
