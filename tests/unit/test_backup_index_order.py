"""复合索引键必须在排序JSON中保留原顺序。"""
from bson import json_util


def test_compound_index_order_survives_canonical_backup():
    from scripts.operations.snapshot import mongo_dump, canonical
    class Collection:
        def find(self): return self
        def limit(self, n): return []
        def options(self): return {}
        def list_indexes(self): return [{'name': 'owner_id_1_conversation_id_1', 'key': {'owner_id': 1, 'conversation_id': 1}}]
    class DB:
        def list_collection_names(self): return ['conversations']
        def __getitem__(self, key): return Collection()
    saved = json_util.loads(canonical(mongo_dump(DB())))
    assert saved['conversations']['indexes'][0]['key'] == [['owner_id', 1], ['conversation_id', 1]]
