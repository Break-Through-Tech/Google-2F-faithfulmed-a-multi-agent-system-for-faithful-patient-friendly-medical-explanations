# Advisor scoring checks - October 27, 2026

The four explicit reference cases passed offline. A separate live Gemini check also completed all four cases and matched the advisor example counts.

Generation/judge model: gemini-3.8-flash. Protocol: advisor-2026-10-27-v1.

| Case | Supported / claims | Omissions / key facts | Additions | Distortions | Hallucination |
| --- | --- | --- | --- | --- | --- |
| A | 7 / 7 | 0 / 5 | 1 | 0 | No |
| B | 4 / 4 | 1 / 5 | 0 | 0 | No |
| C | 5 / 6 | 0 / 5 | 1 | 0 | Yes |
| D | 3 / 5 | 1 / 5 | 0 | 2 | Yes |

These are four illustrative synthetic outputs, not a measurement on the frozen 50 reports or MedAESQA calibration. The background passage follows the support assumed in the supplied PDF.

All **79 local tests passed**, including the existing ADK/Refiner workflow, frozen-set safeguards, new scoring rules, isolated calibration splits, hidden reference labels, and resume behavior. The frozen 50-report snapshot also verified against the original corpus without changes.

## Local evidence

- data/scoring_results/advisor_reference_final_v1.json: reference-annotation checks, not model predictions.
- data/scoring_results/advisor_live_v2.json: saved live judgments and original metrics.
- data/scoring_results/advisor_live_checked_v1.json: the same live judgments checked with final metric calculations; no additional model call.
- data/calibration_results/medaesqa_support_v1.json: prepared development/held-out suite.
- [Calibration selection manifest](calibration_selection_manifest.json): dataset hash, split groups, exclusions, and selected case IDs without raw dataset text.

An initial sandbox connection failure and Developer API schema failures are retained in earlier local attempt files. Schema transport was corrected to omit unsupported additionalProperties while preserving strict local parsing. The configured key/model passed a harmless connectivity check.

## Remaining execution

After explicit authorization, a six-case MedAESQA development pilot completed with **50% agreement (3/6), kappa 0.00**, and no API failures. All predictions were non-supporting. See [the pilot findings](CALIBRATION_PILOT.md). The remaining 34 development and all 40 held-out cases are unscored; inspect the disagreement pattern before further runs. The existing ADK demo and Refiner schema are unchanged.

## Context investigation

The [completed scope investigation](CALIBRATION_INVESTIGATION.md) used the same six cases with full cited titles/abstracts and unchanged labels/model/prompt. Agreement became **66.7% (4/6), kappa 0.33**. All three original false negatives were resolved, but two reference disagreements remained in document/sentence groups with mixed labels. No cases were dropped or relabeled. These development diagnostics do not complete held-out calibration or establish the project targets.

After the context changes, **all 91 local tests passed**, including 12 context/parser/provenance checks. The frozen 50-report snapshot verified unchanged against the original corpus.
