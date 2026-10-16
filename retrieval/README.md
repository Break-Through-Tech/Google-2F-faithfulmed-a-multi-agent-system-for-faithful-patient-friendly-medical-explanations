# Retrieval Adapter

This package provides the framework-neutral retrieval interface for FaithfulMed's Verifier work.

For the completed Gemini-based MedlinePlus collection, see
[`data_pipeline/GEMINI_MEDLINEPLUS.md`](../data_pipeline/GEMINI_MEDLINEPLUS.md).
Use `retrieval.gemini_chroma.GeminiTextQueryCollection` with `retrieve_context`.
It embeds queries with `gemini-embedding-2` and searches the matching 6,883
stored MedlinePlus vectors. The `retrieve_context` interface below is unchanged.
The earlier local fallback index and scripts were retired after Gemini retrieval
was verified. They are available only in Git history.

## Interface

```python
from retrieval import retrieve_context

results = retrieve_context(
    collection,
    "high blood pressure",
    top_k=5,
    where={"source": "medlineplus"},
)
```

`collection` must expose Chroma's `query` method. The adapter sends:

```python
collection.query(
    query_texts=[query],
    n_results=top_k,
    where=where,
)
```

The `where` argument is optional. The adapter does not create the collection or choose an embedding function; those responsibilities belong to the vector-store owner.

## Result format

The function returns a list ordered by the collection's result order. Each item has this shape:

```python
{
    "id": "chunk-123",
    "text": "Plain-language medical text...",
    "metadata": {
        "source": "medlineplus",
        "document_id": "...",
    },
    "distance": 0.18,
}
```

The result is intentionally a plain dictionary so it can be passed to a normal Python pipeline, Google ADK tool, or another orchestration layer. Empty queries, empty collections, and missing optional result fields produce an empty list or `None` distance rather than an exception. Invalid `top_k` values raise `ValueError`.

## Handoff contract

The vector-store owner should provide a populated Chroma collection whose stored documents are meaningful text chunks and whose metadata uses stable keys. The initial metadata contract should include a source identifier and a document or chunk identifier when available. Any additional metadata should remain JSON-serializable.

The adapter can be tested with a mock collection before the real collection is available. Once the shared collection and metadata keys are finalized, integration should only require passing that collection into `retrieve_context`.
