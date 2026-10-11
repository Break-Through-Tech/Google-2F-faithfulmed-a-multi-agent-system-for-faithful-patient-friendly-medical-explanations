# MedlinePlus chunks and Gemini vector index

This is the new Gemini path for the MedlinePlus-only retrieval collection. It does
not reuse the older MiniLM vectors: changing the chunk text or embedding model
requires new document embeddings and matching query embeddings. The project
overview's `text-embedding-004` model was shut down in January 2026; this path
uses the current stable `gemini-embedding-2` model with 768 dimensions.

## Prepare the data (no API key)

From the repository root:

If using the repository's virtual environment without activating it, replace
`python` in the commands below with `.venv\Scripts\python.exe` on Windows.

```powershell
python data_pipeline/export_medlineplus_cleaned.py
python data_pipeline/chunk_medlineplus.py
```

The first command reads `data/MedLineGlossary/mplus_topics_2026-09-23.xml` and
exports 1,979 cleaned topics to `data/MedLineGlossary/medlineplus_cleaned.jsonl`.
It follows Ruhma's EDA rules (remove definitions of 15 characters or fewer, then
keep the first occurrence of each term) and additionally retains each XML topic's
ID and URL. The second command creates
`data/MedLineGlossary/medlineplus_chunks_800.jsonl`. It keeps each chunk at or
below 800 characters, preferring sentence boundaries, and checks that joining
the chunks reproduces the cleaned definition exactly. Both data files are
ignored by Git. The current run produced 6,883 chunks from 1,979 topics.
Ruhma's notebook reported 7,003 chunks using its exploratory splitter; this
reusable splitter makes different boundary choices and verifies that every
cleaned definition can be reconstructed exactly from its chunks.

## Embed and search (Gemini API key required)

Install only the two packages needed for this step:

```powershell
python -m pip install -r data_pipeline/requirements-gemini.txt
```

Open the repository-root `.env` file and paste your key after `GEMINI_API_KEY=`.
This file is ignored by Git. An already-set `GEMINI_API_KEY` environment variable
also works. The code reads the key locally and never prints it.

Start with five chunks to check access, model availability, and retrieval:

```powershell
python -m retrieval.gemini_chroma ingest --limit 5
python -m retrieval.gemini_chroma search "high blood pressure"
```

Once the small run succeeds, resume the same collection for every chunk:

```powershell
python -m retrieval.gemini_chroma ingest --all
```

While that command runs, check saved progress in another terminal without using
the Gemini API:

```powershell
python -m retrieval.gemini_chroma status
```

The ingestion command skips chunks already stored, so it can be rerun after a
quota or connection error. The full run pauses 12 seconds between 16-chunk
batches to stay below the observed free-tier limit of 100 embedding inputs per
minute; a per-minute quota response triggers at most three waits and retries.
This project's observed free-tier limit is also 1,000 embedding requests per
day. The command stops clearly at that daily limit, keeps all saved chunks, and
can be rerun after the quota resets. A complete free-tier build may therefore
take several days, depending on other project usage. The command
reports whether the collection contains all input chunks. A complete run has
**6,883** entries for this source snapshot. There is no silent switch to
another embedding model.

Collection: `faithfulmed_medlineplus_gemini_embedding_2_768_v1`, stored in
`data/MedLineGlossary/chroma_gemini_2/` (also ignored by Git). It stores chunk
text plus MedlinePlus URL, XML topic ID, title, and chunk number. It records a
hash of the chunk file and rejects a changed input or incompatible model/schema.
Gemini receives `title: ... | text: ...` for document embeddings and
`task: search result | query: ...` for query embeddings, following Google's
retrieval guidance. Search uses cosine distance; smaller distances are closer,
not confidence scores.

To use Rafi's framework-neutral retrieval function from Python:

```python
from retrieval import retrieve_context
from retrieval.gemini_chroma import (
    DB_PATH, GeminiEmbedder, GeminiTextQueryCollection, open_collection,
)

collection = GeminiTextQueryCollection(open_collection(DB_PATH), GeminiEmbedder())
results = retrieve_context(collection, "high blood pressure", top_k=3)
```

This builds a **local** Chroma collection. The team's shared-access delivery
still requires an agreed distribution or hosted Chroma arrangement. Keep a live
SQLite/Chroma directory on local disk while writing to it; share an immutable
snapshot after closing the writer, or have teammates rebuild it from the same
chunk file and scripts. Record the exact model, dimension, chunk rule, and
collection name in that handoff.

Google references: [model lifecycle](https://ai.google.dev/gemini-api/docs/deprecations/),
[embedding request and retrieval formatting](https://ai.google.dev/gemini-api/docs/embeddings),
and [API key setup](https://ai.google.dev/gemini-api/docs/api-key).
