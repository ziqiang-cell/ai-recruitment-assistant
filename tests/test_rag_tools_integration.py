"""真实 Chroma + 默认本地 ONNX Embedding；全部资源位于项目外临时目录。"""

import json
import os
from pathlib import Path
import shutil
import socket
import tempfile
import unittest
from unittest.mock import patch

import chromadb
from chromadb.api.client import Client
from chromadb.api.models.Collection import Collection
from chromadb.utils.embedding_functions.onnx_mini_lm_l6_v2 import ONNXMiniLM_L6_V2

import rag
from rag_tools import search_recruitment_knowledge


class RealChromaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cache = Path(ONNXMiniLM_L6_V2.DOWNLOAD_PATH)
        required = ["config.json", "model.onnx", "special_tokens_map.json", "tokenizer_config.json", "tokenizer.json", "vocab.txt"]
        if not all((cache / ONNXMiniLM_L6_V2.EXTRACTED_FOLDER_NAME / name).is_file() for name in required):
            raise unittest.SkipTest("BLOCKED: default ONNX model cache is incomplete; no download permitted")

        # Rust 客户端在 Windows 上可能继续持有数据库句柄；只清理由系统维护的临时目录。
        cls.temp = tempfile.TemporaryDirectory(prefix="rag_tool_real_", ignore_cleanup_errors=True)
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name)
        cls.database = cls.root / "db"
        cls.cache_copy = cls.root / "model_cache"
        shutil.copytree(cache, cls.cache_copy)

        cls.env_patch = patch.dict(os.environ, {"ANONYMIZED_TELEMETRY": "False"})
        cls.env_patch.start()
        cls.addClassCleanup(cls.env_patch.stop)
        cls.cache_patch = patch.object(ONNXMiniLM_L6_V2, "DOWNLOAD_PATH", cls.cache_copy)
        cls.cache_patch.start()
        cls.addClassCleanup(cls.cache_patch.stop)
        # 不替换 Embedding；保留实际 ONNX 推理，只阻止下载与向外连接。
        cls.download_patch = patch.object(ONNXMiniLM_L6_V2, "_download", side_effect=AssertionError("Model downloads are forbidden"))
        cls.download_patch.start()
        cls.addClassCleanup(cls.download_patch.stop)
        cls.network_patch = patch.object(socket.socket, "connect", side_effect=AssertionError("Network connections are forbidden"))
        cls.network_patch.start()
        cls.addClassCleanup(cls.network_patch.stop)
        cls.client = chromadb.PersistentClient(path=str(cls.database))
        cls.collection = cls.client.create_collection(name=rag.COLLECTION_NAME)
        cls.client.create_collection(name="empty_recruitment_standards")
        cls.collection.add(
            ids=["fictional_python", "fictional_rag", "fictional_communication"],
            documents=["Fictional hiring standard: Python programming and debugging.", "Fictional hiring standard: RAG, embeddings and vector retrieval.", "Fictional hiring standard: teamwork and communication."],
            metadatas=[{"source": "fictional_standard.md", "chunk_index": i} for i in range(3)],
        )
        cls.logical_before = cls.collection.get(include=["documents", "metadatas"])
        cls.collection_names_before = sorted(c.name for c in cls.client.list_collections())

    def setUp(self):
        self.enterContext(patch.object(rag, "DATABASE_DIR", self.database))
        # Fixture 写入已完成。以下断言禁止 Tool 或 V6 对比查询主动写入/创建。
        for owner, methods in [(Client, ["create_collection", "get_or_create_collection", "delete_collection"]), (Collection, ["add", "upsert", "update", "delete"]), (rag, ["ensure_knowledge_base", "build_or_update_knowledge_base", "rebuild_knowledge_base"])]:
            for name in methods:
                self.enterContext(patch.object(owner, name, side_effect=AssertionError("Unexpected write operation: " + name)))

    def tearDown(self):
        self.assertEqual(sorted(c.name for c in self.client.list_collections()), self.collection_names_before)
        self.assertEqual(self.collection.get(include=["documents", "metadatas"]), self.logical_before)

    def test_real_query_and_multiple_results(self):
        response = search_recruitment_knowledge("  Python programming  ", top_k=3)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["count"], 3)
        self.assertTrue(all(r["source"] == "fictional_standard.md" for r in response["results"]))
        self.assertEqual(json.loads(json.dumps(response, allow_nan=False)), response)

    def test_real_existing_empty_collection(self):
        with patch.object(rag, "COLLECTION_NAME", "empty_recruitment_standards"):
            self.assertEqual(search_recruitment_knowledge("Python"), {"ok": True, "results": [], "count": 0, "error": None})

    def test_real_missing_collection_not_created(self):
        with patch.object(rag, "COLLECTION_NAME", "missing_recruitment_standards"):
            self.assertEqual(search_recruitment_knowledge("Python")["error"]["code"], "KNOWLEDGE_BASE_NOT_READY")

    def test_real_missing_database_not_created(self):
        missing = self.root / "missing_db"
        with patch.object(rag, "DATABASE_DIR", missing):
            self.assertEqual(search_recruitment_knowledge("Python")["error"]["code"], "KNOWLEDGE_BASE_NOT_READY")
        self.assertFalse(missing.exists())

    def test_real_empty_directory_not_initialized(self):
        empty = self.root / "empty_directory"
        empty.mkdir(exist_ok=True)
        with patch.object(rag, "DATABASE_DIR", empty):
            self.assertEqual(search_recruitment_knowledge("Python")["error"]["code"], "KNOWLEDGE_BASE_NOT_READY")
        self.assertEqual(list(empty.iterdir()), [])

    def test_real_threshold_filters_all_results(self):
        response = search_recruitment_knowledge("completely unrelated fictional topic", max_distance=0)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["count"], 0)

    def test_real_v6_results_match_tool(self):
        # V6 入口的默认 opener 本来允许创建；此处替换为已有集合，避免违反写入禁令。
        with patch.object(rag, "_get_collection", return_value=self.collection):
            for top_k in [1, 4, 8]:
                with self.subTest(top_k=top_k):
                    expected = rag.retrieve_context("Python programming", top_k=top_k)
                    actual = search_recruitment_knowledge("Python programming", top_k=top_k)
                    self.assertTrue(actual["ok"], actual)
                    self.assertEqual(actual["results"], expected)

    def test_real_threshold_matches_v6(self):
        with patch.object(rag, "_get_collection", return_value=self.collection):
            expected = rag.retrieve_context("RAG embeddings", max_distance=1.5)
        response = search_recruitment_knowledge("RAG embeddings", max_distance=1.5)
        self.assertTrue(response["ok"], response)
        self.assertEqual(response["results"], expected)


if __name__ == "__main__":
    unittest.main()
