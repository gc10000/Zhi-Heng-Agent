"""显式旧身份清单迁移；备份恢复门禁在任何目标注册之前执行。"""
import json
import math
import re
from io import BytesIO
from pathlib import Path
from app.knowledge.models import Chunk,SourceRef,content_hash,stable_id
from app.knowledge.repository import fingerprint,ConflictError
from app.ingestion.models import ParsedImage


def plan_migration(records,*,owner_id,kb_id):
    missing=[];collisions=[];mapping=[];seen={};names={};chunk_owners={}
    for row in records:
        sid=row.get('source_id')
        absent=[k for k in ('source_id','name','original_key','original_sha256','chunk_ids') if not row.get(k)]
        if not isinstance(sid,str):absent.append('source_id必须为字符串')
        if not re.fullmatch('[a-f0-9]{64}',str(row.get('original_sha256',''))):absent.append('original_sha256必须为SHA256')
        if not isinstance(row.get('chunk_ids'),list) or any(not str(cid).isdigit() for cid in row.get('chunk_ids',[])):absent.append('chunk_ids必须为旧INT64主键列表')
        if absent:missing.append({'source_id':sid,'fields':absent});continue
        if sid in seen:
            collisions.append({'source_id':sid,'reason':'重复源身份'});continue
        seen[sid]=row;names[row['name']]=names.get(row['name'],0)+1
        for cid in row['chunk_ids']:
            if str(cid) in chunk_owners:collisions.append({'chunk_id':str(cid),'reason':'切片归属重复'})
            chunk_owners[str(cid)]=sid
        did=stable_id('document',kb_id,[owner_id,'legacy:'+sid])
        mapping.append({'source_id':sid,'document_id':did,'name':row['name'],'chunk_count':len(row['chunk_ids'])})
    return {'ready':bool(mapping) and not missing and not collisions,'writes':0,'mapping':mapping,
            'missing':missing,'collisions':collisions,'same_names':[k for k,n in names.items() if n>1]}


def require_recovery(snapshot,report):
    if not report or not report.get('verified') or report.get('snapshot_sha256')!=snapshot['snapshot_sha256']:
        raise ValueError('缺少与本快照匹配的独立恢复核验，禁止迁移写入')


def read_object(client,bucket,key):
    response=client.get_object(bucket,key)
    try:return response.read()
    finally:response.close();response.release_conn()


def safe_blob(directory,name):
    path=(Path(directory)/name).resolve()
    if not path.is_relative_to(Path(directory).resolve()):raise ValueError('快照对象路径越界')
    return path


def normalized(value):
    """Milvus numpy标量转为可校验JSON，稀疏key统一字符串。"""
    if isinstance(value,dict):return {str(k):normalized(v) for k,v in value.items()}
    if isinstance(value,(list,tuple)):return [normalized(v) for v in value]
    if hasattr(value,'item'):return normalized(value.item())
    if isinstance(value,float) and not math.isfinite(value):raise ValueError('快照含非有限向量')
    return value


def backup_selection(records,*,mongo_collection,milvus,collection,objects,bucket,directory,active_snapshot):
    from bson import json_util
    directory=Path(directory);directory.mkdir(parents=True,exist_ok=True)
    snapshot={'version':1,'records':records,'mongo':[],'vectors':[],'objects':[],'active_snapshot':active_snapshot,
              'source':{'db':mongo_collection.database.name,'mongo_collection':mongo_collection.name,'milvus_collection':collection,'bucket':bucket}}
    ids=[];keys={}
    for row in records:
        found=mongo_collection.find_one({'source_id':row['source_id']})
        if found is None:raise ValueError('源Mongo资料缺失')
        snapshot['mongo'].append(json_util.dumps(found,sort_keys=True))
        ids.extend(int(cid) for cid in row['chunk_ids']);keys[row['original_key']]=row['original_sha256']
        for image in row.get('images',[]):keys[image['object_key']]=image['sha256']
    if len(set(ids))!=len(ids):raise ValueError('源切片重复')
    rows=milvus.get(collection_name=collection,ids=ids,output_fields=['*'],consistency_level='Strong')
    if {int(r['chunk_id']) for r in rows}!=set(ids):raise ValueError('源向量切片缺失')
    snapshot['vectors']=sorted([normalized(r) for r in rows],key=lambda r:int(r['chunk_id']))
    for key,digest in keys.items():
        data=read_object(objects,bucket,key)
        if content_hash(data)!=digest:raise ValueError('备份原件hash不符')
        name='blobs/'+digest;target=safe_blob(directory,name);target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        snapshot['objects'].append({'source_key':key,'blob':name,'sha256':digest})
    snapshot['snapshot_sha256']=fingerprint(snapshot)
    (directory/'snapshot.json').write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
    return snapshot


def verify_snapshot(snapshot,directory):
    if fingerprint({k:v for k,v in snapshot.items() if k!='snapshot_sha256'})!=snapshot['snapshot_sha256']:raise ValueError('快照清单hash不符')
    for obj in snapshot['objects']:
        if content_hash(safe_blob(directory,obj['blob']).read_bytes())!=obj['sha256']:raise ValueError('备份文件hash不符')


def restore_sample(snapshot,*,directory,mongo_collection,milvus,index,objects,bucket,prefix):
    """恢复完整已选小批到独立目标；不调用删除/覆盖已有记录。"""
    from bson import json_util
    from pymilvus import DataType
    verify_snapshot(snapshot,directory)
    source=snapshot['source']
    if (mongo_collection.database.name==source['db'] or index==source['milvus_collection'] or not prefix.startswith('m1-test/')
        or not mongo_collection.database.name.startswith('m1_test_') or not index.startswith('m1_test_')):
        raise ValueError('恢复目标必须与源隔离，并使用m1-test对象前缀')
    if mongo_collection.count_documents({}) or objects is None:raise ValueError('恢复目标非空或对象客户端缺失')
    # 使用与旧schema兼容的显式主键恢复，所有字段/原向量原样保留。
    client=milvus
    if client.has_collection(index):raise ValueError('恢复集合已存在，拒绝覆盖')
    description=client.describe_collection(source['milvus_collection'])
    schema=client.create_schema(auto_id=False,enable_dynamic_field=True)
    for field in description['fields']:
        params=dict(field.get('params',{}));params.pop('auto_id',None)
        schema.add_field(field['name'],DataType(field['type']),is_primary=field.get('is_primary',False),**params)
    indexes=client.prepare_index_params()
    indexes.add_index(field_name='dense_vector',index_type='AUTOINDEX',metric_type='IP')
    indexes.add_index(field_name='sparse_vector',index_type='SPARSE_INVERTED_INDEX',metric_type='IP')
    client.create_collection(collection_name=index,schema=schema,index_params=indexes,consistency_level='Strong')
    docs=[json_util.loads(value) for value in snapshot['mongo']]
    mongo_collection.insert_many(docs)
    rows=[dict(row,sparse_vector={int(k):v for k,v in row['sparse_vector'].items()}) for row in snapshot['vectors']]
    client.insert(collection_name=index,data=rows);client.flush(index)
    mapping={}
    for obj in snapshot['objects']:
        data=safe_blob(directory,obj['blob']).read_bytes();key=prefix.rstrip('/')+'/'+obj['sha256']
        objects.put_object(bucket,key,BytesIO(data),len(data));mapping[obj['source_key']]=key
        if content_hash(read_object(objects,bucket,key))!=obj['sha256']:raise ValueError('恢复对象hash不符')
    restored=client.get(collection_name=index,ids=[int(r['chunk_id']) for r in rows],output_fields=['*'],consistency_level='Strong')
    restored=sorted([normalized(r) for r in restored],key=lambda r:int(r['chunk_id']))
    if fingerprint(restored)!=fingerprint(snapshot['vectors']):raise ValueError('恢复向量/引用不符')
    if sorted(json_util.dumps(d,sort_keys=True) for d in mongo_collection.find({}))!=sorted(snapshot['mongo']):raise ValueError('恢复Mongo不符')
    report={'verified':True,'snapshot_sha256':snapshot['snapshot_sha256'],'documents':len(docs),'vectors':len(rows),'objects':len(mapping),
            'active_snapshot':snapshot['active_snapshot'],'restored_object_mapping':mapping,'restore_db':mongo_collection.database.name,'restore_collection':index}
    (Path(directory)/'recovery-report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return report


def migrate_batch(snapshot,recovery,*,directory,repo,index,asset_store,write_original,publisher,embedder,batch_size=1,after_document=None):
    require_recovery(snapshot,recovery);verify_snapshot(snapshot,directory)
    if not repo.db.name.startswith('m1_test_') or not index.collection.startswith('m1_test_') or not asset_store.prefix.startswith('m1-test/'):
        raise ValueError('当前授权仅允许隔离小样迁移')
    report=plan_migration(snapshot['records'],owner_id=repo.owner_id,kb_id=repo.kb_id)
    if not report['ready']:raise ValueError('迁移清单有缺失或碰撞')
    if not 1<=len(snapshot['records'])<=3 or not 1<=batch_size<=3:raise ValueError('当前仅允许1至3份隔离小样')
    checkpoint=repo.db['knowledge_migrations'];batch_id=snapshot['snapshot_sha256']
    result=[];row_map={str(r['chunk_id']):r for r in snapshot['vectors']};blob_map={o['source_key']:o for o in snapshot['objects']}
    for start in range(0,len(snapshot['records']),batch_size):
        for source in snapshot['records'][start:start+batch_size]:
            key={'_id':fingerprint([repo.scope,batch_id,source['source_id']])}
            saved=checkpoint.find_one(key)
            if saved and saved.get('status')=='completed':result.append(saved['result']);continue
            d=repo.register_document('legacy:'+source['source_id'],name=source['name'],purpose=source.get('purpose','unknown'),product_ids=source.get('product_ids',()))
            original=safe_blob(directory,blob_map[source['original_key']]['blob']).read_bytes()
            object_key=write_original(d.document_id,source['original_sha256'],original)
            r=repo.create_revision(d.document_id,'legacy:'+batch_id,original_sha256=source['original_sha256'],object_key=object_key,parser_version='legacy-selected-v1')
            current=repo.get_revision(r.revision_id)
            assets={image['url']:stable_id('legacy-image',r.revision_id,[image['url']]) for image in source.get('images',[])}
            if current['status']=='staged':
                attempt=repo.claim_attempt(r.revision_id,expected_attempt=current['attempt'])
                for image in source.get('images',[]):
                    aid=stable_id('legacy-image',r.revision_id,[image['url']]);ref=SourceRef(document_id=d.document_id,revision_id=r.revision_id,kind='legacy',asset_id=aid)
                    data=safe_blob(directory,blob_map[image['object_key']]['blob']).read_bytes()
                    asset=asset_store.put_image(ParsedImage(image_id=aid,local_path='',source_refs=(ref,)),document_id=d.document_id,revision_id=r.revision_id,
                        data=data,status='not_required',description=None)
                chunks=[]
                for ordinal,cid in enumerate(source['chunk_ids']):
                    old=row_map[str(cid)];text=old.get('content',old.get('text',''))
                    for url,aid in assets.items():text=text.replace(url,'asset://'+aid)
                    refs=(SourceRef(document_id=d.document_id,revision_id=r.revision_id,kind='legacy'),)
                    chunks.append(Chunk(chunk_uid=stable_id('legacy-chunk',r.revision_id,[str(cid)]),document_id=d.document_id,revision_id=r.revision_id,section_id=stable_id('legacy-section',r.revision_id,[str(cid)]),
                        ordinal=ordinal,text=text,heading_path=tuple(x for x in [old.get('parent_title'),old.get('title')] if x),source_refs=refs,asset_ids=tuple(assets.values()),product_ids=d.product_ids))
                index.write_revision(repo,r.revision_id,chunks,attempt=attempt,embedder=embedder)
                publisher.validate(r.revision_id,attempt=attempt)
            document=repo.get_document(d.document_id)
            if document['active_revision_id']!=r.revision_id:publisher.publish(r.revision_id,expected_active=document['active_revision_id'])
            else:publisher.reconcile(d.document_id)
            item={'source_id':source['source_id'],'document_id':d.document_id,'revision_id':r.revision_id,'asset_mapping':assets}
            checkpoint.update_one(key,{'$set':{'status':'completed','result':item,'snapshot_sha256':batch_id}},upsert=True)
            result.append(item)
            if after_document:after_document(item)
    return result
