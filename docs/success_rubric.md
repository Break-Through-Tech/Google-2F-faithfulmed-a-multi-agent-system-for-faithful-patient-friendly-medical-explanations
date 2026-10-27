# FaithfulMed success rubric

Owner: Carlin Verano (original success rubric). Definitions updated October 27, 2026, using Samaneh's email and **Scoring Examples: Faithfulness, Omission, Addition, Hallucination**. Her examples clarify the units of scoring; numerical targets still come from the [overview](../Challenge-Project-Overview.md).

## Inputs and procedure

- Use the [frozen 50-report inputs](../data/curated_baseline/README.md), version `v3-medium-with-allergy-exceptions-frozen-2026-10-26`. Review and freeze are completed; source IDs/text remain unchanged.
- Score the baseline's `model_output` and ADK's released `final_answer` with the **same post-generation evaluator**, version `advisor-2026-10-27-v1`. Drafts may be scored separately; they are not silently substituted for missing final answers.
- Prepare one source-only key-fact inventory per report before scoring either answer. Save its version/hash and use it for both systems. Answers must not determine which source facts are important.
- Original notes are authoritative for patient facts. MedlinePlus can support explicitly general background, not new patient diagnoses, doses, or plans.
- See [the comparison protocol](../evaluation/COMPARISON_PROTOCOL.md) for counting rules, examples, denominators, and failure handling.

## Targets and definitions

| Metric | Definition | Project target |
| --- | --- | --- |
| Faithfulness | Supported claims / all output claims. Pool raw claim counts for the primary cohort score; also report average per-output score. | ≥85% factual fidelity using the documented procedure. |
| Hallucination rate | Outputs with at least one clinically meaningful unsupported claim / scored released outputs. Includes distortions. | <10%. |
| Omission | Important source facts missing from the output. Report missing/total key facts and affected outputs. | No numeric target specified. |
| Addition | Claims absent from the report; split supported background from unsupported additions. | No blanket ban or separate numeric target. |
| Distortion | An existing fact is changed: negation, certainty, number/unit, side, timing, or medication. | Report separately; meaningful unsupported distortions trigger hallucination. |
| Readability pass rate | FK grade ≤8, any configured word limit, and the scorer's non-refusal check. | ≥80% of outputs. |
| Improvement over baseline | Multi-agent faithfulness minus baseline faithfulness on the same matched cases. | ≥15 percentage points. |
| Verifier agreement | Agreement with existing MedAESQA reference support labels, with kappa and sample counts. | ≥80% agreement and Cohen's κ ≥0.6. |

An answer can have 100% claim faithfulness and still omit follow-up. A supported background addition can be acceptable. A distortion can trigger hallucination with no added claim. These are separate measurements.

## Clinically meaningful errors

Examples include no becoming yes, possible becoming definite, pending becoming completed, a wrong dose/number/unit or side, and an invented diagnosis/procedure/medication plan. Missing important follow-up is a clinically meaningful **omission**; absence alone does not create an unsupported output claim.

Source conflicts are documented in the [report review notes](../data/curated_baseline/REVIEW_AND_FREEZE.md). Preserve uncertainty instead of inventing a correction. A mere wording difference is not automatically a clinical error.

## Readability

The active scorer is [`evaluation/readability.py`](../evaluation/readability.py), called by [Alicia's wrapper](../faithfulmed_demo/roles/readability.py).

- Primary: FK grade ≤8. Lower grades indicate simpler wording, not better factual support.
- Secondary: SMOG, medical-word-list jargon density, word/sentence counts, and refusal rate. SMOG is empty below three sentences; no SMOG/jargon pass threshold is specified.
- Defaults: `max_grade=8`, `max_words=None` (no word limit). A refusal cannot pass.
- `status: ok` means text was measured; `readability_status: passed` is the wrapper's decision.
- Do not mix the older starter harness's different sentence/jargon calculations with the active scorer's numbers.

## Demo findings versus evaluation scores

The live Verifier returns `issues`, `supported_examples`, and `scope`. Its examples are not a full claim inventory and cannot supply the faithfulness denominator. The Refiner still consumes those existing issues; the new evaluation leaves that handoff intact.

[`evaluation/scoring.py`](../evaluation/scoring.py) and [the scoring runner](../evaluation/score_outputs.py) request all output claims, fixed-key-fact coverage, and evidence. Code validates quotes/IDs and calculates the metrics. The judge still makes semantic support/segmentation decisions; quote matching alone does not prove them correct.

## Calibration and reporting

Use the [MedAESQA procedure](../evaluation/CALIBRATION.md) for the evidence-support portion. It compares evidence-support judgments with existing supporting, neutral, and contradicting labels. The initial pilot used citation excerpts; the [scope investigation](../evaluation/CALIBRATION_INVESTIGATION.md) found that the references apply to cited titles/abstracts. Document-level context and conflicting reference labels still need a fixed policy before continuing calibration. The test does not measure report omissions or whole-answer accuracy.

Show raw counts, case IDs, model/prompt/input versions, failures/refusals, and denominators. With 50 scored outputs, one output changes an output-level rate by two percentage points; with five, by twenty. Wilson intervals accompany output-level hallucination rates; pilot results remain directional.

Empty answers, no-context runs, API failures, and judge failures stay visible and never become perfect-faithfulness answers. Completed scores of released outputs enter principal quality rates; report completion coverage alongside them. A synthetic smoke run is not a baseline-improvement measurement.
