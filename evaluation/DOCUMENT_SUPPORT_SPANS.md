# Numbered evidence passages for the development judge

Version `document-support-spans-2026-11-07-v4` replaces model-generated source quotations with source passage IDs. This implements the evidence-copying fix from the [v3 investigation](DOCUMENT_SUPPORT_V3_INVESTIGATION.md).

Python divides the unchanged title and abstract into ordered passages such as `E001` and `E002`. Every passage retains its exact text and start/end character offsets. Whitespace, punctuation, and Unicode are preserved. Splits are mechanical and can occur around abbreviations; all source text and order remain available, and the judge can select multiple adjacent IDs for context.

The model returns `evidence_span_ids` for each proposition. Python verifies the IDs and retrieves their exact text into the saved `evidence_spans` records. Supported or contradicted propositions require at least one valid ID. Unknown, repeated, or missing required IDs fail validation. Model-provided source quotations are not accepted as a substitute. The answer's `sentence_quote` is still checked verbatim and can still fail if copied incorrectly.

The existing rules for partial support, uncertainty, causal limits, and technical paraphrases remain. A valid passage ID does not prove that it supports a claim, and passage copying does not validate the proposition inventory. The clinical-report scorer and live ADK Verifier are not changed.

## Local preparation

The prepared suite is `data/calibration_results/medaesqa_document_development_v4_spans.json`: the same 40 development cases, including 26 eligible and 14 quarantined reference-ambiguous cases. The runner sends only eligible cases with complete context. Reference labels and audit decisions are not included in the judge payload. No held-out cases or predictions are added.

Reproduce offline using a fresh output path:

```powershell
.\.venv\Scripts\python.exe -m evaluation.calibrate_support_spans prepare --suite data/calibration_results/medaesqa_document_development_v2_full.json --output data/calibration_results/development_v4_spans_reproduction.json
```

The suite and results are local generated files. New suite/model/prompt/schema settings require a new results path. Previous v2/v3 scores and failed attempts remain in their original files.

## Future development check

This command calls Gemini. A subsequent [six-case development check and two-case targeted engineering check](DOCUMENT_SUPPORT_V4_RUN.md) completed with valid passage IDs in all eight attempted cases. Reference agreement still fell below the project goals.

```powershell
.\.venv\Scripts\python.exe -m evaluation.calibrate_support_spans run --suite data/calibration_results/medaesqa_document_development_v4_spans.json --output data/calibration_results/document_support_v4_development.json --model gemini-3.8-flash --limit 6
```

Results save the selected IDs and source text/offsets. Failed attempts retain safe error stages and categories. Resume saves completed cases, and `--retry-errors` keeps failed attempts in the history. Reference agreement and coverage diagnostics remain separate; no accuracy improvement is established by the local implementation tests.
