"""实际BGE稀疏键经JSON往返仍应全等，不放宽向量数值比较。"""
from copy import deepcopy
from bson import json_util
import pytest
from scripts.operations.snapshot import canonical, vector_dump


class Client:
    def __init__(self,sparse):self.rows=[dict(chunk_uid='c',sparse_vector=sparse,dense_vector=[.125,.25])]
    def query_iterator(self,**kwargs):
        rows=deepcopy(self.rows)
        class Iterator:
            def next(self):
                nonlocal rows
                result,rows=rows,[]
                return result
            def close(self):pass
        return Iterator()


def test_sparse_json_roundtrip_keeps_exact_values_and_order_identity():
    client=Client({6:.046966552734375,1036:.26123046875,12833:.2347412109375})
    restored=vector_dump(client,'c')
    saved=json_util.loads(canonical(client.rows))
    assert canonical(restored)==canonical(saved)
    assert all(type(k) is int for k in client.rows[0]['sparse_vector'])
    altered=deepcopy(saved);altered[0]['sparse_vector']['6']+=.0001
    assert canonical(restored)!=canonical(altered)


@pytest.mark.parametrize('sparse',[{6:.1,'6':.2},{True:.1},{'06':.1}])
def test_ambiguous_sparse_key_is_rejected(sparse):
    with pytest.raises(ValueError):vector_dump(Client(sparse),'c')
