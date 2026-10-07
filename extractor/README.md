# FaithfulMed — Vaibhavi's Extractor / Vector Store

September contribution: load Ruhma's MedlinePlus embeddings into persistent ChromaDB and retrieve the three closest lay-language definitions for a medical term. MTSamples and Synthea are clinical inputs for EDA and later extraction; they are **not** the lay-language retrieval database.

## Start here

Open `extractor/Extractor_Vector_Store.ipynb` for a walkthrough, or run the following from the repository root using Python 3.11 or 3.12:

```bash
python -m pip install -r extractor/requirements.txt
python -m extractor.rag ingest "data/RAG_Embeddings_Full.jsonl" --db extractor/chroma_data
python -m extractor.rag search "hypertension" --db extractor/chroma_data --top-k 3
```

Put your downloaded embeddings in `data/`, or replace that path with their actual location. The uploaded filename was `RAG_Embeddings_Full (1).jsonl`; renaming it is optional. The first text search downloads MiniLM model weights. No Gemini key is needed for this supplied embedding file.

**Store the live database on local disk.** In Colab use `--db /content/faithfulmed_chroma`, rather than Google Drive. Rebuild from the JSONL when starting a new runtime. In this session the workspace-backed SQLite database failed an integrity check; `/tmp` local storage passed ingestion, repeat ingestion, reopen, integrity, and retrieval checks. The ZIP deliberately contains no live database.

## Actual embedding handoff

Ruhma's supplied updated notebook (`medical_rag_pipeline`, notebook JSON without an extension) uses `sentence-transformers/all-MiniLM-L6-v2`, with 384-dimensional vectors. Her README's Gemini description is stale. The supplied JSONL has 18,343 records: 1,015 MedlinePlus, 16,407 MedQuAD, and 921 PLABA. This index includes only the 1,015 MedlinePlus records, following the advisor's MedlinePlus-only RAG scope.

The official overview requests Gemini embeddings. This is a documented MiniLM fallback using the available handoff, not completion of that Gemini requirement. Switching requires regenerating all document vectors and query vectors with the same agreed Gemini model and creating a separate collection. Never mix Gemini queries with MiniLM document vectors.

## Collection and schema

Collection: `faithfulmed_medlineplus_minilm_v1`. Metric: cosine distance (smaller is closer; this is not a confidence probability). Collection metadata records embedding model, dimension, and schema version. Opening a mismatched collection raises an error.

| Input field | Stored value |
|---|---|
| `Medical_Term` | metadata `term` |
| `Lay_Language_Definition` | HTML removed for metadata `definition` and returned context |
| `Text_to_Embed` | Exact original Chroma document matching the supplied vector |
| `Embedding` | Supplied finite, nonzero 384-number vector |
| `Metadata.source` | Must equal `MedlinePlus` |
| `Metadata.url` | metadata `url` and `source_id` |

Metadata also includes `chunk_index=0`. Each supplied topic is one record; this code does not rechunk or regenerate embeddings. IDs are SHA-256 hashes of source URL, term, and embedded text. Repeating ingestion upserts the same IDs. If content changes, old IDs remain: use a new versioned collection for a new snapshot. The input includes a misspelled PLABA field `Lay_Language_Definiton`; it is not used here.

HTML cleanup is for presentation only. Some inputs are long topic summaries; MiniLM truncates inputs to its token limit, so full-document vectors can miss facts toward the end. Chunking and re-embedding should be a coordinated next step, not silently done during ingestion.

## Team interface

```python
from extractor.rag import retrieve, format_context
chunks = retrieve("hypertension", db_path="extractor/chroma_data", top_k=3)
context = format_context(chunks)
```

Each result contains `id`, `text`, `definition`, `metadata`, and `distance`. It is JSON-serializable; the CLI prints JSON. This September component retrieves supporting definitions. It does not generate a patient explanation or extract all clinical facts from a free-text report.

Rafi's existing `retrieval/chroma_retriever.py` calls `collection.query(query_texts=...)`. Use this wrapper so it embeds with matching MiniLM rather than Chroma's default model:

```python
from extractor.rag import TextQueryCollection
from retrieval.chroma_retriever import retrieve_context
chunks = retrieve_context(TextQueryCollection("extractor/chroma_data"), "hypertension", top_k=3)
```

Run this from the repository root. Share the database path, collection name, model name, and output schema with the Simplifier and Verifier owners. The wrapper leaves Rafi's file unchanged.

## Files and validation

- `extractor/rag.py`: current ingestion, validation, search, and retrieval handoff.
- `extractor/Extractor_Vector_Store.ipynb`: setup and walkthrough. Its four code cells were executed in a Python process and outputs saved; the original runtime blocked Jupyter kernel sockets.
- `extractor/PROJECT_CONTEXT.md`: role, findings, decisions, blockers, and session log.
- `extractor/requirements.txt`: the dependency versions recorded with this work. The repository-root `requirements.txt` is the project-wide dependency list.

The original handoff also described `VALIDATION.json`, `MTSAMPLES_EDA.md`, `SYNTHEA_EDA.md`, `fhir.py`, `synthea_audit.py`, `medaesqa_audit.py`, `extractor.py`, `examples/chunks.jsonl`, and an Extractor-specific `tests/` directory. Those files were **not included** in Vaibhavi's merged commit and are not present in this folder. The original validation and test claims below describe her earlier session, not checks reproduced by this README.

Keep raw datasets, embeddings, API keys, and Chroma files out of Git. This Extractor work is now part of the team repository.

## Repository placement

This README was restored from Vaibhavi's `3c25478` commit and placed beside her code in `extractor/`. The repository-root `README.md` remains the project overview. Keep the large embeddings on Drive or local storage; use the team's agreed branch/PR process for future changes.
