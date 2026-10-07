# September single-Gemini baseline

Owner: Zurabi. Implements the September portion of issue #5. The October ADK
scaffold remains separate. This baseline does one retrieval step and at most one
SDK generation call, with no agent loop or automatic prompt repair.

## Offline smoke test

From the repository root, with Python 3.10+:

```sh
python -m baseline --demo
python -m unittest discover -s tests -v
python -m unittest discover -s EDAs/MedAESQA -p 'test_*.py' -v
```

The demo uses a synthetic collection and a hard-coded response. Its model is
`offline-stub-not-gemini` and `demo` is true. It verifies plumbing only; do not
include it in benchmark results. The baseline and retrieval tests require only the
standard library; `tests/test_readability.py` also needs `pandas` and `textstat`
from the root requirements.

## Real integration

Real retrieval comes from Vaibhavi's MedlinePlus vector store in
[`extractor/`](../extractor/README.md): collection
`faithfulmed_medlineplus_minilm_v1`, built from Ruhma's embeddings with
`sentence-transformers/all-MiniLM-L6-v2` (384 dimensions). The Chroma database is
gitignored, so build it locally first. From the repository root, using Python
3.11 or 3.12:

```sh
python -m pip install -r extractor/requirements.txt google-genai
python -m extractor.rag ingest data/RAG_Embeddings_Full.jsonl --db extractor/chroma_data
python -m extractor.rag search "hypertension" --db extractor/chroma_data --top-k 3
```

The embeddings JSONL is shared outside the repository
(`data_pipeline/RAG_Embeddings_Full.jsonl` is an empty placeholder); put it in
`data/` or point the command at its location. Set `GEMINI_API_KEY` and
`GEMINI_MODEL` in your environment; do not put keys into source code. Select an
available text-generation model explicitly so model changes are deliberate.

Pass `extractor.rag.TextQueryCollection` as the collection. Rafi's
`retrieve_context` calls `query(query_texts=...)`, and this wrapper embeds those
query texts with the same MiniLM model as the stored vectors. Do not pass a raw
Chroma collection: it would not embed queries with MiniLM, so retrieval would
fail or return mismatched results.

```python
import os
from google import genai
from baseline import BaselineInput, GeminiGenerator, run_baseline
from extractor.rag import TextQueryCollection

def explain(clinical_text, example_id, retrieval_query=None):
    collection = TextQueryCollection("extractor/chroma_data")
    with genai.Client(api_key=os.environ["GEMINI_API_KEY"]) as client:
        return run_baseline(
            BaselineInput(example_id, clinical_text, retrieval_query),
            collection=collection,
            generator=GeminiGenerator(client, model=os.environ["GEMINI_MODEL"]),
            top_k=5,
        )
```

Through this wrapper, each chunk's `text` is the exact embedded document and its
`metadata` carries `term`, `url`, `source_id`, and a cleaned `definition`.

`GeminiGenerator` follows the [Google Gen AI Python SDK](https://googleapis.github.io/python-genai/)
`models.generate_content` interface. Clients are injected so callers control
credentials, transport timeout/retry settings, and lifecycle. A single SDK call
may involve transport retries configured on that client.

## Input/output task specification

Input `BaselineInput`:

| Field | Contract |
| --- | --- |
| `example_id` | Required nonblank string; use a stable ID across experiments. |
| `clinical_text` | Required nonblank, de-identified clinical plain text; preserve original facts. Flatten raw FHIR upstream. |
| `retrieval_query` | Optional nonblank query; defaults to the clinical text with outer whitespace stripped. |

`top_k` must be a positive integer. Optional `where` is forwarded to the shared
retrieval adapter as a Chroma metadata filter. Collection creation, ingestion,
embedding selection, and relevance thresholds remain the retrieval owner's work.

Output is a JSON-serializable dictionary:

| Field | Meaning |
| --- | --- |
| `schema_version` | `1.0` |
| `example_id`, `clinical_text`, `retrieval_query` | Input and exact retrieval query for audit. |
| `retrieved_context` | Ordered chunks with `id`, `text`, `metadata`, `distance`, using Rafi's existing adapter. |
| `model`, `prompt_version`, `top_k`, `where` | Generation/retrieval configuration identifiers. |
| `status` | `ok` for nonempty complete model text, or `no_context` when retrieval returns no usable text. |
| `model_output` | Patient-friendly explanation, or an empty string for `no_context`. |

`ok` is a technical completion status, not a faithfulness verdict. Retrieved
chunks are provenance, not verified citations. A model may produce a textual
refusal; Alicia's evaluation should classify it separately. `no_context` is a
retrieval failure category, not a model refusal. Invalid input raises `ValueError`;
retrieval/API failures propagate. Blocked, incomplete (including token-limit),
or empty Gemini responses raise `RuntimeError`; partial text is not accepted.

## Prompt and reproducibility

The system prompt requests short plain-language sentences and preserves clinical
facts, negations, uncertainty, doses, and follow-up instructions. Clinical text
and context are serialized as JSON data separate from system instructions.
That separation does not prove resistance to prompt injection or hallucinations.
The pipeline deliberately avoids a second refiner call, preserving the baseline.

Temperature is 0, candidate count is 1, and output budget is 4096 tokens. Control
flow is deterministic; hosted model outputs are not guaranteed byte-identical.
For comparisons, freeze the example set, collection snapshot, embedding model,
SDK version, Gemini model, and prompt version. Record these alongside exported
results. Context length depends on upstream chunk sizes and top_k; overlarge
requests fail rather than silently dropping clinical information.

## Evaluation handoff and remaining dependencies

Alicia can score `model_output` on `status == "ok"` records using her readability
harness, joining `example_id` to the source set (or mapping it to `question_id`
for the current notebook). Count retrieval/API failures separately instead of
scoring empty strings as easy-to-read answers. Rafi's rubric/manual assessment
is still needed to assess faithfulness.

Current status:

- `data_pipeline/RAG_Embeddings_Full.jsonl` is still an empty placeholder; get
  the embeddings file from Ruhma or Vaibhavi to build the index.
- The embedding model is settled on `all-MiniLM-L6-v2` for September (see the
  extractor README). `data_pipeline/README.md` still describes Gemini
  `text-embedding-004` and is stale. Moving to Gemini embeddings would need a new
  collection with document and query vectors regenerated together.
- The curated 50-report set is on main in
  [`data/curated_baseline/`](../data/curated_baseline/README.md) (v1-proposed,
  awaiting team freeze). Use its `source_row_id` as `example_id`. No benchmark
  results are claimed by this baseline.

Next: build the local index from the embeddings file, then do a quick test run
with real Gemini on a few curated reports (no patient-identifying data) through
`TextQueryCollection`. Once that works, run and evaluate the full agreed set.
