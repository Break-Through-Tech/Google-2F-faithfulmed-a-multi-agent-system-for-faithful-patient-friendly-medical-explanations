# Five-report baseline versus ADK pilot

Follow-up: [bounded readability rewrite and rerun](READABILITY_REWRITE_PILOT.md).
Later scoring follow-up: [source-ID clinical scorer results](CLINICAL_SCORING_V2_RUN.md)
reached 10/10 valid assessments on the original saved texts. The earlier failed
assessments below remain the historical first scoring attempt.
The results below remain the original pilot, before that implementation change.

Completed generation for five frozen MTSamples reports, using `gemini-3.8-flash`
for both systems. The baseline returned five answers. ADK produced five drafts but
released none: all five exceeded the Flesch-Kincaid grade-8 target. This is a useful
end-to-end pilot result, not evidence that either system meets the accuracy goals.

Generation began November 7; scoring and the comparison report were completed November
8, 2026. Artifact paths retain the November 7 start date.

## Generation and readability

| Report | Baseline FK grade | ADK FK grade | Baseline status | ADK status |
|---|---:|---:|---|---|
| 4998: Allergy evaluation | 8.23 | 10.28 | Answer returned | Needs simplification; draft retained |
| 3938: COPD discharge | 8.41 | 8.11 | Answer returned | Needs simplification; draft retained |
| 3808: Cystitis / diabetes | 6.18 | 9.08 | Answer returned | Needs simplification; draft retained |
| 3606: Abdominal / pelvic CT | 7.39 | 8.61 | Answer returned | Needs simplification; draft retained |
| 2964: Carotid ultrasound | 7.23 | 9.87 | Answer returned | Needs simplification; draft retained |

- Generated texts: **10/10**, with no generation/service failures.
- Baseline readability passes: **3/5**. ADK draft readability passes: **0/5**.
- Baseline answers are returned without ADK's release gate; `ok` is not an accuracy verdict.
- Average saved elapsed time: baseline **23.70 seconds**, ADK **55.62 seconds**.
  These are single observed attempts, not a controlled timing benchmark.
- Every ADK final internal Verifier verdict had zero unresolved issues and no repair
  rounds. Those judgments remain uncalibrated and do not establish completeness.
- The current readability stage reports that rewriting is needed; it does not itself
  rewrite the draft. No rule or threshold was relaxed to obtain a released answer.

## Fairness and reproducibility checks

The frozen set `v3-medium-with-allergy-exceptions-frozen-2026-10-26` was validated
against the original MTSamples CSV, including all six frozen file hashes. The pilot IDs
were fixed: 4998, 3938, 3808, 3606, 2964. The five source-fact inventories and their
file hashes were verified before evaluation; the same 53 facts were used for each
system, totaling 106 fact-coverage checks requested from the evaluator.

Both systems used the same complete report as the query, `top_k=3`, and the same
6,883-chunk Gemini embedding collection. All five pairs matched on the ordered chunk
IDs. An additional comparison checks exact retrieved text and URLs. Generation used
the existing system prompts; there were no prompt changes during this pilot.

The earlier report-4998 pair was reused after verifying that its source, code/settings
fingerprints, and retrieval index metadata match this run. The other four pairs were
generated once. The old second-computer run remains intact in its original directory.
Report 4998's source checklist was prepared retrospectively; this timing limitation
is retained. The pilot is hand-picked and does not estimate performance on all 50.

## Concrete findings from inspecting the saved text

These are targeted source/output observations, separate from automated aggregate scores.
They are not a complete clinical adjudication or replacement reference annotations.

| Report | What the comparison shows |
|---|---|
| 4998 | Both outputs retain uncertain Keflex causality and pending testing. The baseline retains the reason atenolol was medically necessary despite complicating anaphylaxis treatment. The ADK draft lists atenolol but omits that explanation and does not state that no further problems were reported after discharge. |
| 3938 | Both preserve all five prednisone taper steps, the final two-day step, Levaquin's five-more-day instruction, EF 55%, the abnormal/reversible ischemia finding, and the primary-care/cardio follow-up timing. The ADK draft is just above grade 8. |
| 3808 | Both repeat the checklist's denial of bladder disorder alongside an acute cystitis diagnosis without explaining the discrepancy. Neither invents a treatment duration from the quantity of 30 tablets. The ADK additionally writes `400/80 mg` where the source lists `400/80` without a unit; this needs review under the source-only policy. |
| 3606 | The baseline explicitly describes the renal/adrenal wording as an uncertain location in the report. The ADK draft gives separate kidney and adrenal entries without clearly saying they conflict, potentially implying two nodules. The draft also omits the explicit limitation from noncontrast technique. Both preserve the lung follow-up in three months and possible cirrhosis wording. |
| 2964 | Both preserve left internal carotid narrowing of **at least 50%**, right-sided plaque without greater-than-50% narrowing, and a CTA recommendation rather than claiming it was completed. The ADK is more concise about measurements but its added terminology/background still leaves it above grade 8. |

In the CT trace, the internal Verifier even describes a separate adrenal recommendation
while accepting the kidney nodule wording. This is a concrete case to retain for future
conflict-preservation tests. An empty issues list did not catch this ambiguity.

## Post-generation assessment

The unchanged advisor-defined clinical evaluator was applied to all ten outputs with
the same source-only inventories. Its judgments are provisional because calibration
targets have not been reached. ADK texts remain explicitly marked `draft`; they must
not enter released-answer faithfulness or hallucination summaries.

Several initial assessments failed exact quote validation. A bounded diagnostic retry
showed that some quoted text omitted Markdown bold markers. An auditable helper permits
restoration only where the source has one match differing in inline formatting or
whitespace. It preserves every original assessment and adjustment and reruns the strict
validator. It does not rewrite answers, alter support decisions, relax coverage rules,
or accept changed wording. Shortened evidence with ellipses and paraphrased quotes can
still fail. Each remaining failed assessment received at most one retry; valid initial
assessments were reused. Failures remain in the denominator of attempted evaluations.

Final assessment counts: **5/10 valid, 5/10 failed**. Four valid assessments are baseline
answers and one is an ADK draft. Four remaining failures have unresolvable quote anchors;
one has no parsed structured assessment. There were 19 post-generation scoring calls
including initial failures, one diagnostic call, and eight bounded retries. No further
calls were made. Final details and provisional scores are saved in the local `SUMMARY.md`
and `clinical_scores_v2.json` listed below. Missing scores are not zero or 100%.
The generation pilot is complete; a complete valid clinical scoring comparison remains
unfinished. No baseline/ADK accuracy winner is established by this pilot.

There are semantic concerns even in structurally valid assessments. For example, the
3808 ADK assessment marks all seven checklist items covered and all 16 extracted claims
supported, despite the unresolved bladder/cystitis wording and added Bactrim unit noted
above. It also combines multiple independent facts into single claim entries. Quote
validation alone cannot establish correct support judgments or an exhaustive atomic
claim inventory; its 100% model-assigned score must not be treated as verified accuracy.

## Saved artifacts

All are under `data/comparison_results/five_report_pilot_2026-11-07_v1/`:

- `SUMMARY.md`: comparison results and scoring completion counts.
- `OUTPUTS.md`: full sources and all ten saved answers/drafts, readable side by side.
- `paired-pilot-v1.json`: generation settings, original outputs, timings, provenance,
  and retrieval results.
- `traces/`: complete ADK states and events for all five reports.
- `scoring_inputs.json`: the fixed source/checklist/context/answer input for each assessment.
- `clinical_scores_v1.json`: all initial scoring attempts, including failures.
- `scoring_diagnostic_4998_baseline.json`: preserved diagnostic assessment.
- `clinical_scores_initial_with_diagnostic.json`: valid diagnostic result restored
  offline for reuse; the initial failures remain preserved separately.
- `clinical_scores_v2.json` and `assessment_attempts/`: bounded retries, saved raw
  assessments, exact restored anchors, and retained initial attempts.

Generated clinical data and outputs remain local under the existing Git-ignore rules.
No personal documentation was included, and nothing was committed or pushed.

## What this pilot says to do next

1. Add a bounded readability rewrite followed by re-verification, so an otherwise usable
   draft can progress toward the target instead of only returning a suggestion.
2. Improve handling of conflicting report sections, using the renal/adrenal and
   bladder/cystitis cases as regression examples. Preserve uncertainty rather than
   implying an extra finding or repeating contradictory facts without explanation.
3. Improve evidence-anchor reliability in the clinical evaluator before claiming a
   complete claim-level comparison. Keep failed scoring attempts visible.
4. Repeat this fixed pilot after intentional pipeline changes in a new versioned run.
   Preserve these outputs for comparison. Expand to all 50 after the release/scoring
   behavior is understood. Calibration remains a separate unfinished task.

## Validation

Before generation: 49 comparison/scoring tests passed, with four additional subtests.
The formatting-anchor helper's seven focused tests passed. Generation records and
source/checklist hashes were checked. Source prompts, frozen text, and model remained
unchanged during the run.
