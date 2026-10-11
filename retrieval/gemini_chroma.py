"""Gemini Embedding 2 index for chunked MedlinePlus and Chroma-compatible search."""

from __future__ import annotations

import argparse
import json
import math
import os
import time
from pathlib import Path
from typing import Any

from retrieval import retrieve_context
from retrieval.medlineplus_index import CHUNKS_PATH, CHUNK_RULE, read_chunks, source_digest


ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "data/MedLineGlossary/chroma_gemini_2"
KEY_PATH = ROOT / ".env"
MODEL = "gemini-embedding-2"
DIMENSION = 768
COLLECTION = "faithfulmed_medlineplus_gemini_embedding_2_768_v1"
BATCH_SIZE = 16


def api_key() -> str:
    """Read a local environment variable or the ignored root .env file."""
    key = os.environ.get("GEMINI_API_KEY", "").strip()
    if key:
        return key
    if KEY_PATH.exists():
        for line in KEY_PATH.read_text(encoding="utf-8").splitlines():
            if line.strip().startswith("GEMINI_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"\'')
                if key:
                    return key
    raise RuntimeError(f"Set GEMINI_API_KEY in your environment or fill in {KEY_PATH}")


def document_prompt(term: str, text: str) -> str:
    return f"title: {term} | text: {text}"


def query_prompt(query: str) -> str:
    return f"task: search result | query: {query}"


class GeminiEmbedder:
    """Use one Gemini model and vector dimension for documents and queries."""

    def __init__(self, client: Any | None = None):
        if client is None:
            try:
                from google import genai
            except ImportError as exc:
                raise RuntimeError("Install data_pipeline/requirements-gemini.txt") from exc
            client = genai.Client(api_key=api_key())
        self.client = client

    def embed(self, prompts: list[str]) -> list[list[float]]:
        if not prompts:
            return []
        from google.genai import types

        # Each Content object produces its own vector with Embedding 2.
        contents = [types.Content(parts=[types.Part.from_text(text=prompt)]) for prompt in prompts]
        response = self.client.models.embed_content(
            model=MODEL,
            contents=contents,
            config=types.EmbedContentConfig(output_dimensionality=DIMENSION),
        )
        embeddings = response.embeddings or []
        if len(embeddings) != len(prompts):
            raise RuntimeError("Gemini returned the wrong number of embeddings")
        vectors = [embedding.values for embedding in embeddings]
        if any(
            vector is None
            or len(vector) != DIMENSION
            or not all(math.isfinite(value) for value in vector)
            for vector in vectors
        ):
            raise RuntimeError("Gemini returned an invalid embedding")
        return vectors

    def embed_documents(self, rows: list[dict[str, Any]]) -> list[list[float]]:
        return self.embed([document_prompt(row["medical_term"], row["text"]) for row in rows])

    def embed_queries(self, queries: list[str]) -> list[list[float]]:
        return self.embed([query_prompt(query) for query in queries])


def open_collection(db_path: Path, *, create: bool = False, digest: str | None = None) -> Any:
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError as exc:
        raise RuntimeError("Install data_pipeline/requirements-gemini.txt") from exc
    client = chromadb.PersistentClient(path=str(db_path), settings=Settings(anonymized_telemetry=False))
    expected = {
        "embedding_model": MODEL,
        "dimension": DIMENSION,
        "chunk_rule": CHUNK_RULE,
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
    metadata = collection.metadata or {}
    if any(metadata.get(key) != value for key, value in expected.items()):
        raise ValueError("Chroma collection model or chunk schema mismatch")
    if digest and metadata.get("source_sha256") != digest:
        raise ValueError("Chunk source changed; use a new versioned collection")
    return collection


def ingest(
    chunks_path: Path = CHUNKS_PATH,
    db_path: Path = DB_PATH,
    *,
    limit: int | None = None,
    seconds_per_batch: float = 0,
    embedder: GeminiEmbedder | None = None,
    collection: Any | None = None,
) -> dict[str, Any]:
    """Embed missing chunks in small restartable batches."""
    rows = read_chunks(chunks_path)
    if limit is not None and limit < 1:
        raise ValueError("limit must be positive")
    if seconds_per_batch < 0:
        raise ValueError("seconds_per_batch cannot be negative")
    selected = rows[:limit] if limit else rows
    if collection is None:
        collection = open_collection(db_path, create=True, digest=source_digest(chunks_path))
    if embedder is None:
        embedder = GeminiEmbedder()
    added = 0
    for start in range(0, len(selected), BATCH_SIZE):
        batch = selected[start : start + BATCH_SIZE]
        existing_ids = set(collection.get(ids=[row["id"] for row in batch])["ids"])
        pending = [row for row in batch if row["id"] not in existing_ids]
        if not pending:
            continue
        for attempt in range(4):
            try:
                vectors = embedder.embed_documents(pending)
                break
            except Exception as exc:
                detail = str(exc)
                if "RequestsPerDay" in detail:
                    raise RuntimeError(
                        "Gemini's daily embedding quota is exhausted. Saved chunks are intact; "
                        "rerun ingest --all after the daily quota resets."
                    ) from exc
                is_quota = getattr(exc, "code", None) == 429 or "429 RESOURCE_EXHAUSTED" in detail
                if not is_quota or attempt == 3:
                    raise
                print("Gemini per-minute quota reached; waiting 65 seconds before retrying")
                time.sleep(65)
        collection.upsert(
            ids=[row["id"] for row in pending],
            documents=[row["text"] for row in pending],
            embeddings=vectors,
            metadatas=[
                {
                    "source": row["source"],
                    "source_id": row["source_id"],
                    "source_url": row["source_url"],
                    "term": row["medical_term"],
                    "chunk_index": row["chunk_index"],
                    "chunk_count": row["chunk_count"],
                }
                for row in pending
            ],
        )
        added += len(pending)
        print(f"Embedded {added} new chunks; processed {min(start + BATCH_SIZE, len(selected))} selected chunks")
        if seconds_per_batch and start + BATCH_SIZE < len(selected):
            time.sleep(seconds_per_batch)
    return {
        "collection": COLLECTION,
        "model": MODEL,
        "total_chunks": len(rows),
        "selected_chunks": len(selected),
        "embedded_this_run": added,
        "collection_count": collection.count(),
        "complete": collection.count() == len(rows),
    }


class GeminiTextQueryCollection:
    """Present Gemini query vectors through Rafi's existing retrieval interface."""

    def __init__(self, target: Any, embedder: GeminiEmbedder):
        self.target = target
        self.embedder = embedder

    def query(self, *, query_texts: list[str], n_results: int = 3, **kwargs: Any) -> dict[str, Any]:
        if type(n_results) is not int or n_results < 1:
            raise ValueError("n_results must be a positive integer")
        if not self.target.count():
            return {key: [[] for _ in query_texts] for key in ("ids", "documents", "metadatas", "distances")}
        kwargs.setdefault("include", ["documents", "metadatas", "distances"])
        return self.target.query(
            query_embeddings=self.embedder.embed_queries(query_texts),
            n_results=min(n_results, self.target.count()),
            **kwargs,
        )


def search(query: str, db_path: Path = DB_PATH, top_k: int = 3) -> list[dict[str, Any]]:
    target = open_collection(db_path)
    wrapper = GeminiTextQueryCollection(target, GeminiEmbedder())
    return retrieve_context(wrapper, query, top_k=top_k)


def status(chunks_path: Path = CHUNKS_PATH, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Report saved progress without calling the Gemini API."""
    rows = read_chunks(chunks_path)
    collection = open_collection(db_path, digest=source_digest(chunks_path))
    count = collection.count()
    return {
        "collection": COLLECTION,
        "model": MODEL,
        "indexed_chunks": count,
        "total_chunks": len(rows),
        "complete": count == len(rows),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    build = commands.add_parser("ingest", help="Embed and index a small sample, or --all chunks")
    build.add_argument("--chunks", type=Path, default=CHUNKS_PATH)
    build.add_argument("--db", type=Path, default=DB_PATH)
    extent = build.add_mutually_exclusive_group()
    extent.add_argument("--limit", type=int, default=5)
    extent.add_argument("--all", action="store_true")
    build.add_argument(
        "--seconds-per-batch",
        type=float,
        default=None,
        help="Pause between batches (default: 12 seconds for --all, 0 for a sample)",
    )
    lookup = commands.add_parser("search", help="Search the Gemini MedlinePlus collection")
    lookup.add_argument("query")
    lookup.add_argument("--db", type=Path, default=DB_PATH)
    lookup.add_argument("--top-k", type=int, default=3)
    progress = commands.add_parser("status", help="Show saved index progress without an API call")
    progress.add_argument("--chunks", type=Path, default=CHUNKS_PATH)
    progress.add_argument("--db", type=Path, default=DB_PATH)
    args = parser.parse_args()
    if args.command == "ingest":
        pause = args.seconds_per_batch
        if pause is None:
            pause = 12 if args.all else 0
        result = ingest(args.chunks, args.db, limit=None if args.all else args.limit, seconds_per_batch=pause)
    elif args.command == "search":
        result = search(args.query, args.db, args.top_k)
    else:
        result = status(args.chunks, args.db)
    print(json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False))


if __name__ == "__main__":
    main()
