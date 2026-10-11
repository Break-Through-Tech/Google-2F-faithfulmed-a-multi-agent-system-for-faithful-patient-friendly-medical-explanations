# MedlinePlus MiniLM index

This temporary local retrieval index uses the same cleaned MedlinePlus chunks
as the Gemini build. It lets the team work while Gemini's daily quota delays
that build. It is separate from both the partial Gemini collection and the
older 1,015-record September MiniLM collection.

## Build and search

Run from the repository root. On Windows, use `.venv\Scripts\python.exe` instead
of `python` if the virtual environment is not activated.

```powershell
python -m pip install -r data_pipeline/requirements-minilm.txt
python -m retrieval.minilm_chroma ingest
python -m retrieval.minilm_chroma status
python -m retrieval.minilm_chroma search "high blood pressure"
```

The input is `data/MedLineGlossary/medlineplus_chunks_800.jsonl`: 6,883 chunks
from 1,979 topics (1,002 English and 977 Spanish, matched to the source XML).
If it is missing, first run the cleaned export and chunking
commands in [the data preparation instructions](GEMINI_MEDLINEPLUS.md).
The builder skips existing IDs when resumed and rejects a changed source file.
`status` checks that the stored IDs exactly match the chunk file.

Model: `sentence-transformers/all-MiniLM-L6-v2`, revision
`1110a243fdf4706b3f48f1d95db1a4f5529b4d41`, 384 dimensions. The first use downloads
the model to the ignored `data/MedLineGlossary/model_cache/` directory. Embedding
and search then run locally on CPU without a Gemini key. To force cached-only
operation, set `HF_HUB_OFFLINE=1` before starting Python.

Collection: `faithfulmed_medlineplus_minilm_chunks_384_v1`.
Database folder: `data/MedLineGlossary/chroma_minilm_chunks/`.
Document input is the topic title, a newline, and the unchanged chunk text.
Vectors are normalized and searched by cosine distance (smaller is closer,
not a confidence score). Inputs exceeding the model's 256-token limit are split
at whitespace into token-bounded windows. Their normalized vectors are averaged
with token-count weights and normalized again, retaining one vector per original
chunk. The same rule applies to long queries. This avoids silently discarding
the ends of chunks; it does not change the stored chunk text or IDs.
For this snapshot, 1,085 inputs need two windows: 7,968 embedding windows
produce 6,883 stored vectors. All input words are preserved.
The database records the model revision, chunk rule, and input SHA-256.

## Use Rafi's retrieval function

```python
from retrieval import retrieve_context
from retrieval.minilm_chroma import MiniLMTextQueryCollection

collection = MiniLMTextQueryCollection()
results = retrieve_context(collection, "high blood pressure", top_k=3)
```

Keep this wrapper alive across searches so the model is loaded only once.
Results contain `id`, `text`, `metadata`, and `distance`. Metadata includes
`source`, `source_id`, `source_url`, `term`, `chunk_index`, and `chunk_count`.
No-result filters and empty queries return an empty list. This is retrieval
integration; it does not implement the Simplifier or Verifier agents.

## Build validation

The completed local build contains all 6,883 expected IDs, with no missing or
unexpected records. Stored text and source metadata match the chunk export;
all vectors are finite, normalized, and 384-dimensional. Re-running ingestion
adds zero records. The focused MiniLM, Gemini, and retrieval tests pass (12 tests).

Fresh-process, offline searches for high blood pressure, kidney stones, asthma,
A1C, and Zika returned relevant topics in the top three. Spanish searches for
high blood pressure and asthma also returned matching topics, but
`cálculos renales` did not retrieve kidney stones in the top three. This is a
known limitation of this temporary English-model index, not validated bilingual
retrieval. Detailed records are in `data/MedLineGlossary/minilm_validation.json`.

## Sharing and the later Gemini switch

The team's shared Google Drive folder **Google 2F - Faithfulmed / MedlinePlus
MiniLM Index** contains `medlineplus_minilm_chunks_v1.zip` and
`medlineplus_minilm_chunks_v1.zip.sha256`. Teammates should download both files
after receiving the matching code through the team's PR. On Windows, run
`Get-FileHash -Algorithm SHA256 medlineplus_minilm_chunks_v1.zip` and compare
its hash with the first value in the `.zip.sha256` file. Extract the ZIP into
`data/MedLineGlossary/` on local disk, then install
`data_pipeline/requirements-minilm.txt` and run the `status` and `search`
commands above. Do not run the live Chroma database inside a synced Drive folder.

The ZIP includes the database, chunk JSONL, validation report, and version
manifest; it excludes API keys and model weights. The checksum file is
only a fingerprint of the ZIP and does not need to be extracted.
The local handoff archive is `data/MedLineGlossary/medlineplus_minilm_chunks_v1.zip`.
The archive was verified by extracting it into a separate directory, checking
all manifest hashes, reopening all 6,883 records, and searching the copy offline.

The shared ZIP is a snapshot, not a hosted Chroma server. Each teammate needs
their own local copy and must download the matching MiniLM model once. The ZIP
includes the chunk JSONL used by the `status` check, so teammates do not need
to regenerate document vectors.

The database, chunks, model cache, and keys are ignored by Git. Commit the code
and instructions through a reviewed PR; distribute the snapshot through Drive.
The full team-agent integration is still pending.

Resume Gemini separately using [its instructions](GEMINI_MEDLINEPLUS.md).
Once its index is complete, check retrieval quality before selecting its
collection and query embedder. Never query MiniLM vectors with Gemini vectors.

MiniLM is an English general-purpose model; source text in other languages and
specialist medical queries need explicit review. A few smoke searches establish
that retrieval works, not clinical accuracy or overall retrieval quality.
[Model documentation](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2).
