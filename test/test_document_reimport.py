"""同一产品的不同文档必须共存；重新导入只替换当前来源。"""
import os
import unittest
from unittest.mock import Mock, patch

os.environ.setdefault("LOG_CONSOLE_ENABLE", "false")
from app.import_process.agent.nodes import node_import_milvus as chunks_node
from app.import_process.agent.nodes import node_item_name_recognition as items_node


class DocumentReimportTests(unittest.TestCase):
    def test_chunks_cleanup_uses_source_document(self):
        client = Mock()
        chunks_node.step_3_clean_old_data(client, [
            {"item_name": "HAK180", "file_title": "HAK180安全手册"},
            {"item_name": "HAK180", "file_title": "HAK180安全手册"},
        ])
        self.assertEqual(client.delete.call_count, 1)
        self.assertEqual(client.delete.call_args.kwargs["filter"],
                         'file_title == "HAK180安全手册"')

    def test_missing_source_never_deletes_other_documents(self):
        client = Mock()
        with self.assertRaises(ValueError):
            chunks_node.step_3_clean_old_data(client, [{"item_name": "HAK180"}])
        client.delete.assert_not_called()

    def test_product_index_cleanup_uses_source_document(self):
        client = Mock()
        client.has_collection.return_value = True
        with patch.dict(os.environ, {"MILVUS_URL": "http://localhost:19530",
                                     "ITEM_NAME_COLLECTION": "items"}), \
             patch.object(items_node, "get_milvus_client", return_value=client):
            items_node.step_6_save_to_milvus({}, "HAK180安全手册", "HAK180", [1.0], {1: 1.0})
        self.assertEqual(client.delete.call_args.kwargs["filter"],
                         'file_title == "HAK180安全手册"')


if __name__ == "__main__":
    unittest.main()
