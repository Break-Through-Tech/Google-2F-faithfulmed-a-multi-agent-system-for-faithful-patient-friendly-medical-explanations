"""Offline checks for the new MedlinePlus chunk and Gemini retrieval handoff."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from data_pipeline.chunk_medlineplus import chunk_file, split_text
from retrieval import retrieve_context
from retrieval.gemini_chroma import (
    GeminiTextQueryCollection,
    document_prompt,
    ingest,
    query_prompt,
)


class FakeEmbedder:
    def __init__(self):
        self.documents = []
        self.queries = []

    def embed_documents(self, rows):
        self.documents.extend(document_prompt(row["medical_term"], row["text"]) for row in rows)
        return [[float(index), 1.0] for index, _ in enumerate(rows)]

    def embed_queries(self, queries):
        self.queries.extend(query_prompt(query) for query in queries)
        return [[1.0, 0.0] for _ in queries]


class QuotaOnceEmbedder(FakeEmbedder):
    def __init__(self):
        super().__init__()
        self.attempts = 0

    def embed_documents(self, rows):
        self.attempts += 1
        if self.attempts == 1:
            error = RuntimeError("per-minute quota")
            error.code = 429
            raise error
        return super().embed_documents(rows)


class DailyQuotaEmbedder(FakeEmbedder):
    def embed_documents(self, rows):
        error = RuntimeError("EmbedContentRequestsPerDayPerUserPerProjectPerModel-FreeTier")
        error.code = 429
        raise error


class FakeCollection:
    def __init__(self):
        self.rows = {}
        self.last_query = None

    def get(self, *, ids):
        return {"ids": [identifier for identifier in ids if identifier in self.rows]}

    def upsert(self, *, ids, documents, embeddings, metadatas):
        for identifier, document, vector, metadata in zip(ids, documents, embeddings, metadatas):
            self.rows[identifier] = (document, vector, metadata)

    def count(self):
        return len(self.rows)

    def query(self, *, query_embeddings, n_results, **kwargs):
        self.last_query = (query_embeddings, n_results, kwargs)
        matches = list(self.rows.items())[:n_results]
        return {
            "ids": [[identifier for identifier, _ in matches]],
            "documents": [[row[0] for _, row in matches]],
            "metadatas": [[row[2] for _, row in matches]],
            "distances": [[0.1 for _ in matches]],
        }


class MedlinePlusGeminiTests(unittest.TestCase):
    def test_chunking_preserves_cleaned_text_and_source(self):
        text = "First sentence. " + "many words " * 95 + "Final sentence."
        pieces = split_text(text, 80)
        self.assertEqual(" ".join(pieces), text)
        self.assertTrue(all(0 < len(piece) <= 80 for piece in pieces))

        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "cleaned.jsonl"
            output = Path(temporary) / "chunks.jsonl"
            topic = {
                "medical_term": "Example",
                "definition": text,
                "source": "MedlinePlus",
                "source_id": "123",
                "source_url": "https://medlineplus.gov/example.html",
            }
            source.write_text(json.dumps(topic) + "\n", encoding="utf-8")
            report = chunk_file(source, output, max_chars=80)
            chunks = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
            self.assertEqual(report["chunks"], len(chunks))
            self.assertEqual(" ".join(row["text"] for row in chunks), text)
            self.assertEqual(len({row["id"] for row in chunks}), len(chunks))
            self.assertTrue(all(row["source_id"] == "123" for row in chunks))

    def test_ingest_resumes_and_retrieval_uses_query_embedding(self):
        with tempfile.TemporaryDirectory() as temporary:
            chunks_path = Path(temporary) / "chunks.jsonl"
            rows = [
                {
                    "id": f"id-{index}",
                    "text": f"Definition {index}",
                    "medical_term": "Example",
                    "source": "MedlinePlus",
                    "source_id": "123",
                    "source_url": "https://medlineplus.gov/example.html",
                    "chunk_index": index,
                    "chunk_count": 2,
                }
                for index in range(2)
            ]
            chunks_path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
            target = FakeCollection()
            embedder = FakeEmbedder()
            first = ingest(chunks_path, limit=1, embedder=embedder, collection=target)
            self.assertEqual(first["collection_count"], 1)
            self.assertFalse(first["complete"])
            second = ingest(chunks_path, embedder=embedder, collection=target)
            self.assertEqual(second["embedded_this_run"], 1)
            self.assertTrue(second["complete"])
            self.assertEqual(len(embedder.documents), 2)

            wrapper = GeminiTextQueryCollection(target, embedder)
            found = retrieve_context(wrapper, "example query", top_k=3)
            self.assertEqual(len(found), 2)
            self.assertEqual(found[0]["metadata"]["source_id"], "123")
            self.assertEqual(embedder.queries, ["task: search result | query: example query"])
            self.assertEqual(target.last_query[0], [[1.0, 0.0]])
            self.assertEqual(target.last_query[1], 2)

    def test_quota_response_retries_without_losing_batch(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "chunks.jsonl"
            row = {
                "id": "one",
                "text": "Definition",
                "medical_term": "Example",
                "source": "MedlinePlus",
                "source_id": "123",
                "source_url": "https://medlineplus.gov/example.html",
                "chunk_index": 0,
                "chunk_count": 1,
            }
            source.write_text(json.dumps(row) + "\n", encoding="utf-8")
            target = FakeCollection()
            embedder = QuotaOnceEmbedder()
            with patch("retrieval.gemini_chroma.time.sleep") as sleep:
                report = ingest(source, embedder=embedder, collection=target)
            self.assertEqual(embedder.attempts, 2)
            sleep.assert_called_once_with(65)
            self.assertEqual(report["collection_count"], 1)

    def test_daily_quota_stops_without_waiting(self):
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "chunks.jsonl"
            row = {
                "id": "one",
                "text": "Definition",
                "medical_term": "Example",
                "source": "MedlinePlus",
                "source_id": "123",
                "source_url": "https://medlineplus.gov/example.html",
                "chunk_index": 0,
                "chunk_count": 1,
            }
            source.write_text(json.dumps(row) + "\n", encoding="utf-8")
            target = FakeCollection()
            with patch("retrieval.gemini_chroma.time.sleep") as sleep:
                with self.assertRaisesRegex(RuntimeError, "daily embedding quota"):
                    ingest(source, embedder=DailyQuotaEmbedder(), collection=target)
            sleep.assert_not_called()
            self.assertEqual(target.count(), 0)


if __name__ == "__main__":
    unittest.main()
