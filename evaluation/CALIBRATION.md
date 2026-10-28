# Verifier evidence-support calibration

Version: **medaesqa-support-2026-10-27-v1**. This is the original snippet-input support pilot. The subsequent [scope investigation](CALIBRATION_INVESTIGATION.md) found that the reference labels are defined at cited-document title/abstract level. Treat v1 results as a snippet proxy, not completed document-level calibration. A medical question is not substituted for a clinical source note.

## Actual dataset and mapping

Input: `data/MedAESQA_data/medaesqa_v1.json`. Its 40 questions have `machine_generated_answers`, `answer_sentences`, and `citation_assessment` records; citations provide `evidence_support` and `evidence_relation`.

| Relation | Binary target | Treatment |
| --- | --- | --- |
| supporting | True | Include with nonblank excerpt. |
| neutral | False | Include with nonblank excerpt. |
| contradicting | False | Include with nonblank excerpt. |
| not relevant | False in principle | All 1,551 local records lack excerpts; exclude from this text task. |
| invalid citation | Separate validity task | Exclude all 409 records; a PMID alone cannot establish validity/support. |

The 9,611 citation records contain 6,490 supporting, 972 neutral, 189 contradicting, 1,551 not-relevant, and 409 invalid-citation relations. Preparation excludes 110 records from duplicate pairs with conflicting binary references and collapses 714 further repeated records. Repetition across machine answers must not inflate agreement.

This does not measure whole-answer accuracy, clinical-note omissions, or every live Verifier behavior. A sentence can cite several papers: one pair asks whether one excerpt supports the assertion for which it is cited. The checker shares evidence/uncertainty rules with the final-output scorer but uses this task-specific input shape.

## Fixed suite

Dataset SHA-256: `a062742c1678b4379121ad030a06bda574afd376f331df41575938dd9849c383`.

- Seed 42 assigns 20 questions to development and 20 to held-out evaluation. No question is in both.
- Duplicate identity uses question, sentence with numeric citation markers removed, and excerpt with whitespace normalized. Conflicting binary references are excluded.
- Default sample: 20 supported and 20 non-supported pairs per split: **40 development and 40 held-out cases**. This deterministic balanced sample is diagnostic, not a prevalence estimate.
- Eligible unique development pairs: 2,818 supported/539 non-supported; held-out: 2,923/547. The suite records selected IDs, groups, exclusions, and source hash.
- Only question, sentence, and excerpt reach the judge. Reference labels, expected scores, original answer-model names, and record IDs stay out of the prompt.
- Use development cases for prompt checks; hold settings fixed before evaluating held-out cases.

## Commands

Prepare without an API request:

```powershell
.\.venv\Scripts\python.exe -m evaluation.calibrate_verifier prepare --output data/calibration_results/medaesqa_support_v1.json
```

The suite is already prepared locally. The command refuses to replace it; a deliberate reselection needs a new path/version.

Run or continue a bounded development pilot (the first six cases are already completed):

```powershell
.\.venv\Scripts\python.exe -m evaluation.calibrate_verifier run --suite data/calibration_results/medaesqa_support_v1.json --output data/calibration_results/development_v1.json --split development --limit 6
```

Rerun to continue unfinished cases. Use `--retry-errors` to retry failures while retaining attempt history. Only the latest attempt per case enters the summary. Changed model/prompt/suite requires a new output path. The ignored root `.env` already supplies the key configuration.

After development and fixing settings, evaluate held-out cases:

```powershell
.\.venv\Scripts\python.exe -m evaluation.calibrate_verifier run --suite data/calibration_results/medaesqa_support_v1.json --output data/calibration_results/heldout_v1.json --split heldout --limit 40
```

## Results and current status

Reports include correct/scored counts, agreement, Cohen's kappa, confusion counts, class counts, mismatches/reasons, pending/failed cases, API-attempt count, and an agreement Wilson interval. Kappa is `null` when chance agreement is 1. The partial-result target flag applies only to scored cases; a completed held-out run is needed for the planned target check.

Targets: agreement ≥80% and kappa ≥0.6. Keep actual results and coverage visible. Balanced-sample agreement is not a raw-prevalence estimate.

Suite preparation and offline regression checks are completed. After explicit authorization, the first **six development pairs** were sent to Gemini and all returned valid predictions: **3/6 agreement (50%), kappa 0.00**. The judge predicted non-support for all six. No reference labels or prompt settings were changed after this result. See [the pilot record](CALIBRATION_PILOT.md) for the disagreements and next checks.

There are 34 development pairs remaining and **all 40 held-out pairs remain unscored**. The initial six-case pilot is completed; the full calibration is not. Inspect the evidence/label alignment before expanding the run or changing the judge prompt.

## Scope investigation completed

Using full cited titles/abstracts for the same six cases, with model, prompt, and labels fixed, produced **4/6 agreement (66.7%), kappa 0.33**. It resolved all three original false negatives, but two selected neutral labels still disagreed with the judge. Both are in document/normalized-sentence groups containing conflicting reference labels. The audit flags these groups without relabeling or excluding them.

The context diagnostic remains a development experiment. [The investigation record](CALIBRATION_INVESTIGATION.md) documents sources, paired results, cache provenance, and the required document-level reference policy before a larger calibration run. No held-out prediction was made.
