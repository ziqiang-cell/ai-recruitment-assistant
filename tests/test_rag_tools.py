"""Mock 单元测试与 V6 接口回归；不会连接原始数据库。"""

import inspect
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from chromadb.errors import NotFoundError

import rag
import rag_tools


def sample_results():
    return [
        {"text": "虚构标准：Python 基础", "source": "standard.md", "chunk_index": 0, "distance": 0.25},
        {"text": "虚构标准：沟通能力", "source": "standard.md", "chunk_index": 1, "distance": 0.75},
    ]


class ToolValidationTests(unittest.TestCase):
    def setUp(self):
        self.retriever = self.enterContext(patch("rag_tools.retrieve_existing_context", return_value=[]))
        self.client = self.enterContext(patch("rag.chromadb.PersistentClient"))

    def assert_invalid(self, code, **arguments):
        arguments.setdefault("query", "Python")
        response = rag_tools.search_recruitment_knowledge(**arguments)
        self.assertEqual(response["error"]["code"], code)
        self.assertFalse(response["ok"])
        self.assertEqual(response["results"], [])
        self.assertEqual(response["count"], 0)
        json.dumps(response, allow_nan=False)
        self.retriever.assert_not_called()
        self.client.assert_not_called()

    def test_empty_query(self):
        self.assert_invalid("INVALID_QUERY", query="")

    def test_whitespace_query(self):
        self.assert_invalid("INVALID_QUERY", query=" \t\n ")

    def test_non_string_query(self):
        for value in [None, 5, 1.2, True, [], {}, b"Python"]:
            with self.subTest(value=value):
                self.assert_invalid("INVALID_QUERY", query=value)

    def test_query_too_long(self):
        self.assert_invalid("INVALID_QUERY", query="学" * 2001)

    def test_query_length_boundaries_and_trimming(self):
        for value in ["学", "学" * 2000, "  " + "学" * 2000 + "\n"]:
            with self.subTest(length=len(value)):
                response = rag_tools.search_recruitment_knowledge(value)
                self.assertTrue(response["ok"])
                self.retriever.assert_called_with(value.strip(), 4, None)

    def test_top_k_minimum(self):
        self.assertTrue(rag_tools.search_recruitment_knowledge("Python", top_k=1)["ok"])
        self.retriever.assert_called_once_with("Python", 1, None)

    def test_top_k_maximum(self):
        self.assertTrue(rag_tools.search_recruitment_knowledge("Python", top_k=8)["ok"])
        self.retriever.assert_called_once_with("Python", 8, None)

    def test_top_k_out_of_range(self):
        for value in [-1, 0, 9, 100]:
            with self.subTest(value=value):
                self.assert_invalid("INVALID_TOP_K", top_k=value)

    def test_top_k_wrong_type(self):
        for value in [None, 1.0, "4", [], {}]:
            with self.subTest(value=value):
                self.assert_invalid("INVALID_TOP_K", top_k=value)

    def test_top_k_boolean(self):
        for value in [True, False]:
            with self.subTest(value=value):
                self.assert_invalid("INVALID_TOP_K", top_k=value)

    def test_distance_none(self):
        self.assertTrue(rag_tools.search_recruitment_knowledge("Python", max_distance=None)["ok"])
        self.retriever.assert_called_once_with("Python", 4, None)

    def test_distance_zero(self):
        self.assertTrue(rag_tools.search_recruitment_knowledge("Python", max_distance=0)["ok"])
        self.retriever.assert_called_once_with("Python", 4, 0)

    def test_distance_positive(self):
        for value in [1, 0.5, 10**400]:
            with self.subTest(value=value):
                self.assertTrue(rag_tools.search_recruitment_knowledge("Python", max_distance=value)["ok"])
                self.retriever.assert_called_with("Python", 4, value)

    def test_distance_negative(self):
        for value in [-1, -0.1]:
            with self.subTest(value=value):
                self.assert_invalid("INVALID_DISTANCE", max_distance=value)

    def test_distance_nan(self):
        self.assert_invalid("INVALID_DISTANCE", max_distance=float("nan"))

    def test_distance_infinity(self):
        for value in [float("inf"), float("-inf")]:
            with self.subTest(value=value):
                self.assert_invalid("INVALID_DISTANCE", max_distance=value)

    def test_distance_boolean(self):
        for value in [True, False]:
            with self.subTest(value=value):
                self.assert_invalid("INVALID_DISTANCE", max_distance=value)

    def test_distance_wrong_type(self):
        for value in ["0.5", [], {}, 1 + 2j]:
            with self.subTest(value=str(value)):
                self.assert_invalid("INVALID_DISTANCE", max_distance=value)

    def test_public_signature_has_no_path_or_collection_argument(self):
        signature = inspect.signature(rag_tools.search_recruitment_knowledge)
        self.assertEqual(str(signature), "(query, top_k=4, max_distance=None)")
        with self.assertRaises(TypeError):
            rag_tools.search_recruitment_knowledge("Python", database_path="external")
        with self.assertRaises(TypeError):
            rag_tools.search_recruitment_knowledge("Python", collection_name="external")
        self.retriever.assert_not_called()


class ToolResponseTests(unittest.TestCase):
    def setUp(self):
        self.retriever = self.enterContext(patch("rag_tools.retrieve_existing_context"))
        self.client = self.enterContext(patch("rag.chromadb.PersistentClient"))

    def test_normal_query(self):
        self.retriever.return_value = sample_results()[:1]
        response = rag_tools.search_recruitment_knowledge("  Python  ")
        self.assertEqual(response, {"ok": True, "results": sample_results()[:1], "count": 1, "error": None})
        self.retriever.assert_called_once_with("Python", 4, None)

    def test_multiple_results(self):
        self.retriever.return_value = sample_results()
        response = rag_tools.search_recruitment_knowledge("Python")
        self.assertEqual(response["count"], 2)
        self.assertEqual(response["results"], sample_results())

    def test_no_relevant_results(self):
        self.retriever.return_value = []
        self.assertEqual(rag_tools.search_recruitment_knowledge("无相关结果"), {"ok": True, "results": [], "count": 0, "error": None})

    def test_not_ready_error_is_sanitized(self):
        self.retriever.side_effect = rag.KnowledgeBaseNotReadyError("sensitive internal details")
        response = rag_tools.search_recruitment_knowledge("Python")
        self.assertEqual(response["error"]["code"], "KNOWLEDGE_BASE_NOT_READY")
        self.assertNotIn("sensitive", json.dumps(response))

    def test_retrieval_error_is_sanitized(self):
        self.retriever.side_effect = RuntimeError("private credential and internal path")
        response = rag_tools.search_recruitment_knowledge("Python")
        self.assertEqual(response["error"]["code"], "RETRIEVAL_ERROR")
        self.assertEqual(response["results"], [])
        self.assertEqual(response["count"], 0)
        self.assertNotIn("private", json.dumps(response))

    def test_success_is_json_serializable(self):
        self.retriever.return_value = sample_results()
        response = rag_tools.search_recruitment_knowledge("Python")
        self.assertEqual(json.loads(json.dumps(response, ensure_ascii=False, allow_nan=False)), response)

    def test_non_json_evidence_is_error(self):
        for value in [[{"text": object()}], [{"distance": float("nan")}], [{"distance": float("inf")}]]:
            with self.subTest(value_type=str(type(value[0]))):
                self.retriever.return_value = value
                self.assertEqual(rag_tools.search_recruitment_knowledge("Python")["error"]["code"], "RETRIEVAL_ERROR")


class ExistingCollectionTests(unittest.TestCase):
    def setUp(self):
        self.directory = self.enterContext(tempfile.TemporaryDirectory(prefix="rag_tool_unit_"))
        self.database = Path(self.directory) / "isolated_db"
        self.enterContext(patch.object(rag, "DATABASE_DIR", self.database))
        self.client_factory = self.enterContext(patch("rag.chromadb.PersistentClient"))
        self.client = self.client_factory.return_value
        self.collection = self.client.get_collection.return_value
        self.collection.count.return_value = 2
        self.collection.query.return_value = {
            "documents": [[r["text"] for r in sample_results()]],
            "metadatas": [[{"source": r["source"], "chunk_index": r["chunk_index"]} for r in sample_results()]],
            "distances": [[0.25, 0.75]],
        }

    def make_database_marker(self):
        # 只是 Mock 前置条件标记，不是真实 SQLite 或 Chroma 数据库。
        self.database.mkdir()
        (self.database / "chroma.sqlite3").touch()

    def test_missing_database_directory_does_not_initialize_client(self):
        response = rag_tools.search_recruitment_knowledge("Python")
        self.assertEqual(response["error"]["code"], "KNOWLEDGE_BASE_NOT_READY")
        self.client_factory.assert_not_called()
        self.client.close.assert_not_called()
        self.assertFalse(self.database.exists())

    def test_empty_database_directory_does_not_initialize_client(self):
        self.database.mkdir()
        self.assertEqual(rag_tools.search_recruitment_knowledge("Python")["error"]["code"], "KNOWLEDGE_BASE_NOT_READY")
        self.client_factory.assert_not_called()
        self.client.close.assert_not_called()
        self.assertEqual(list(self.database.iterdir()), [])

    def test_missing_collection(self):
        self.make_database_marker()
        self.client.get_collection.side_effect = NotFoundError("internal collection name")
        response = rag_tools.search_recruitment_knowledge("Python")
        self.assertEqual(response["error"]["code"], "KNOWLEDGE_BASE_NOT_READY")
        self.client.close.assert_called_once_with()
        self.client.get_or_create_collection.assert_not_called()
        self.client.create_collection.assert_not_called()

    def test_existing_empty_collection(self):
        self.make_database_marker()
        self.collection.count.return_value = 0
        self.assertEqual(rag_tools.search_recruitment_knowledge("Python"), {"ok": True, "results": [], "count": 0, "error": None})
        self.collection.query.assert_not_called()
        self.client.close.assert_called_once_with()

    def test_chroma_query_failure(self):
        self.make_database_marker()
        self.collection.query.side_effect = RuntimeError("private details")
        response = rag_tools.search_recruitment_knowledge("Python")
        self.assertEqual(response["error"]["code"], "RETRIEVAL_ERROR")
        self.assertNotIn("private", json.dumps(response))
        self.client.close.assert_called_once_with()

    def test_client_initialization_failure(self):
        self.make_database_marker()
        self.client_factory.side_effect = RuntimeError("internal database path")
        self.assertEqual(rag_tools.search_recruitment_knowledge("Python")["error"]["code"], "RETRIEVAL_ERROR")
        self.client.close.assert_not_called()

    def test_unexpected_get_collection_failure_is_not_disguised_as_missing(self):
        self.make_database_marker()
        self.client.get_collection.side_effect = RuntimeError("corrupt database")
        self.assertEqual(rag_tools.search_recruitment_knowledge("Python")["error"]["code"], "RETRIEVAL_ERROR")
        self.client.close.assert_called_once_with()

    def test_count_failure(self):
        self.make_database_marker()
        self.collection.count.side_effect = RuntimeError("internal failure")
        self.assertEqual(rag_tools.search_recruitment_knowledge("Python")["error"]["code"], "RETRIEVAL_ERROR")
        self.client.close.assert_called_once_with()

    def test_client_close_failure_is_sanitized(self):
        self.make_database_marker()
        self.client.close.side_effect = RuntimeError("private client cleanup detail")
        response = rag_tools.search_recruitment_knowledge("Python")
        self.assertFalse(response["ok"])
        self.assertEqual(response["error"]["code"], "RETRIEVAL_ERROR")
        self.assertEqual(response["results"], [])
        self.assertEqual(response["count"], 0)
        self.assertNotIn("private", json.dumps(response))
        self.collection.query.assert_called_once()
        self.client.close.assert_called_once_with()

    def test_tool_never_creates_deletes_updates_or_rebuilds(self):
        self.make_database_marker()
        with patch.object(rag, "ensure_knowledge_base") as ensure, patch.object(rag, "build_or_update_knowledge_base") as build, patch.object(rag, "rebuild_knowledge_base") as rebuild:
            response = rag_tools.search_recruitment_knowledge("Python")
            self.assertTrue(response["ok"])
            self.client.get_collection.assert_called_once_with(name=rag.COLLECTION_NAME)
            self.client.close.assert_called_once_with()
            for method in [self.client.get_or_create_collection, self.client.create_collection, self.client.delete_collection, self.collection.add, self.collection.upsert, self.collection.update, self.collection.delete, ensure, build, rebuild]:
                method.assert_not_called()

    def test_shared_distance_filter_includes_exact_boundary(self):
        self.make_database_marker()
        response = rag_tools.search_recruitment_knowledge("Python", max_distance=0.25)
        self.assertEqual(response["results"], sample_results()[:1])
        self.client.close.assert_called_once_with()

    def test_no_match_after_distance_filter_is_success(self):
        self.make_database_marker()
        self.assertEqual(rag_tools.search_recruitment_knowledge("Python", max_distance=0)["results"], [])
        self.client.close.assert_called_once_with()


class V6CompatibilityTests(unittest.TestCase):
    def setUp(self):
        self.collection = MagicMock()
        self.collection.count.return_value = 2
        self.collection.query.return_value = {"documents": [["Python", "沟通"]], "metadatas": [[{"source": "standard.md", "chunk_index": 0}, {"source": "standard.md", "chunk_index": 1}]], "distances": [[0.25, 0.75]]}
        self.get_collection = self.enterContext(patch.object(rag, "_get_collection", return_value=self.collection))

    def test_v6_signature_unchanged(self):
        self.assertEqual(str(inspect.signature(rag.retrieve_context)), "(query, top_k=4, max_distance=None)")

    def test_v6_default_results_and_top_k_clamping(self):
        result = rag.retrieve_context("Python")
        self.assertEqual(len(result), 2)
        self.assertEqual(set(result[0]), {"text", "source", "chunk_index", "distance"})
        self.assertEqual([r["distance"] for r in result], [0.25, 0.75])
        self.collection.query.assert_called_once_with(query_texts=["Python"], n_results=2, include=["documents", "metadatas", "distances"])

    def test_v6_top_k_one(self):
        rag.retrieve_context("Python", top_k=1)
        self.assertEqual(self.collection.query.call_args.kwargs["n_results"], 1)

    def test_v6_empty_query_still_opens_collection_then_returns_empty(self):
        self.assertEqual(rag.retrieve_context("  "), [])
        self.get_collection.assert_called_once_with()
        self.collection.query.assert_not_called()

    def test_v6_nonpositive_top_k_returns_empty(self):
        self.assertEqual(rag.retrieve_context("Python", top_k=0), [])
        self.collection.query.assert_not_called()

    def test_v6_empty_collection(self):
        self.collection.count.return_value = 0
        self.assertEqual(rag.retrieve_context("Python"), [])
        self.collection.query.assert_not_called()

    def test_v6_distance_boundary(self):
        self.assertEqual([r["distance"] for r in rag.retrieve_context("Python", max_distance=0.25)], [0.25])

    def test_v6_exceptions_still_propagate(self):
        self.collection.query.side_effect = RuntimeError("legacy failure")
        with self.assertRaisesRegex(RuntimeError, "legacy failure"):
            rag.retrieve_context("Python")


class V6OpenerTests(unittest.TestCase):
    def test_v6_default_opener_still_gets_or_creates(self):
        with patch("rag.chromadb.PersistentClient") as factory:
            result = rag._get_collection()
            factory.assert_called_once_with(path=str(rag.DATABASE_DIR))
            factory.return_value.get_or_create_collection.assert_called_once_with(name=rag.COLLECTION_NAME)
            self.assertIs(result, factory.return_value.get_or_create_collection.return_value)


if __name__ == "__main__":
    unittest.main()
