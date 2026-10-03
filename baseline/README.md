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
include it in benchmark results. Offline tests require only the standard library.

## Real integration

Install `google-genai` and the dependencies needed by the collection owner
(`chromadb` is already in the root requirements). Set `GEMINI_API_KEY` and
`GEMINI_MODEL` in your environment; do not put keys into source code. Select an
available text-generation model explicitly so model changes are deliberate.

```python
import os
from google import genai
from baseline import BaselineInput, GeminiGenerator, run_baseline

# Supply the existing populated Chroma collection from Vaibhavi.
# Its query embedding function MUST match ingestion's model and dimensions.
# Do not create a new empty collection or silently use Chroma's default embedding.
def explain(collection, clinical_text, example_id):
    with genai.Client(api_key=os.environ["GEMINI_API_KEY"]) as client:
        return run_baseline(
            BaselineInput(example_id=example_id, clinical_text=clinical_text),
            collection=collection,
            generator=GeminiGenerator(client, model=os.environ["GEMINI_MODEL"]),
            top_k=5,
        )
```

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

At the reviewed main revision (`b4c00cb`):

- `data_pipeline/RAG_Embeddings_Full.jsonl` is an empty placeholder.
- The data notebook embeds using `all-MiniLM-L6-v2`, while its README describes
  Gemini `text-embedding-004`. Resolve the ingestion/query model contract with
  Ruhma and Vaibhavi before using a real index.
- The curated 50-report set is in open PR #7, not yet on main. No benchmark
  results or dataset completeness are claimed by this baseline.

Next: obtain a populated collection with its matching query embedding function,
run a de-identified live Gemini smoke test, then evaluate the agreed frozen set.
