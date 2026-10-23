"""真实Mongo共享缓存/限流与隔离MinIO原图，描述用fake明确非供应商验收。"""
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path
from uuid import uuid4
import os
import pytest

pytestmark=pytest.mark.integration


def test_mongo_cache_claim_and_shared_rate_reservation(mongo_db):
    from app.knowledge.assets import MongoSummaryCache
    from app.infrastructure.rate_limits import MongoRateStore
    key=str(uuid4());caches=[MongoSummaryCache(mongo_db) for _ in range(2)]
    with ThreadPoolExecutor(max_workers=4) as pool:
        claims=list(pool.map(lambda i:caches[i%2].claim(key,str(i)),range(8)))
    assert sum(claims)==1
    owner=caches[0].get(key)['owner']
    assert not caches[0].complete(key,'wrong','bad')
    assert caches[0].complete(key,owner,'description')
    assert not caches[1].claim(key,'again')
    stores=[MongoRateStore(mongo_db) for _ in range(2)];rate_key=str(uuid4())
    with ThreadPoolExecutor(max_workers=4) as pool:
        slots=list(pool.map(lambda i:stores[i%2].reserve(rate_key,100,2),range(8)))
    assert sorted(slots)==[100+2*i for i in range(8)]


def test_original_image_and_description_are_linked_in_isolated_objects(mongo_db,tmp_path):
    from minio import Minio
    from PIL import Image
    from types import SimpleNamespace
    from app.ingestion.models import ParsedImage,ParsedDocument
    from app.knowledge.models import SourceRef
    from app.knowledge.assets import AssetStore,MongoSummaryCache
    from app.ingestion.stages.images import ImageSummaryService,process_images
    data=BytesIO();Image.new('RGB',(8,6),'red').save(data,format='PNG')
    path=tmp_path/'image.png';path.write_bytes(data.getvalue())
    document_id=str(uuid4());revision_id=str(uuid4())
    parsed=ParsedDocument(document_id=document_id,revision_id=revision_id,original_sha256='a'*64,parser='test',parser_version='1',
        images=(ParsedImage(image_id=str(uuid4()),local_path=str(path),context='独立拓扑测试',source_refs=(SourceRef(document_id=document_id,revision_id=revision_id,kind='pdf',page=1),)),))
    client=Minio(os.environ['MINIO_ENDPOINT'],access_key=os.environ['MINIO_ACCESS_KEY'],secret_key=os.environ['MINIO_SECRET_KEY'],secure=os.getenv('MINIO_SECURE','').lower()=='true')
    store=AssetStore(mongo_db,client,bucket=os.environ['MINIO_BUCKET_NAME'],prefix='m1-test/'+mongo_db.name+'/')
    calls=[]
    service=ImageSummaryService(MongoSummaryCache(mongo_db),SimpleNamespace(acquire=lambda:None),lambda *a:calls.append(1) or '图片摘要')
    result,assets=process_images(parsed,store,service,model='fake-model',prompt_version='1')
    assert assets[0].description_status=='completed'
    item,original=store.read(assets[0].asset_id)
    assert original==data.getvalue() and item['description']=='图片摘要'
    assert result.blocks[-1].text=='' and result.blocks[-1].description=='图片摘要'
    assert result.blocks[-1].source_refs[0].kind=='image_description'
    process_images(parsed,store,service,model='fake-model',prompt_version='1')
    assert len(calls)==1
