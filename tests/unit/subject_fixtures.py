"""两张合成键值表，含相同正文，测试数据不包含真实手册内容。"""
import json
from app.knowledge.repository import fingerprint
from app.knowledge.models import content_hash,stable_id
from app.answering.reviewed_subjects import row_chunk_identity,compile_binding
from app.knowledge.index import V2Index


def subject_case(monkeypatch, *, did='d',rid='r',owner='o',kb='k',pid='p'):
    import app.answering.reviewed_subjects as module
    raw=[];relations=[];rows=[]
    for subject,cells,page in [('合成扩展台甲',[['USB','连接外设']],13),
            ('合成扩展台乙',[['USB','连接外设'],['LAN','连接测试线'],['存储','插入测试卡']],14)]:
        ti=len(raw);title=dict(type='footer',text=subject,page_idx=12);raw.append(title)
        bi=len(raw);body='<table>'+''.join('<tr>'+''.join('<td>'+c+'</td>' for c in r)+'</tr>' for r in cells)+'</table>'
        block=dict(type='table',table_body=body,page_idx=page-1);raw.append(block)
        relations.append(dict(subject=subject,title=dict(cache_block_index=ti,cache_kind='footer',text_sha256=fingerprint(subject),
            cache_block_sha256=fingerprint(title),physical_page=13),table=dict(cache_block_index=bi,cache_block_sha256=fingerprint(block),
                body_utf8_sha256=content_hash(body.encode()),physical_page=page,row_count=len(cells),
                rows=[dict(row_index_zero_based=i,cells_sha256=fingerprint(r)) for i,r in enumerate(cells)]),
            assertion='table_rows_describe_named_accessory',no_model_compatibility_or_other_revision_claim=True))
        for i,r in enumerate(cells):
            identity=row_chunk_identity(rid,segment_offset=0,table_index=bi,row_index=i,cells=r,max_chars=2000)
            meta=dict(section_id=stable_id('section',rid,[identity['block_id'],['配件']]),heading_path=['配件'],product_ids=[pid],
                source_refs=[dict(document_id=did,revision_id=rid,kind='pdf',page=None)],content_kind='table',asset_ids=[])
            rows.append(dict(document_id=did,revision_id=rid,chunk_uid=identity['chunk_uid'],owner_id=owner,kb_id=kb,
                ordinal=len(rows),text=' | '.join(r),content_sha256=identity['content_sha256'],metadata=meta))
    original=b'synthetic original';cache=json.dumps(raw,ensure_ascii=False).encode()
    source=dict(document_id=did,revision_id=rid,original_sha256=content_hash(original),cache_sha256=content_hash(cache))
    manifest=json.dumps(dict(documents=[source])).encode()
    snapshot=dict(documents=[{**source,'chunks':[dict(chunk_uid=r['chunk_uid'],payload_sha256=fingerprint(V2Index.payload(r))) for r in rows]}])
    proof=dict(kind='independent_source_subject_table_review',source=source,frozen_manifest_file_sha256=content_hash(manifest),
        relations=relations,page_scope='physical_table_and_heading_pages_only_not_existing_row_page_override')
    proof['payload_sha256']=fingerprint(proof);data=json.dumps(proof,ensure_ascii=False).encode();review=b'synthetic independent review'
    def ref(path,b):return dict(commit='a'*40,path='docs/'+path,sha256=content_hash(b))
    proof_ref,review_ref=ref('proof.json',data),ref('review.md',review)
    store={proof_ref['sha256']:data,review_ref['sha256']:review}
    def evidence(value):
        ref=module.GitEvidence.model_validate(value)
        result=store.get(ref.sha256)
        if result is None or content_hash(result)!=ref.sha256:raise ValueError('合成Git证据hash不匹配')
        return result
    monkeypatch.setattr(module,'evidence_bytes',evidence)
    kwargs=dict(proof_ref=proof_ref,review_ref=review_ref,original_bytes=original,cache_bytes=cache,
        frozen_manifest_bytes=manifest,frozen_rows=rows,corpus_snapshot=snapshot,corpus_snapshot_sha256=fingerprint(snapshot))
    binding=compile_binding(**kwargs)
    return binding,rows,kwargs,proof


def as_doc(row):
    return row | dict(chunk_id=row['chunk_uid'],source='local',source_refs=row['metadata']['source_refs'],asset_ids=[])
