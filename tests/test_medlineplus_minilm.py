"""Real Chroma integration checks without model downloads or API calls."""
import json
import re
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from retrieval import retrieve_context
from retrieval.minilm_chroma import (
    DIMENSION, MiniLMEmbedder, MiniLMTextQueryCollection, ingest, open_collection, status, token_windows,
)


class FakeEmbedder:
    def __init__(self):
        self.calls = []

    def validate_lengths(self, texts):
        return max(map(len, texts))

    def embed(self, texts):
        self.calls.extend(texts)
        # Distinct orthogonal vectors verify query wiring and ranking.
        vectors = []
        for text in texts:
            vector = [0.0] * DIMENSION
            vector[0 if "blood" in text else 1] = 1.0
            vectors.append(vector)
        return vectors


class MiniLMIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.close_database)
        self.root = Path(self.temp.name)
        self.source = self.root / "chunks.jsonl"
        self.db = self.root / "db"
        self.rows = [{
            "id": str(index), "text": text, "medical_term": text,
            "source": "MedlinePlus", "source_id": str(index),
            "source_url": f"https://medlineplus.gov/{index}.html",
            "chunk_index": 0, "chunk_count": 1,
        } for index, text in enumerate(["blood pressure", "skin rash"])]
        self.source.write_text("".join(json.dumps(row) + "\n" for row in self.rows), encoding="utf-8")

    def close_database(self):
        # Chroma caches its Rust database handle; release it before Windows cleanup.
        from chromadb.api.shared_system_client import SharedSystemClient
        system = SharedSystemClient._identifier_to_system.pop(str(self.db), None)
        if system is not None:
            system.stop()
        self.temp.cleanup()

    def test_build_reopen_resume_and_retrieve(self):
        embedder = FakeEmbedder()
        self.assertTrue(ingest(self.source, self.db, embedder=embedder)["complete"])
        self.assertEqual(ingest(self.source, self.db, embedder=embedder)["embedded_this_run"], 0)
        self.assertEqual(len(embedder.calls), 2)
        wrapper = MiniLMTextQueryCollection(self.db, embedder=embedder)
        found = retrieve_context(wrapper, "blood", top_k=3)
        self.assertEqual(len(found), 2)
        self.assertEqual(found[0]["id"], "0")
        self.assertEqual(found[0]["text"], "blood pressure")
        self.assertEqual(found[0]["metadata"]["source_url"], "https://medlineplus.gov/0.html")
        self.assertEqual(retrieve_context(wrapper, " "), [])
        self.assertEqual(retrieve_context(wrapper, "blood", where={"source": "absent"}), [])
        self.assertTrue(status(self.source, self.db)["complete"])

    def test_changed_source_and_wrong_model_are_rejected(self):
        ingest(self.source, self.db, embedder=FakeEmbedder())
        self.source.write_text(self.source.read_text() + "\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "source changed"):
            ingest(self.source, self.db, embedder=FakeEmbedder())
        collection = open_collection(self.db)
        metadata = {k: v for k, v in collection.metadata.items() if k != "hnsw:space"}
        collection.modify(metadata={**metadata, "embedding_model": "wrong"})
        with self.assertRaisesRegex(ValueError, "schema mismatch"):
            open_collection(self.db)

    def test_overlong_text_preserves_all_words_in_token_windows(self):
        class WordTokenizer:
            def num_special_tokens_to_add(self, pair=False):
                return 2

            def __call__(self, text, **kwargs):
                matches = list(re.finditer(r"\S+", text))
                return {"input_ids": list(range(len(matches))),
                        "offset_mapping": [match.span() for match in matches]}

        text = " ".join(f"word{i}" for i in range(600))
        pieces, weights = token_windows(text, WordTokenizer(), 256)
        self.assertEqual(" ".join(pieces), text)
        self.assertEqual(weights, [254, 254, 92])

        import numpy as np
        def encode(windows, **kwargs):
            self.assertEqual(windows, ["one two", "three"])
            return np.eye(2, DIMENSION)

        embedder = MiniLMEmbedder.__new__(MiniLMEmbedder)
        embedder.windowed_inputs = 0
        embedder.model = SimpleNamespace(tokenizer=WordTokenizer(), max_seq_length=4, encode=encode)
        vector = embedder.embed(["one two three"])[0]
        self.assertAlmostEqual(vector[0], 2 / 5 ** 0.5)
        self.assertAlmostEqual(vector[1], 1 / 5 ** 0.5)
        self.assertAlmostEqual(np.linalg.norm(vector), 1)


if __name__ == "__main__":
    unittest.main()
