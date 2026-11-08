# Bounded readability rewrites and five-report rerun

Implemented November 8, 2026. The final ADK stage now uses Alicia's existing scorer
and can request at most two Gemini wording rewrites when a clinically cleared draft
is above grade 8. Every candidate receives a fresh Verifier check before acceptance.

## Release rules

- Existing Verifier findings or an unresolved strict-Refiner blocker prevent rewriting.
- Every candidate and its input draft, scores, verdict, and acceptance are retained
  in `readability_history`. Pending checks set `faithfulness_recheck_required`.
- A candidate with new findings is rejected. The last verified draft is retained,
  the result becomes `needs_review`, and `final_answer` remains empty.
  `final_verdict` still describes that retained draft; the rejected candidate's
  findings live in `readability_history`, alongside its lower score.
- A candidate that does not improve the grade stops the loop and leaves the previous
  verified draft in place. Refusals and invalid text cannot pass.
- A draft still above grade 8 after two attempts remains `needs_simplification`.
- Service failures stop the run without releasing an unchecked candidate.
- Scripted walkthroughs remain deterministic and do not call the rewrite model.

Zurabi's exact-source clinical Refiner rules and two-round clinical repair limit were
not relaxed. Readability rewrites are a separate, bounded wording pass after those
checks. The shared generation model remains `gemini-3.8-flash`, temperature 0.

Gradio uses this same root agent. Its **Checks & repairs** panel now includes rewrite
grades and recheck outcomes; the trace includes full candidate history. Restart an
already-running ADK or Gradio server to load the change.

## Pilot design

The same five frozen IDs were used: 4998, 3938, 3808, 3606, 2964. The original run is
preserved in `data/comparison_results/five_report_pilot_2026-11-07_v1/`.
Unchanged baseline answers were reused after verifying their code fingerprint.
The ADK pipeline was regenerated in full with the new code in a separate result file;
this was not a replay of only the last stage of the original saved drafts.

New outputs, traces, and per-attempt grades are under
`data/comparison_results/five_report_readability_2026-11-08_v2/`.
The runner still uses the full report query, top-k 3, and the same Gemini index.
Fresh retrieval changed passage order in three pairs and one passage in the CT pair.
The intermediate `paired-pilot-v1.json` retains that mismatch. Matching baseline calls
were attempted for those four reports using the actual saved ADK context, including
its original passage metadata. Three completed. The CT baseline returned a non-normal
model finish twice; no answer was accepted. This failure remains visible. The carotid
pair reused the prior baseline with the same passage IDs/order/text/URLs; floating
distance metadata is not claimed identical there. The final artifact is
`paired-pilot-matched-context-v2.json`: four comparable pairs and one failed baseline
generation. Previous answers remain in the intermediate file and attempt history.
No search was repeated for the matching baseline calls.
`complete_matching_baselines.py` records this bounded local procedure.
Because ADK generations were repeated, differences between old and new final answers
cannot all be attributed to the readability feature. The within-run before/after
rewrite grades provide the direct evidence of its effect on each candidate.

The final result table and exact saved outputs are recorded in that directory's
`SUMMARY.md` and `OUTPUTS.md`. No clinical post-generation
judge scores from the old answers are transferred to the new answers.

## ADK results

| Report | New draft before rewrite | Retained grade after recheck | Status |
|---|---:|---:|---|
| 4998: Allergy | 11.03 | 7.84 | Complete |
| 3938: COPD discharge | 8.50 | 5.26 | Complete |
| 3808: Cystitis / diabetes | 8.67 | 6.61 | Complete |
| 3606: CT | 8.92 | 8.92 | Needs review; candidate rejected |
| 2964: Carotid ultrasound | 10.41 | 6.46 | Complete |

All five attempted one rewrite. Four were accepted after clean rechecks. The CT
candidate scored 4.59, but the Verifier flagged its added phrase "normal wear and tear"
because the report only described degenerative changes. It was rejected; the original
verified draft remained at 8.92, with no final answer released. This demonstrates the
clinical recheck gate blocking a candidate even after it passes readability.

Retained-text readability and final-answer release improved from **0/5** in the first
pilot to **4/5 (80%)** here. This is a five-report workflow result, not a population
estimate or proof that the clinical-quality targets have been reached. No extra rewrites
were attempted to force the fifth case through the gate.

Inspection of the COPD rewrite confirmed all five prednisone taper steps, Levaquin's
five-more-day instruction, and the follow-up timing. The carotid rewrite retains
"at least 50%" and a recommended, not completed, CTA. These targeted checks are not
an exhaustive independent clinical review.

## Verification

Seven new release-gate tests passed: already-readable text avoids rewriting; a rewritten
answer waits for rechecking; a dose-change finding blocks release despite a passing
grade; existing clinical blockers prevent rewriting; the two-attempt cap holds;
non-improving text stops early; and recheck service failure cannot release a candidate.

The related regression run passed 74 existing checks with 32 subtests. After the UI
display and turn-reset assertions were updated, all 21 ADK/UI tests passed again.
These local tests use deterministic stand-ins, not live claims of Verifier accuracy.

## Remaining quality limits

The live Verifier remains uncalibrated. A clean recheck is a release decision under
the current implementation, not proof of complete clinical accuracy. In particular,
the newly readable cystitis output still repeats bladder-disorder denial alongside
the cystitis diagnosis and includes an unstated medication unit from its initial
draft. Existing omission and source-conflict problems need their own focused fixes.
Lowering the reading grade does not resolve those problems or satisfy the calibration
targets. The readability formula and grade-8 threshold were not changed.
