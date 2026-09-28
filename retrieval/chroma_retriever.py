"""Small adapter around a Chroma-compatible collection.

The adapter intentionally does not import Chroma or an orchestration framework. A
collection only needs to provide Chroma's ``query`` method, which keeps this
interface usable from Google ADK, a plain Python pipeline, or tests.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Protocol


class ChromaCollection(Protocol):
    """The portion of the Chroma collection interface used by this adapter."""

    def query(self, **kwargs: Any) -> dict[str, list[list[Any]]]:
        """Return Chroma query results for the supplied query text."""


@dataclass(frozen=True)
class RetrievedChunk:
    """One retrieved document and the metadata needed for downstream grounding."""

    id: str
    text: str
    metadata: dict[str, Any]
    distance: float | None

    def as_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable result for an LLM or pipeline step."""
        return asdict(self)


def retrieve_context(
    collection: ChromaCollection,
    query: str,
    *,
    top_k: int = 5,
    where: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Retrieve and normalize the most relevant chunks for ``query``.

    Args:
        collection: A Chroma collection or test double exposing ``query``.
        query: Medical or clinical term/question to search for.
        top_k: Maximum number of chunks to return. Must be positive.
        where: Optional Chroma metadata filter.

    Returns:
        A list of dictionaries with ``id``, ``text``, ``metadata``, and
        ``distance`` keys, ordered as returned by Chroma. An empty query or a
        collection with no matches returns an empty list.
    """
    normalized_query = query.strip()
    if not normalized_query:
        return []
    if top_k < 1:
        raise ValueError("top_k must be at least 1")

    query_kwargs: dict[str, Any] = {
        "query_texts": [normalized_query],
        "n_results": top_k,
    }
    if where is not None:
        query_kwargs["where"] = where

    raw_results = collection.query(**query_kwargs)
    ids = _first_result_list(raw_results.get("ids"))
    documents = _first_result_list(raw_results.get("documents"))
    metadatas = _first_result_list(raw_results.get("metadatas"))
    distances = _first_result_list(raw_results.get("distances"))

    chunks: list[dict[str, Any]] = []
    for index, chunk_id in enumerate(ids):
        document = documents[index] if index < len(documents) else ""
        metadata = metadatas[index] if index < len(metadatas) else {}
        distance = distances[index] if index < len(distances) else None
        if not chunk_id or not document:
            continue
        chunks.append(
            RetrievedChunk(
                id=str(chunk_id),
                text=str(document),
                metadata=dict(metadata or {}),
                distance=float(distance) if distance is not None else None,
            ).as_dict()
        )

    return chunks


def _first_result_list(value: Any) -> list[Any]:
    """Extract the first query's result list from Chroma's nested response."""
    if not value:
        return []
    if isinstance(value, list) and value and isinstance(value[0], list):
        return value[0]
    return value if isinstance(value, list) else []