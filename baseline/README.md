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

## Real MedlinePlus integration

The current source is the cleaned, chunked MedlinePlus collection described in
[the MiniLM handoff](../data_pipeline/MINILM_MEDLINEPLUS.md). It contains all
6,883 chunks from 1,979 topics. The Gemini **embedding** collection is still
incomplete; the baseline can use MiniLM to search locally and Gemini to write
its one explanation. The two embedding models have separate Chroma collections.

Download the verified MiniLM ZIP from the team's shared Drive folder **Google 2F -
Faithfulmed / MedlinePlus MiniLM Index**, extract it to `data/MedLineGlossary/`,
and follow the handoff's `status` command. The Chroma files and generated output
are ignored by Git. Do not send identifying patient information to the API.

From the repository root, install the retrieval and generation dependencies:

```powershell
python -m pip install -r data_pipeline/requirements-minilm.txt
python -m pip install -r data_pipeline/requirements-gemini.txt
```

Put your key in the ignored root `.env` file as `GEMINI_API_KEY=...`, or set the
environment variable. Choose an available **text-generation** model explicitly;
this tested run used `gemini-3.8-flash`. The new runner takes one JSON input with
`example_id`, `clinical_text`, and optional `retrieval_query`, then saves the
baseline's evaluation-ready JSON output:

```powershell
python -m retrieval.minilm_chroma status
python -m baseline.run_medlineplus --input baseline/examples/synthetic_chest_pain.json --output data/baseline_results/chest_pain.json --model gemini-3.8-flash
```

On Windows, replace `python` with `.\.venv\Scripts\python.exe` if the virtual
environment is not activated. The second synthetic example is
`baseline/examples/synthetic_low_glucose.json`. The output includes the query,
retrieved text and MedlinePlus URLs, Gemini model, prompt version, and MiniLM
collection/model/source hash. A successful `status: ok` means the code completed;
it is **not** a clinical or faithfulness verdict. Keep the same model and index
snapshot across examples intended for comparison.

The older `extractor/rag.py` collection is a separate September handoff. This
runner uses `retrieval.minilm_chroma.MiniLMTextQueryCollection` to embed queries
with the same model as the current chunked index, then passes the results to
`run_baseline`. After the Gemini embedding collection is complete and checked,
its query wrapper can replace MiniLM without changing the baseline generator.

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

Current status (October 14, 2026):

- The real baseline ran end-to-end with the complete local MiniLM MedlinePlus
  index and Gemini `gemini-3.8-flash` on two synthetic, de-identified notes.
  Both returned `status: ok` with three retrieved chunks and saved JSON results
  under the ignored `data/baseline_results/` folder.
- In the chest-pain smoke test, the first prompt added an unsupported detail
  about how a stress test worked. Prompt version `medlineplus-baseline-v3`
  stopped that addition in a repeat run while retaining the negative heart-attack
  finding, pending test result, uncertain liver finding, and follow-up timing.
- For the low-blood-sugar note, a broad query returned Spanish diabetes pages.
  A focused query using terms from the note returned English Blood Glucose and
  Hypoglycemia pages; Gemini retained the 84-to-60-unit history, hold tonight,
  55-unit morning dose, and next-week review. This is a retrieval-quality warning,
  not proof the query strategy works across all reports.
- Alicia's local readability scorer gave the two final smoke outputs
  Flesch-Kincaid grades of **5.47** and **6.97**; neither was flagged as a
  refusal. These numbers describe only those outputs, not baseline performance.
- The proposed 50-report source set still needs team review and freezing.
  Neither these two smoke tests nor `status: ok` are benchmark or clinical
  validation. A full scored comparison, Verifier calibration, and the multi-agent
  Refiner loop remain later work.
