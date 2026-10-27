# Comparing baseline and ADK outputs

Protocol: **advisor-2026-10-27-v1**, October 27, 2026. This implements the definitions in Samaneh's reply and supplied scoring examples.

## What stays fixed

Use frozen version `v3-medium-with-allergy-exceptions-frozen-2026-10-26`; run the freeze validator first. Preserve IDs/text. Compare the same generation model, retrieval snapshot, top-k/query rule, and recorded settings. Save actual retrieved passages. Ruhma and Carlin own consistent retrieval and paired generation; this evaluator can already score saved answers independently.

Prepare important source facts **before seeing either answer**. Keep the same fact list/IDs for both systems, with exact source quotes and a digest. Existing source-review notes explain caveats; they are not automatically a complete key-fact inventory. Include important findings, negation, pending results, medication changes, and follow-up rather than every routine normal detail. If the inventory changes, version it and rescore both systems.

## Claims and evidence

One claim is an independently checkable proposition. Split independent diagnoses, conclusions, and proposed treatments. Keep number/unit/laterality attached to the underlying measured fact. A separate inference such as “this means pulmonary hypertension” is another claim. Repeated identical propositions do not earn extra support points. Headings, greetings, citation formatting, and list markers are not claims.

Request every claim, with a verbatim output span, support decision, evidence references, addition flag, distortion types, clinical significance, and reason. Quote validation prevents invented anchors; semantic completeness of the inventory remains a judge behavior to test.

The report supports patient facts. Retrieved MedlinePlus passages can support explicitly general background; they cannot establish a new patient diagnosis or plan. Preserve uncertainty and source conflicts. Extractor atoms cannot replace the full source when judging omissions.

## Calculations

| Measure | Rule |
| --- | --- |
| Per-output faithfulness | `claims_supported / claims_total`. No claims means no score, not 100%. |
| Cohort faithfulness, primary (micro) | Sum supported claims / sum all claims over scored final outputs. |
| Cohort faithfulness, secondary (macro) | Mean per-output faithfulness; report separately. |
| Omissions | Count fixed important facts marked missing; also report total key facts and affected outputs. |
| Additions | Claims absent from the report; split supported background and unsupported additions. |
| Distortions | Changed existing facts; not also additions. A present-but-distorted fact is not also missing. |
| Hallucination | At least one clinically meaningful unsupported claim, including meaningful distortions. |
| Hallucination rate | Flagged outputs / scored final outputs, with raw counts and a 95% Wilson interval. |

A missing follow-up is an omission, not by itself a hallucinated assertion. Inventing a different interval is a distortion. Clinically meaningful errors include negation/hedge flips, pending-to-completed changes, wrong dose/measurement/unit/side, and invented diagnosis or treatment plans. Do not equate a missing citation with a false patient statement.

## Advisor reference checks

| Example | Supported / claims | Missing / key facts | Additions | Distorted claims | Hallucination |
| --- | --- | --- | --- | --- | --- |
| A: complete plus supported background | 7 / 7 | 0 / 5 | 1 supported | 0 | No |
| B: truthful, missing follow-up | 4 / 4 | 1 / 5 | 0 | 0 | No |
| C: invented biopsy plan | 5 / 6 | 0 / 5 | 1 unsupported | 0 | Yes |
| D: strengthened diagnosis and wrong size | 3 / 5 | 1 / 5 | 0 | 2 | Yes |

These reference annotations test intended distinctions and arithmetic; they are not predictions. The fixture background quote represents support assumed in the high-level PDF, not a newly fetched MedlinePlus passage. Report live judgments separately.

## Commands and input records

Use the same post-generation evaluator on both systems' final text. Evaluation calls do not change baseline generation into an agent pipeline. Keep ADK internal verdicts/repair history as separate trace information.

Offline reference checks:

```powershell
.\.venv\Scripts\python.exe -m evaluation.score_outputs --advisor-examples --output data/scoring_results/advisor_reference_final_v1.json
```

For live example checks, add `--live` and choose a different output path. Expected assessments are never sent to the judge.

Normal input is one JSON record or an object with a `records` list:

```json
{
  "case_id": "source-row-0",
  "system": "baseline",
  "generation_model": "the-recorded-model-id",
  "output_kind": "final",
  "run_status": "ok",
  "source_report": "the unchanged note",
  "key_facts": [{"id": "K1", "text": "an important fact", "source_quote": "exact original words"}],
  "retrieved_context": [{"id": "chunk-id", "text": "actual retrieved passage"}],
  "output": "the saved answer"
}
```

```powershell
.\.venv\Scripts\python.exe -m evaluation.score_outputs --input data/comparison_results/scoring_inputs.json --output data/scoring_results/comparison_v1.json --limit 5
```

The runner saves each attempt and resumes unfinished jobs with matching settings. Changed inputs/model/prompt require a new output path. Errors remain recorded; use a new path for a deliberate new evaluation attempt. Results include input digests, claim details, counts, readability, mode, judge model, and evaluation time. Summaries are grouped by system/generation model.

To prepare facts independently, provide JSON containing `source_report`:

```powershell
.\.venv\Scripts\python.exe -m evaluation.score_outputs --prepare-source data/source_input.json --output data/scoring_results/source_facts_v1.json
```

This makes a model call and refuses to replace an existing inventory. Save/reuse the facts for both systems. Fact extraction needs its own spot checks before omission counts can be interpreted as exhaustive.

## Failures and uncertainty

- Report attempted generations, released answers, successfully scored answers, drafts, refusals, and failures separately. Empty/failed responses never get faithfulness 100%.
- An unreleased text must use `output_kind: draft`; draft scores are excluded from released-output summaries. Preserve its generation status.
- Use Alicia's active readability scorer with identical thresholds/word-limit settings. Do not mix the older harness's calculations into the comparison.
- Show supported/total claims, missing/total key facts, additions by type, and hallucinated/total outputs. An empty internal `issues` list cannot replace a claim-level score.
- Report matched cases and completion coverage; disclose failed pairs instead of selecting only successes.
- Wilson intervals describe output flags. Claims within one answer are correlated; do not treat all claims as independent patients for a confidence interval. A five-case pilot does not establish project targets.

## Status

The schema, reference cases, arithmetic, and calibration preparation are implemented. The evaluator is ready for saved pilot outputs. See [CALIBRATION.md](CALIBRATION.md) for the support-calibration scope and commands. Paired report generation and the shared retrieval rule remain parallel teammate work.

The MedAESQA [scope investigation](CALIBRATION_INVESTIGATION.md) found that document reference labels must not be equated silently with short-snippet judgments. The six-case title/abstract diagnostic reached 66.7% agreement and kappa 0.33, with mixed document-level references still unresolved. This does not change the advisor's clinical-report scoring formulas or establish final calibration.
