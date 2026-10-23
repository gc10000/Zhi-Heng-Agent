"""新领域契约：身份不依赖名称/hash，精确定位不能凭空补齐。"""
import pytest
from pydantic import ValidationError


def test_same_name_and_hash_do_not_merge_business_documents():
    from app.knowledge.models import Document, Revision
    a = Document(kb_id='kb', owner_id='u', name='手册')
    b = Document(kb_id='kb', owner_id='u', name='手册')
    assert a.document_id != b.document_id
    x = Revision(document_id=a.document_id, kb_id='kb', owner_id='u', original_sha256='a'*64, object_key='a')
    y = Revision(document_id=b.document_id, kb_id='kb', owner_id='u', original_sha256='a'*64, object_key='b')
    assert x.revision_id != y.revision_id
    assert isinstance(x.revision_id, str)


def test_stable_ids_are_revision_scoped_and_unambiguous():
    from app.knowledge.models import stable_id
    assert stable_id('chunk', 'r', ['ab', 'c']) == stable_id('chunk', 'r', ['ab', 'c'])
    assert stable_id('chunk', 'r', ['ab', 'c']) != stable_id('chunk', 'r', ['a', 'bc'])
    assert stable_id('chunk', 'r', ['a']) != stable_id('chunk', 'r2', ['a'])


def test_unknown_location_stays_unknown_and_model_description_is_explicit():
    from app.knowledge.models import SourceRef
    ref = SourceRef(document_id='d', revision_id='r', kind='pdf')
    assert ref.page is None and ref.bbox is None
    assert ref.model_dump(mode='json')['kind'] == 'pdf'
    assert SourceRef(document_id='d', revision_id='r', kind='image_description', asset_id='a').asset_id == 'a'


@pytest.mark.parametrize('changes', [{'page': 0}, {'document_id': 123}, {'kind':'excel', 'page':1}, {'kind':'pdf','sheet':'s'}, {'bbox': [0,0,2,1]}])
def test_invalid_or_cross_format_location_is_rejected(changes):
    from app.knowledge.models import SourceRef
    with pytest.raises(ValidationError):
        SourceRef(**({'document_id':'d','revision_id':'r','kind':'pdf'} | changes))


def test_all_entities_serialize_ids_as_strings_and_are_immutable():
    from app.knowledge.models import KnowledgeBase, Document, Revision, Section, Chunk, Asset
    from app.products.models import Product
    entities = [KnowledgeBase(owner_id='u',name='kb'), Product(owner_id='u',model='LA2608'),
                Document(owner_id='u',kb_id='k',name='n'),
                Revision(owner_id='u',kb_id='k',document_id='d',original_sha256='b'*64,object_key='o'),
                Section(document_id='d',revision_id='r',section_id='s'),
                Chunk(document_id='d',revision_id='r',section_id='s',chunk_uid='c',text='x',ordinal=1),
                Asset(document_id='d',revision_id='r',asset_id='a',sha256='c'*64,object_key='o',media_type='image/png')]
    for entity in entities:
        assert all(v is None or isinstance(v,str) for k,v in entity.model_dump().items() if k.endswith('_id') or k=='chunk_uid')
        with pytest.raises(ValidationError):
            entity.document_id = 'changed'
