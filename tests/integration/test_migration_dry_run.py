"""三资料真实备份/独立恢复/迁移，全部独立测试源，原课程库不访问。"""
import json
import os
from io import BytesIO
from uuid import uuid4
from pathlib import Path
import pytest
from tests.integration.test_v2_index import real_embedder

pytestmark=pytest.mark.integration


def test_isolated_backup_recovery_and_resumable_three_document_migration(mongo_db,real_embedder,tmp_path):
    import fitz
    from PIL import Image
    from minio import Minio
    from pymilvus import MilvusClient,DataType
    from app.knowledge.migration import plan_migration,backup_selection,restore_sample,migrate_batch,read_object
    from app.knowledge.models import content_hash
    from app.knowledge.repository import KnowledgeRepository
    from app.knowledge.index import V2Index
    from app.knowledge.assets import AssetStore
    from app.knowledge.publishing import RevisionPublisher
    from tests.unit.test_tabular_sources import make_workbook
    from scripts.migrations.register_v1_documents import main as dry_run
    run=uuid4().hex;source=mongo_db['legacy_'+run];client=MilvusClient(uri=os.environ['MILVUS_URL'])
    objects=Minio(os.environ['MINIO_ENDPOINT'],access_key=os.environ['MINIO_ACCESS_KEY'],secret_key=os.environ['MINIO_SECRET_KEY'],secure=os.getenv('MINIO_SECURE','').lower()=='true')
    bucket=os.environ['MINIO_BUCKET_NAME'];prefix='m1-test/'+mongo_db.name+'/'+run+'/'
    legacy='m1_test_'+run+'_legacy';schema=client.create_schema(auto_id=False,enable_dynamic_field=True)
    schema.add_field('chunk_id',DataType.INT64,is_primary=True);schema.add_field('content',DataType.VARCHAR,max_length=65535)
    schema.add_field('dense_vector',DataType.FLOAT_VECTOR,dim=1024);schema.add_field('sparse_vector',DataType.SPARSE_FLOAT_VECTOR)
    params=client.prepare_index_params();params.add_index(field_name='dense_vector',index_type='AUTOINDEX',metric_type='IP');params.add_index(field_name='sparse_vector',index_type='SPARSE_INVERTED_INDEX',metric_type='IP')
    client.create_collection(collection_name=legacy,schema=schema,index_params=params,consistency_level='Strong')
    image=BytesIO();Image.new('RGB',(9,7),'blue').save(image,format='PNG');image_bytes=image.getvalue();image_key=prefix+'source/topology.png'
    objects.put_object(bucket,image_key,BytesIO(image_bytes),len(image_bytes),content_type='image/png')
    old_url='https://legacy.invalid/topology.png';records=[];texts=['网络拓扑 ![配图]('+old_url+')','长手册设备参数与故障处理','|参数|值|\n|速率|1000|']
    embeddings=real_embedder(texts);vectors=[]
    for i in range(3):
        if i<2:
            pdf=fitz.open()
            for page in range(1 if i==0 else 150):pdf.new_page().insert_text((72,72),'Independent sample '+str(page+1))
            raw=pdf.tobytes();pdf.close();name='同名.pdf'
        else:
            path=tmp_path/'sample.xlsx';make_workbook(path);raw=path.read_bytes();name='参数表.xlsx'
        key=prefix+'source/'+str(i);objects.put_object(bucket,key,BytesIO(raw),len(raw))
        records.append({'source_id':run+'-'+str(i),'name':name,'original_key':key,'original_sha256':content_hash(raw),'chunk_ids':[str(i+1)],
                        'images':[{'url':old_url,'object_key':image_key,'sha256':content_hash(image_bytes)}] if i==0 else []})
        source.insert_one(records[-1]|{'legacy_state':'available'})
        vectors.append({'chunk_id':i+1,'content':texts[i],'title':'样例'+str(i),'dense_vector':embeddings['dense'][i],
                        'sparse_vector':{int(k):float(v) for k,v in embeddings['sparse'][i].items()}})
    client.insert(collection_name=legacy,data=vectors);client.flush(legacy)
    before_mongo=source.count_documents({});before_vectors=client.get_collection_stats(legacy)
    manifest=tmp_path/'selection.json';manifest.write_text(json.dumps(records,ensure_ascii=False),encoding='utf-8')
    assert dry_run(['--dry-run','--manifest',str(manifest),'--owner-id','test','--kb-id',run,'--output',str(tmp_path/'dry-run.json')])==0
    assert source.count_documents({})==before_mongo and client.get_collection_stats(legacy)==before_vectors
    assert plan_migration(records,owner_id='test',kb_id=run)['same_names']==['同名.pdf']
    # 旧库无版本注册表，活动修订清单真实为空；保留为快照事实。
    backup_dir=Path('output/m1-migration')/run
    snapshot=backup_selection(records,mongo_collection=source,milvus=client,collection=legacy,objects=objects,bucket=bucket,directory=backup_dir,active_snapshot=[])
    repo=KnowledgeRepository(mongo_db,kb_id='target-'+run,owner_id='test');index=V2Index(client,'m1_test_'+run+'_v2');index.ensure_collection()
    assets=AssetStore(mongo_db,objects,bucket=bucket,prefix=prefix+'target/assets/')
    def write_original(did,digest,data):
        key=prefix+'target/originals/'+did+'/'+digest;objects.put_object(bucket,key,BytesIO(data),len(data));return key
    publisher=RevisionPublisher(repo,index,read_original=lambda r:read_object(objects,bucket,r['object_key']),asset_store=assets)
    kwargs=dict(directory=backup_dir,repo=repo,index=index,asset_store=assets,write_original=write_original,publisher=publisher,embedder=real_embedder)
    with pytest.raises(ValueError):migrate_batch(snapshot,None,**kwargs)
    assert repo.documents.count_documents(repo.scope)==0
    restore_db=mongo_db.client['m1_test_restore_'+run]
    recovery=restore_sample(snapshot,directory=backup_dir,mongo_collection=restore_db['legacy'],milvus=client,index='m1_test_'+run+'_restore',objects=objects,bucket=bucket,prefix=prefix+'restore/')
    assert recovery['verified'] and recovery['vectors']==3 and recovery['objects']==4
    actual_publish=publisher.publish
    def publish_then_interrupt(*args,**kw):
        actual_publish(*args,**kw)
        raise RuntimeError('合成发布后检查点前中断')
    publisher.publish=publish_then_interrupt
    with pytest.raises(RuntimeError):migrate_batch(snapshot,recovery,**kwargs)
    publisher.publish=actual_publish
    assert len(repo.get_active_revisions())==1
    completed=[]
    def interrupt(item):completed.append(item);raise RuntimeError('合成批次中断')
    with pytest.raises(RuntimeError):migrate_batch(snapshot,recovery,after_document=interrupt,**kwargs)
    assert len(completed)==1 and len(repo.get_active_revisions())==1
    assert completed[0]['asset_mapping'][old_url]
    result=migrate_batch(snapshot,recovery,**kwargs)
    assert len(result)==3 and len({r['document_id'] for r in result})==3
    kwargs['embedder']=lambda *a:pytest.fail('完成批次重试不应重编码')
    assert migrate_batch(snapshot,recovery,**kwargs)==result
    first=result[0];rows=index.revision_rows(repo,first['revision_id'])
    assert old_url not in rows[0]['text'] and 'asset://' in rows[0]['text'] and rows[0]['metadata']['source_refs'][0]['bbox'] is None
    assert source.count_documents({})==3
    (backup_dir/'migration-results.json').write_text(json.dumps({'result':result,'active_snapshot':repo.get_active_revisions(),'recovery':recovery},ensure_ascii=False,indent=2),encoding='utf-8')
    client.close()
