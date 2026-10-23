"""独立v2双路索引；不删除或重建旧集合，所有读写携带归属/修订范围。"""
import math
import re
from app.knowledge.models import content_hash
from app.knowledge.repository import ConflictError,fingerprint
from app.retrieval.filters import scoped_filter


class V2Index:
    def __init__(self,client,collection_name,*,dense_dim=1024):
        if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]{0,254}',collection_name):raise ValueError('非法集合名')
        if not (collection_name.endswith('_v2') or collection_name.startswith('m1_test_')):raise ValueError('只允许显式v2或隔离测试集合')
        self.client,self.collection,self.dense_dim=client,collection_name,dense_dim

    def ensure_collection(self):
        from pymilvus import DataType
        if not self.client.has_collection(self.collection):
            schema=self.client.create_schema(auto_id=False,enable_dynamic_field=False)
            for name,length in [('chunk_uid',128),('owner_id',128),('kb_id',128),('document_id',128),('revision_id',128),('text',65535),('content_sha256',64)]:
                schema.add_field(name,DataType.VARCHAR,max_length=length,is_primary=name=='chunk_uid')
            schema.add_field('ordinal',DataType.INT32)
            schema.add_field('metadata',DataType.JSON)
            schema.add_field('dense_vector',DataType.FLOAT_VECTOR,dim=self.dense_dim)
            schema.add_field('sparse_vector',DataType.SPARSE_FLOAT_VECTOR)
            params=self.client.prepare_index_params()
            params.add_index(field_name='dense_vector',index_type='AUTOINDEX',metric_type='IP')
            params.add_index(field_name='sparse_vector',index_type='SPARSE_INVERTED_INDEX',metric_type='IP')
            self.client.create_collection(collection_name=self.collection,schema=schema,index_params=params,consistency_level='Strong')
        description=self.client.describe_collection(self.collection)
        fields={f['name']:f for f in description['fields']}
        if not {'chunk_uid','owner_id','kb_id','revision_id','document_id','ordinal','text','metadata','content_sha256','dense_vector','sparse_vector'}<=fields.keys():
            raise ValueError('已有v2集合字段不兼容，拒绝覆盖')
        if int(fields['ordinal']['type'])!=int(DataType.INT32) or int(fields['dense_vector']['params']['dim'])!=self.dense_dim:
            raise ValueError('已有v2序号/向量维度不兼容')
        self.client.load_collection(self.collection)

    def revision_rows(self,repo,revision_id,*,vectors=False):
        revision=repo.get_revision(revision_id)
        fields=['chunk_uid','owner_id','kb_id','document_id','revision_id','ordinal','text','metadata','content_sha256']
        if vectors:fields+=['dense_vector','sparse_vector']
        iterator=self.client.query_iterator(collection_name=self.collection,filter=scoped_filter(owner_id=repo.owner_id,kb_id=repo.kb_id,
            revision_ids=[revision_id],document_id=revision['document_id']),output_fields=fields,batch_size=256,consistency_level='Strong')
        rows=[]
        try:
            while True:
                batch=iterator.next()
                if not batch:break
                rows.extend(batch)
        finally:iterator.close()
        return rows

    @staticmethod
    def payload(row):
        """可复核的业务载荷，不包含驱动浮点序列化差异。"""
        return {k:row[k] for k in ('chunk_uid','owner_id','kb_id','document_id','revision_id','ordinal','text','metadata','content_sha256')}

    @staticmethod
    def validate_vectors(dense,sparse,dimension):
        if len(dense)!=dimension or not all(math.isfinite(float(v)) for v in dense) or not any(float(v) for v in dense):
            raise ValueError('稠密向量为空/维度错误/非有限值')
        if not sparse or any(int(k)<0 or not math.isfinite(float(v)) for k,v in sparse.items()):
            raise ValueError('learned sparse向量缺失或非法')

    def write_revision(self,repo,revision_id,chunks,*,attempt,embedder):
        revision=repo.get_revision(revision_id)
        if revision['attempt']!=attempt or revision['status']!='staged':raise ConflictError('过期attempt或非staged修订不能索引')
        if not chunks or len({c.chunk_uid for c in chunks})!=len(chunks):raise ValueError('切片必须非空且ID唯一')
        if any(c.document_id!=revision['document_id'] or c.revision_id!=revision_id for c in chunks):raise ValueError('索引切片跨资料/修订')
        hashes={c.chunk_uid:content_hash(c.text.encode()) for c in chunks}
        payloads={c.chunk_uid:{'chunk_uid':c.chunk_uid,'owner_id':repo.owner_id,'kb_id':repo.kb_id,'document_id':c.document_id,
            'revision_id':revision_id,'ordinal':c.ordinal,'text':c.text,
            'metadata':c.model_dump(mode='json',exclude={'chunk_uid','document_id','revision_id','ordinal','text'}),'content_sha256':hashes[c.chunk_uid]} for c in chunks}
        payload_hashes={uid:fingerprint(value) for uid,value in payloads.items()}
        manifest={'count':len(chunks),'hashes':hashes,'payload_hashes':payload_hashes,'collection':self.collection,'manifest_sha256':fingerprint(payload_hashes)}
        prior=self.revision_rows(repo,revision_id)
        if any(row['chunk_uid'] not in payload_hashes or fingerprint(self.payload(row))!=payload_hashes[row['chunk_uid']] for row in prior):
            raise ConflictError('同修订已有不同切片，须创建新修订')
        if set(hashes)=={r['chunk_uid'] for r in prior}:
            repo.save_stage(revision_id,attempt=attempt,stage='indexed',manifest=manifest)
            return manifest
        embeddings=embedder([c.text for c in chunks])
        if len(embeddings['dense'])!=len(chunks) or len(embeddings['sparse'])!=len(chunks):raise ValueError('向量数量不符')
        rows=[]
        for c,dense,sparse in zip(chunks,embeddings['dense'],embeddings['sparse']):
            sparse={int(k):float(v) for k,v in sparse.items()};self.validate_vectors(dense,sparse,self.dense_dim)
            rows.append(payloads[c.chunk_uid]|{'dense_vector':dense,'sparse_vector':sparse})
        # 分批写入便于中断重试；活动指针未切换，失败不会影响旧版。
        for start in range(0,len(rows),64):
            current=repo.get_revision(revision_id)
            if current['attempt']!=attempt or current['status']!='staged':raise ConflictError('索引写入attempt已过期')
            self.client.upsert(collection_name=self.collection,data=rows[start:start+64])
        self.client.flush(self.collection)
        repo.save_stage(revision_id,attempt=attempt,stage='indexed',manifest=manifest)
        return manifest

    def search(self,repo,text,*,embedder,revision_snapshot=None,product_ids=(),limit=5):
        from pymilvus import AnnSearchRequest,WeightedRanker
        snapshot=repo.get_active_revisions() if revision_snapshot is None else revision_snapshot
        ids=[r['active_revision_id'] for r in snapshot]
        if not ids:return []
        # 显式快照仍须逐项复核当前调用范围，历史引用可按授权回看。
        for rid in ids:repo.get_revision(rid)
        embedding=embedder([text]);dense=embedding['dense'][0];sparse=embedding['sparse'][0]
        self.validate_vectors(dense,sparse,self.dense_dim)
        expr=scoped_filter(owner_id=repo.owner_id,kb_id=repo.kb_id,revision_ids=ids,product_ids=product_ids)
        requests=[AnnSearchRequest(data=[dense],anns_field='dense_vector',param={'metric_type':'IP'},limit=limit,expr=expr),
                  AnnSearchRequest(data=[sparse],anns_field='sparse_vector',param={'metric_type':'IP'},limit=limit,expr=expr)]
        return self.client.hybrid_search(collection_name=self.collection,reqs=requests,ranker=WeightedRanker(0.5,0.5),limit=limit,
                                        output_fields=['chunk_uid','text','document_id','revision_id','ordinal','metadata'],consistency_level='Strong')[0]
