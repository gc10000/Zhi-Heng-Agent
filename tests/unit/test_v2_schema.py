"""已有集合必须验证完整字段类型，不能将同名字段当兼容。"""
from types import SimpleNamespace
import pytest


@pytest.mark.parametrize('changed',['metadata','chunk_uid','sparse_vector'])
def test_incompatible_existing_schema_is_rejected(changed):
    from pymilvus import DataType
    from app.knowledge.index import V2Index
    fields=[{'name':k,'type':DataType.VARCHAR,'params':{'max_length':65535},'is_primary':k=='chunk_uid'} for k in
            ('chunk_uid','owner_id','kb_id','document_id','revision_id','text','content_sha256')]
    fields += [{'name':'ordinal','type':DataType.INT32,'params':{}},{'name':'metadata','type':DataType.JSON,'params':{}},
               {'name':'dense_vector','type':DataType.FLOAT_VECTOR,'params':{'dim':1024}},
               {'name':'sparse_vector','type':DataType.SPARSE_FLOAT_VECTOR,'params':{}}]
    for f in fields:
        if f['name']==changed:f['type']=DataType.INT64
    client=SimpleNamespace(has_collection=lambda *a:True,describe_collection=lambda *a:{'fields':fields},load_collection=lambda *a:None)
    with pytest.raises(ValueError):V2Index(client,'test_v2').ensure_collection()


def test_revision_readback_has_stable_source_order():
    from app.knowledge.index import V2Index
    class Iterator:
        def __init__(self):self.batches=[[{'chunk_uid':'later','ordinal':300},{'chunk_uid':'first','ordinal':0}],[]]
        def next(self):return self.batches.pop(0)
        def close(self):pass
    index=V2Index(SimpleNamespace(query_iterator=lambda **kw:Iterator()),'test_v2')
    repo=SimpleNamespace(get_revision=lambda rid:{'document_id':'d'},owner_id='o',kb_id='k')
    assert [row['chunk_uid'] for row in index.revision_rows(repo,'r')]==['first','later']
