# Citation calibration and report-evaluator status

Updated November 11, 2026. Consolidated findings; intermediate experiment scripts
and detailed investigations remain local.

## Current held-out result

The unchanged original citation judge scored **23/31 agreement (74.2%), Cohen's
kappa 0.498**, with zero failed or pending assessments. Targets of **80% agreement
and kappa 0.6** remain unmet.

| Reference / prediction | Supporting | Not supporting |
|---|---:|---:|
| Supporting | 13 | 7 |
| Not supporting | 1 | 10 |

Before predictions, the existing document-level policy quarantined eight conflicting
reference entries and excluded one repeated document/assertion from the original 40.
All 31 eligible entries had PMID-matched titles/abstracts. Their reference classes
were 20 supporting and 11 not supporting. No exclusions depended on predictions.

The descriptive case-level Wilson 95% agreement interval is 56.8% to 86.3%; it does
not adjust for correlated cases within questions. This small diagnostic sample is
not a deployment-prevalence estimate or clinical validation of the whole system.

[Compact frozen results](results/original_judge_heldout_v1.json) preserve all 40
selected IDs, labels, exclusions, 31 predictions/reasons/quotes, source hashes,
question splits, prompt/schema and provenance fingerprints. Full abstracts and raw
artifacts remain under ignored `data/calibration_results/`.

## Task and labeling boundaries

The original prompt is `PROMPT` in [calibrate_verifier.py](calibrate_verifier.py),
prefixed by `EVIDENCE_RULES` in [scoring.py](scoring.py). It assesses citation support
for an assertion. A citation may support a substantive part without proving the
whole sentence. Question relevance, citation validity, citation support and complete
factual coverage are separate judgments. Missing evidence is not contradiction.
Preserve negation, uncertainty, population, quantities, comparators and causal scope.

Supporting maps to binary true; neutral/contradicting/not-relevant map to false.
Invalid citations are a separate task and excluded. No reference labels enter the
judge payload. Conflicting document-level binary references are quarantined rather
than resolved using model predictions.

The [MedAESQA paper, page 5](https://d-nb.info/1374626414/34) defines document/assertion
relations but does not explicitly resolve every compound sentence's intended scope.
[BioACE section 4.2.3](https://pmc.ncbi.nlm.nih.gov/articles/PMC13119346/) describes
any-supported-nugget attribution with contradiction priority, while its displayed
Appendix A4 prompt requires support for each nugget. Do not claim an unambiguous
universal partial-support rule or assume either party is correct in every disagreement.

## Frozen protocol and reproduction

- Original seed-42 split: 20 development and 20 held-out questions, with no overlap.
  Preserve all 40 selected held-out entries; no resampling or replacement labels.
- Apply existing `support-conflict-2026-11-07-v1` policy before predictions:
  quarantine binary conflicts, invalid/unmapped relations and punctuation neighbors;
  deduplicate document/assertion identity. Retain every exclusion reason.
- Fetch only numeric PMIDs from public PubMed. Check identity/content hashes and
  freeze the cache and inputs before calls. Missing abstracts are unavailable
  coverage, never snippet fallbacks. Current sources are not verified annotation-time
  snapshots.
- Freeze model `gemini-3.8-flash`, temperature zero, original prompt/schema and judge.
  Prompt digest: `0eded17cd2bfeb37c5d79e4a765b77b000cf50478a91e1091adbe5800c151bfb`.
- Send only question, sentence and complete title/abstract. No reference labels,
  grouping output, preceding-answer context or whole-support sidecars.
- One attempt per eligible source-ready case. Checkpoint progress; resume only
  unattempted cases. No label-based or quote-failure retries. Stop on access/quota errors.
- Report agreement/kappa/confusion counts on valid predictions, plus failures,
  unavailable/pending cases, class balance and correct/all eligible. A target claim
  requires a completed evaluation with all eligible sources available.

[original_judge_heldout.py](original_judge_heldout.py) uses the unchanged original
judge and existing tracked preparation helpers. Requires the original local MedAESQA
dataset and configured Gemini key. Never commit `.env`.

```powershell
.\.venv\Scripts\python.exe -m evaluation.original_judge_heldout select
.\.venv\Scripts\python.exe -m evaluation.original_judge_heldout prepare
.\.venv\Scripts\python.exe -m evaluation.original_judge_heldout run
.\.venv\Scripts\python.exe -m evaluation.original_judge_heldout report
```

Artifacts use `data/calibration_results/original_judge_heldout_*_v1.json`. Existing
frozen inputs cannot be replaced with different settings, and recorded attempts are
not repeated. The report command needs full local artifacts; the committed compact
record supports result inspection and score verification without them. Reproduction
can vary even at temperature zero and is not fresh independent validation.

**This held-out set has now been evaluated.** If its disagreements guide revisions,
it becomes development evidence for those revisions. Preserve this score and use
fresh independent cases to confirm later improvement. This does not calibrate every
live ADK/Gradio Verifier behavior or trigger a runtime configuration change.

## Experimental findings retained

| Development experiment | Agreement | Kappa | Finding |
|---|---:|---:|---|
| Original six cases, snippets | 3/6 | 0.000 | Input scope mismatched document-level labels. |
| Same six, title/abstract | 4/6 | 0.333 | More context helped; conflicts remained. |
| V5 document cohort | 13/26 | 0.000 | Partial support/inference remained problematic. |
| V6 | 15/26 | 0.123 | Citation/whole-coverage separation did not settle scope. |
| V7 | 16/26 | 0.217 | Small gain; evidence IDs did not solve semantic errors. |
| Original prompt, same 26 | 19/26 | 0.420 | Stronger observed baseline, not proof of better reasoning. |
| Original plus clause reminder | 18/26 | 0.350 | One gain, two losses; not adopted. |
| Original repeated during V8 | 17/26 | 0.282 | Two decisions changed despite unchanged settings. |

These are repeatedly used development cases, not independent confirmations. The
six-case and 26-case scores use different cohorts and are not directly paired.

V8 added evidence-ID validation and separate whole-sentence assessment. Dedicated
extraction fixed a bundled therapy list but mishandled OR/AND scope. Later overlapping
groups passed nine synthetic extraction checks after a local inherited-condition
validator repair. Reassessment completed 18 of 26 cases, blocked seven and had one
validation error. The adapter rebundled independent AND claims, causing coverage
warnings; some blocks were overly literal token checks rather than lost medical facts.
**Grouping/adapter work is paused and not adopted.** No evidence-judgment accuracy
gain was established. Older experiments remain local rather than being published as
multiple competing current implementations.

## Separate report-evaluator fixes

[clinical_scoring_v2.py](clinical_scoring_v2.py), version
`clinical-source-ids-2026-11-11-v4`, clarifies these boundaries:

- Ordinary headings/nonclinical disclaimers are not biomedical claims. Factual clauses
  in a disclaimer still require assessment.
- Unsupported medication doses, units, routes, frequencies or durations are clinically
  meaningful under the project's conservative source-only rubric. This policy does
  not establish actual patient harm or permit outside drug knowledge.
- Naming a medication does not preserve a missing rationale, warning or follow-up.
  Partial coverage requires a substantive part of the fixed fact, not a shared name.
- Support failure and clinical significance are separate decisions requiring reasons.

On eight unchanged controlled synthetic examples, checks improved **6/8 to 8/8**.
The [versioned fixtures](examples/clinical_scoring_regressions_v3.json) preserve
source/output texts and expectations: background additions, invented dose units,
combined follow-up, strengthened uncertainty, invented findings, historical/current
diagnoses, omitted medication rationale and nonclinical disclaimers. This is a
recorded development regression result, not held-out medical accuracy or live-agent
calibration. Full generated assessments remain local.

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_clinical_scoring_v2.py tests/test_original_judge_heldout.py tests/test_calibration.py -q
```

For a separately authorized live rerun, the report scorer accepts
`--input evaluation/examples/clinical_scoring_regressions_v3.json --output <new-path>`.
Keep model judgments separate from the fixture expectations when checking results.
