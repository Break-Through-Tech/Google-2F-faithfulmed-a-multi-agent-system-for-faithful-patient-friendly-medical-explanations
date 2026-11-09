# Running the baseline and ADK comparison

`evaluation/run_comparison.py` runs the single-Gemini baseline and the ADK pipeline on the same frozen reports. It saves one record per report and system, so the answers can be scored later. It calls the existing code and does not change how either system works.

**Status:** the first five-report live pilot generated both systems' texts, but all
five ADK outputs remained drafts above the readability target. A subsequent
[bounded readability rewrite and rerun](READABILITY_REWRITE_PILOT.md) released four
ADK answers and held one candidate for review. See [the original pilot run record](FIVE_REPORT_PILOT.md)
for the earlier results and scoring limits; the new run retains its own failures.

## What it does

1. Confirms the frozen reports are unchanged, using `evaluation/validate_frozen_set.py`, and validates the requested report IDs.
2. Gives both systems the full report text as the note and as the search query, with `top_k` 3 and the same Gemini index.
3. Saves the results file after every call, so stopping partway loses at most the call in progress.
4. On a rerun, skips finished records. Failed records run again only if you add `--retry-errors`, and earlier failures are kept in the record's `attempts` list.
5. Stops the batch on a service access or quota error (codes 400, 401, 403, 404 and 429). Saved records are kept, so you can resume later.

## Before a live run

- Put `GEMINI_API_KEY=...` in the root `.env` file.
- Set up the Gemini index in `data/MedLineGlossary/chroma_gemini_2`, following `data_pipeline/GEMINI_MEDLINEPLUS.md`. The ZIP was made on Windows, so check that the extracted files are in real folders on a Mac. The runner stops with a clear message if the index is missing.
- Have `data/curated_baseline/mtsamples_curated_50.csv` in place. It is not stored in Git.

A live run uses your API quota. ADK makes several model calls per report, while the baseline makes one.

## Mac / zsh

Run these from the repository root.

Try the whole flow with scripted answers and no API calls:

```zsh
.venv/bin/python -m evaluation.run_comparison --offline
```

Run one pair, which is the first pilot report on both systems:

```zsh
.venv/bin/python -m evaluation.run_comparison --limit 2
```

Check that record, then run all five. The finished pair is skipped:

```zsh
.venv/bin/python -m evaluation.run_comparison
```

Resume after an interruption by running the same command again. To run failed records again:

```zsh
.venv/bin/python -m evaluation.run_comparison --retry-errors
```

## Windows PowerShell

```powershell
.\.venv\Scripts\python.exe -m evaluation.run_comparison --offline
.\.venv\Scripts\python.exe -m evaluation.run_comparison --limit 2
.\.venv\Scripts\python.exe -m evaluation.run_comparison
.\.venv\Scripts\python.exe -m evaluation.run_comparison --retry-errors
```

## Options

| Option | Meaning |
| --- | --- |
| `--ids` | JSON file listing the reports. Default: `evaluation/pilot_ids.json`. It needs `pilot_version`, `frozen_set_version` and `source_row_ids`. |
| `--systems` | `baseline`, `adk`, or both. Default: both. |
| `--model` | Generation model for both systems. Default: `gemini-3.8-flash`. |
| `--output` | Results file. Default: `data/comparison_results/<pilot_version>.json`. |
| `--limit` | Maximum generation calls in this run. Two calls make one pair. |
| `--retry-errors` | Run failed records again. |
| `--offline` | Scripted answers and no API calls. Default output ends in `-offline.json`. |
| `--export-scoring` | Do not generate. Convert saved results for the evaluator; see below. |
| `--key-facts-dir` | Folder of key-fact files, used with `--export-scoring`. |

## What offline mode does

Offline mode runs the real report text through the real workflow, with scripted stand-ins for every outside call. It does not use the demo's `/offline` messages, which always run a synthetic chest-pain note instead of the report.

| Part | Offline stand-in |
| --- | --- |
| Baseline search and generation | A fake collection and a fake generator |
| ADK Extractor | A scripted model that quotes the start of the report; ADK still parses the output and the real quote check still runs |
| ADK retrieval, Simplifier and Verifier | Scripted results, in place only during the offline call |
| ADK Refiner and readability, and the baseline's own logic | The real code |

Every offline record has `mode: offline-scripted` and the model `offline-stub-not-gemini`. The answers and passages are scripted, so offline results say nothing about quality and cannot be exported for scoring. ADK's own state and messages in a trace still say live because it ran its live path, so the trace's `runner_mode` and `note` fields record that the calls were scripted.

## Where results go

Everything under `data/comparison_results/` is ignored by Git.

- **Results file:** `data/comparison_results/<pilot_version>.json`, with a `records` list and a `retrieval_comparison` list. Each record saves the report it ran on in `source_text`.
- **ADK traces:** `data/comparison_results/traces/`, with one file per attempt holding the full session state and events. A record's `trace_path` names its file.

## Reading a record

| `status` | System | `output_kind` | Meaning |
| --- | --- | --- | --- |
| `ok` | Baseline | `final_answer` | The model finished and returned text. This is not a faithfulness verdict. |
| `complete` | ADK | `final_answer` | ADK released a final answer. |
| `needs_review` | ADK | `needs_review_draft` | Verifier findings are unresolved. The text is a draft. |
| `needs_simplification` | ADK | `needs_review_draft` | No findings remain, but the text missed the readability target, so ADK did not release it. The text is a draft. |
| `no_context` | Baseline | none | Retrieval returned nothing, so no answer was generated. |
| `failed` | ADK | none | A stage stopped. The reason is in `error`. |
| `error` | Either | none | The run failed, or ADK ended without usable text. The reason is in `error`. |

`no_context`, `failed` and `error` can be retried with `--retry-errors`. Every other status counts as finished.

**Checking retrieval:** each `retrieval_comparison` entry says `match`, `mismatch` or `not_comparable` for one report. `match` means the same query, `top_k` and passages in the same order. `not_comparable` means at least one system saved no passages. Investigate any `mismatch` before scoring. Each record also keeps its query and passages.

**Token counts:** `token_usage` is complete for the baseline's generation call. For ADK it covers the Extractor only, because the Simplifier and Verifier calls do not report tokens through ADK events. Neither system's count includes embedding the search query.

## When settings change

A record's key combines the report, system, model and settings. The settings include the frozen set, pilot version, search rule, `top_k`, index and a fingerprint of the prompt code. Changing any of these adds a new record, and old records are never overwritten.

The fingerprint comes from the source files, so any edit to them counts as a change, even to a comment. If you change settings on purpose, use a new `--output` path for that run. Scoring refuses a results file that holds more than one group of settings for the same report, system and model.

For a different model, run the command again in a new process with `--model`. ADK reads its model once when it loads, and the runner stops if the loaded model is not the one you asked for.

For all 50 reports, make a new ID file with its own `pilot_version` and all 50 `source_row_ids`, then pass it with `--ids`. Keep the five pilot records out of that file's results by leaving the default output path in place, which is named after the `pilot_version`.

## Passing results to the evaluator

`evaluation/score_outputs.py` needs the same source-only key facts for both systems, prepared before anyone reads the answers. Prepare one file per report with `--prepare-source` (see `COMPARISON_PROTOCOL.md`) and save them as `source_row_<id>.json` in one folder. The export checks that each file was prepared from the exact frozen text.

Mac / zsh:

```zsh
.venv/bin/python -m evaluation.run_comparison --export-scoring data/comparison_results/scoring_inputs.json --key-facts-dir data/scoring_results/key_facts
.venv/bin/python -m evaluation.score_outputs --input data/comparison_results/scoring_inputs.json --output data/scoring_results/comparison_v1.json --limit 2
```

Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -m evaluation.run_comparison --export-scoring data/comparison_results/scoring_inputs.json --key-facts-dir data/scoring_results/key_facts
.\.venv\Scripts\python.exe -m evaluation.score_outputs --input data/comparison_results/scoring_inputs.json --output data/scoring_results/comparison_v1.json --limit 2
```

Add `--output` to the export command if your results are not at the default path. Scoring makes live model calls, so `--limit 2` starts with one pair. Remove it to continue.

The export changes these labels to the ones the evaluator expects:

| Runner | Evaluator |
| --- | --- |
| `output_kind: final_answer` | `output_kind: final` |
| `output_kind: needs_review_draft` | `output_kind: draft`, which is left out of released-answer summaries |
| Failed run, with no output | `output_kind: final` and empty text, which the evaluator counts as `generation_failed` rather than dropping |
| `status` | `run_status` |
| `output_text` | `output` |

## Tests

```zsh
.venv/bin/python -m pip install pytest
.venv/bin/python -m pytest
```

`tests/test_run_comparison.py` makes no API calls. Its one real-data check is skipped if the frozen CSV is not present.
