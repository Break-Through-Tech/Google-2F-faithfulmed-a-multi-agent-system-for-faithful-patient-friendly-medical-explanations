"""Build and search a local MiniLM index of the current MedlinePlus chunks."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from retrieval import retrieve_context
from retrieval.medlineplus_index import CHUNKS_PATH, CHUNK_RULE, ROOT, read_chunks, source_digest

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DIMENSION = 384
COLLECTION = "faithfulmed_medlineplus_minilm_chunks_384_v1"
DB_PATH = ROOT / "data/MedLineGlossary/chroma_minilm_chunks"
MODEL_CACHE = ROOT / "data/MedLineGlossary/model_cache"
BATCH_SIZE = 128


def document_text(row: dict[str, Any]) -> str:
    return f"{row['medical_term']}\n{row['text']}"


def token_windows(text, tokenizer, max_tokens):
    """Split on whitespace at tokenizer offsets, preserving all input words."""
    budget = max_tokens - tokenizer.num_special_tokens_to_add(pair=False)
    windows, weights = [], []
    remaining = text.strip()
    while remaining:
        encoded = tokenizer(remaining, add_special_tokens=False, truncation=False, verbose=False,
                            return_offsets_mapping=True)
        if len(encoded["input_ids"]) <= budget:
            windows.append(remaining)
            weights.append(max(1, len(encoded["input_ids"])))
            break
        boundary = encoded["offset_mapping"][budget][0]
        # Avoid cutting through a word-piece sequence.
        while boundary > 0 and not remaining[boundary - 1].isspace():
            boundary -= 1
        if boundary == 0:
            raise ValueError("A single word exceeds MiniLM's token limit")
        piece = remaining[:boundary].strip()
        size = len(tokenizer(piece, add_special_tokens=False, truncation=False, verbose=False)["input_ids"])
        if not piece or size > budget:
            raise ValueError("Unable to split input within MiniLM's token limit")
        windows.append(piece)
        weights.append(max(1, size))
        remaining = remaining[boundary:].strip()
    return windows, weights


class MiniLMEmbedder:
    def __init__(self):
        from sentence_transformers import SentenceTransformer

        self.model = SentenceTransformer(
            MODEL, revision=REVISION, cache_folder=str(MODEL_CACHE), device="cpu"
        )
        self.windowed_inputs = 0

    def validate_lengths(self, texts: list[str]) -> int:
        tokens = self.model.tokenizer(texts, truncation=False, padding=False, verbose=False)["input_ids"]
        longest = max(map(len, tokens), default=0)
        return longest

    def embed(self, texts: list[str]) -> list[list[float]]:
        import numpy as np

        windows, groups = [], []
        for text in texts:
            pieces, weights = token_windows(text, self.model.tokenizer, self.model.max_seq_length)
            if not pieces:
                raise ValueError("Cannot embed empty text")
            groups.append((len(windows), len(pieces), weights))
            windows.extend(pieces)
            self.windowed_inputs += len(pieces) > 1
        encoded = self.model.encode(
            windows, batch_size=32, normalize_embeddings=True, show_progress_bar=False
        )
        vectors = np.asarray([
            np.average(encoded[start:start + count], axis=0, weights=weights)
            for start, count, weights in groups
        ])
        if vectors.shape != (len(texts), DIMENSION) or not np.isfinite(vectors).all():
            raise ValueError("MiniLM returned invalid embeddings")
        if not np.all(np.linalg.norm(vectors, axis=1) > 0):
            raise ValueError("MiniLM returned a zero vector")
        vectors /= np.linalg.norm(vectors, axis=1, keepdims=True)
        return vectors.tolist()


def open_collection(db_path: Path = DB_PATH, *, create: bool = False, digest: str | None = None):
    import chromadb
    from chromadb.config import Settings

    client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))
    expected = {
        "embedding_model": MODEL,
        "model_revision": REVISION,
        "dimension": DIMENSION,
        "chunk_rule": CHUNK_RULE,
        "document_format": "term_newline_text_v1",
        "long_text_policy": "whitespace_token_windows_256_token_weighted_mean_v1",
        "schema_version": 1,
        "hnsw:space": "cosine",
    }
    if create:
        if not digest:
            raise ValueError("Creating an index requires a source digest")
        collection = client.get_or_create_collection(
            COLLECTION, metadata={**expected, "source_sha256": digest}, embedding_function=None
        )
    else:
        collection = client.get_collection(COLLECTION, embedding_function=None)
    if any((collection.metadata or {}).get(k) != v for k, v in expected.items()):
        raise ValueError("MiniLM collection model or schema mismatch")
    if digest and collection.metadata.get("source_sha256") != digest:
        raise ValueError("Chunk source changed; use a new versioned collection")
    return collection


def status(chunks_path: Path = CHUNKS_PATH, db_path: Path = DB_PATH) -> dict[str, Any]:
    rows = read_chunks(chunks_path)
    collection = open_collection(db_path, digest=source_digest(chunks_path))
    expected = {row["id"] for row in rows}
    actual = set(collection.get(include=[])["ids"])
    return {
        "collection": COLLECTION, "model": MODEL, "model_revision": REVISION,
        "source_sha256": source_digest(chunks_path),
        "indexed_chunks": len(actual), "total_chunks": len(expected),
        "missing_chunks": len(expected - actual), "unexpected_chunks": len(actual - expected),
        "complete": actual == expected,
    }


def ingest(chunks_path: Path = CHUNKS_PATH, db_path: Path = DB_PATH, *, embedder=None) -> dict[str, Any]:
    rows = read_chunks(chunks_path)
    embedder = embedder or MiniLMEmbedder()
    # Audit input lengths; embed() handles overlong inputs without truncation.
    max_tokens = embedder.validate_lengths([document_text(row) for row in rows])
    collection = open_collection(db_path, create=True, digest=source_digest(chunks_path))
    existing = set(collection.get(include=[])["ids"])
    if existing - {row["id"] for row in rows}:
        raise ValueError("Collection contains unexpected chunk IDs")
    pending = [row for row in rows if row["id"] not in existing]
    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        vectors = embedder.embed([document_text(row) for row in batch])
        collection.upsert(
            ids=[row["id"] for row in batch], embeddings=vectors,
            documents=[row["text"] for row in batch],
            metadatas=[{
                "source": row["source"], "source_id": row["source_id"],
                "source_url": row["source_url"], "term": row["medical_term"],
                "chunk_index": row["chunk_index"], "chunk_count": row["chunk_count"],
            } for row in batch],
        )
        print(f"Saved {collection.count()}/{len(rows)} chunks", flush=True)
    return {**status(chunks_path, db_path), "embedded_this_run": len(pending),
            "max_input_tokens": max_tokens,
            "windowed_inputs_this_run": getattr(embedder, "windowed_inputs", 0)}


class MiniLMTextQueryCollection:
    """Match the existing retrieval interface using explicit MiniLM query vectors."""
    def __init__(self, db_path: Path = DB_PATH, *, embedder=None):
        self.target = open_collection(db_path)
        self.embedder = embedder

    def query(self, *, query_texts: list[str], n_results: int = 3, **kwargs):
        if type(n_results) is not int or n_results < 1:
            raise ValueError("n_results must be a positive integer")
        count = self.target.count()
        if not count:
            return {key: [[] for _ in query_texts] for key in ("ids", "documents", "metadatas", "distances")}
        if self.embedder is None:
            self.embedder = MiniLMEmbedder()
        kwargs.setdefault("include", ["documents", "metadatas", "distances"])
        return self.target.query(
            query_embeddings=self.embedder.embed(query_texts),
            n_results=min(n_results, count), **kwargs,
        )


def search(query: str, db_path: Path = DB_PATH, top_k: int = 3):
    return retrieve_context(MiniLMTextQueryCollection(db_path), query, top_k=top_k)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("ingest", "status"):
        command = commands.add_parser(name)
        command.add_argument("--chunks", type=Path, default=CHUNKS_PATH)
        command.add_argument("--db", type=Path, default=DB_PATH)
    lookup = commands.add_parser("search")
    lookup.add_argument("query")
    lookup.add_argument("--db", type=Path, default=DB_PATH)
    lookup.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()
    if args.command == "ingest":
        result = ingest(args.chunks, args.db)
    elif args.command == "status":
        result = status(args.chunks, args.db)
    else:
        result = search(args.query, args.db, args.top_k)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
