"""离线反例仅验证发布校验器；真实存储/指针测试另列。"""
from types import SimpleNamespace
import pytest
from app.knowledge.index import V2Index
from app.knowledge.models import Chunk,SourceRef,content_hash
from app.knowledge.repository import fingerprint
from app.knowledge.publishing import RevisionPublisher


def fixture(*,refs=True):
    c=Chunk(chunk_uid='c',document_id='d',revision_id='r',section_id='s',ordinal=0,text='原文',
            source_refs=(SourceRef(document_id='d',revision_id='r',kind='pdf',page=1),) if refs else ())
    row={'chunk_uid':'c','owner_id':'o','kb_id':'k','document_id':'d','revision_id':'r','ordinal':0,'text':c.text,
         'content_sha256':content_hash(c.text.encode()),'metadata':c.model_dump(mode='json',exclude={'chunk_uid','document_id','revision_id','ordinal','text'}),
         'dense_vector':[1.,0.],'sparse_vector':{1:1.}}
    hashes={'c':fingerprint(V2Index.payload(row))}
    revision={'revision_id':'r','document_id':'d','attempt':1,'original_sha256':content_hash(b'original'),
              'stages':{'indexed':{'collection':'test_v2','count':1,'payload_hashes':hashes,'manifest_sha256':fingerprint(hashes)}}}
    index=SimpleNamespace(collection='test_v2',dense_dim=2,revision_rows=lambda *a,**kw:[row],payload=V2Index.payload,validate_vectors=V2Index.validate_vectors)
    publisher=RevisionPublisher(None,index,read_original=lambda r:b'original')
    return publisher,revision,row


def test_missing_provenance_cannot_be_published():
    publisher,revision,_=fixture(refs=False)
    with pytest.raises(ValueError,match='来源'):publisher.inspect(revision)


@pytest.mark.parametrize('bad',[[0.,0.],[float('nan'),1.],[1.]])
def test_invalid_vectors_block_validation(bad):
    publisher,revision,row=fixture();row['dense_vector']=bad
    with pytest.raises(ValueError):publisher.inspect(revision)


def test_picture_reference_requires_asset_validator():
    publisher,revision,row=fixture()
    row['metadata']['asset_ids']=['missing']
    hashes={'c':fingerprint(V2Index.payload(row))}
    revision['stages']['indexed'].update(payload_hashes=hashes,manifest_sha256=fingerprint(hashes))
    with pytest.raises(ValueError,match='图片资产'):publisher.inspect(revision)


@pytest.mark.parametrize('bad',['pending','foreign','decode','hash'])
def test_picture_failure_blocks_validation(bad):
    from io import BytesIO
    from PIL import Image
    publisher,revision,row=fixture()
    row['metadata']['asset_ids']=['a']
    hashes={'c':fingerprint(V2Index.payload(row))}
    revision['stages']['indexed'].update(payload_hashes=hashes,manifest_sha256=fingerprint(hashes))
    data=BytesIO();Image.new('RGB',(4,4)).save(data,format='PNG');raw=data.getvalue()
    item={'document_id':'d','revision_id':'r','description_status':'completed','sha256':content_hash(raw)}
    if bad=='pending':item['description_status']='pending'
    if bad=='foreign':item['revision_id']='other'
    if bad=='decode':raw=b'not an image';item['sha256']=content_hash(raw)
    if bad=='hash':item['sha256']='a'*64
    publisher.assets=SimpleNamespace(read=lambda aid:(item,raw))
    with pytest.raises(ValueError if bad!='decode' else OSError):publisher.inspect(revision)
