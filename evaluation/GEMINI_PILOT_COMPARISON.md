# Gemini pilot comparison and Issue #32 handoff

## November 20 updated-prompt rerun

The updated Simplifier/Verifier prompts were rerun on the same five reports in
`data/comparison_results/five_report_prompt_fixes_2026-11-20_v1/`. After the saved
connection failures, an authorized technical retry returned five baseline answers
and released four ADK answers. Report 3808 remained an ADK draft after its
readability rewrite failed verification. All five retrieval pairs matched.

The new matched released cohort is 4998, 3938, 3606, and 2964. Its clinical scores
are baseline 171/176 supported claims (97.16%) and ADK 154/157 (98.09%), with
missing facts 0/46 and 1/46 respectively. Both had 0/4 outputs flagged for a
clinically meaningful unsupported claim. ADK's three unsupported additions were
general explanations not supported by the supplied passages. Baseline met grade 8
on 3/4 matched answers and ADK on 4/4. All nine released answers have valid
assessments after technical recovery. The held ADK draft's assessment failed a
coverage-consistency check and has no valid score.

The medication-unit fix took effect in the retained 3808 draft, and the 4998
answer preserved the atenolol rationale. The post-discharge update remains
missing. The earlier cohort below included 3808 instead of 3606, so the aggregate
percentages are not a direct before/after comparison. On the three common
released IDs (4998, 3938, 2964), ADK supported claims changed from 107/107 to
106/109, while missing facts decreased from 2/33 to 1/33. The targeted fixes do
not establish uniform clinical improvement.

The local run's `SUMMARY.md` records every denominator, failure, retry, and saved
artifact. Exact input hashes, evidence IDs, coverage, and metrics were revalidated
offline. The prompts and evaluation settings stayed fixed during this run.

## Earlier pilot

The readability rewrite pilot produced four comparable baseline and ADK pairs using Gemini 3.8 Flash. ADK met the grade-8 target more often, while the baseline received higher faithfulness scores from the clinical judge. The fifth baseline generation failed, and the corresponding ADK draft was held for review.

| Measure | Baseline | Full ADK |
| --- | ---: | ---: |
| Reports attempted | 5 | 5 |
| Answers returned or released | 4/5 | 4/5 |
| Generation failures | 1/5 | 0/5 |
| Drafts held for review | 0/5 | 1/5 |
| Grade 8 or below on the four matched pairs | 3/4 | 4/4 |
| Mean Flesch–Kincaid grade on those pairs | 7.56 | 6.54 |
| Mean recorded generation time on those pairs | 25.38 seconds | 85.87 seconds |
| Valid clinical assessments for those pairs | 4/4 | 4/4 |
| Supported claims / total claims | 139/139 (100%) | 140/145 (96.6%) |
| Missing key facts | 0/40 | 2/40 |
| Partially covered key facts | 2/40 | 3/40 |
| Unsupported additions | 0 | 4 |
| Answers with clinically meaningful unsupported claims | 0/4 | 1/4 |

Times are descriptive. The comparison reuses one historical baseline answer and regenerates three with the matched ADK context. The [readability comparison](READABILITY_COMPARISON.md) records the full readability metrics. For report 3606, ADK rejected a rewrite that added a qualification and retained the earlier draft at grade 8.92. The [rewrite pilot](READABILITY_REWRITE_PILOT.md) records the failure and the recheck.

## Scoring the saved pilot

- Source: `data/comparison_results/five_report_readability_2026-11-08_v2/paired-pilot-matched-context-v2.json`. All ten input slots were checked against the saved output, source text, status, and frozen pilot fact inventory. All nine non-empty payloads passed local preparation.
- `evaluation.clinical_scoring_v2` used the same fact inventory for both systems. The initial run recorded nine connection failures. The retry produced nine valid assessments across ten generation slots. It scored the four baseline answers, four released ADK answers, and one held ADK draft. The saved retry is `clinical_scores_source_ids_2026-11-20_retry.json` in the same local results directory. Input digests and every scored assessment's evidence IDs and metrics were revalidated offline.
- For report 4998, the judge flagged the released ADK answer for omitting the post-discharge update and the rationale for continuing atenolol. For report 3808, the judge flagged a medication unit added to the ADK answer that was absent from the report. The one flagged released answer drives the ADK rate of 1/4.
- The held ADK draft for report 3606 scored 32/35 supported claims with one missing key fact. The judge flagged the draft for presenting the kidney and adrenal descriptions as separate findings without acknowledging the source discrepancy. The draft is outside the matched released-answer totals.

These are model judgments on four matched released pairs. The claim counts depend on how the judge splits the text. The results describe this pilot and do not establish a clinical accuracy difference on the full set.

## Handoff to the 50-report run

Use the [comparison runner](RUNNING_COMPARISONS.md) and [scoring protocol](COMPARISON_PROTOCOL.md) for the full run. Carlin owns generation and token accounting in Issue #32. Rafi owns scoring and interpretation.

- The local `data/curated_baseline/frozen_50_source_key_facts_v1.json` inventory covers all 50 frozen reports. It preserves the original pilot facts and IDs and adds 115 facts for the other 45 reports using a source-only desk review. Every evidence quote was checked against the frozen source. The new lists are focused and do not exhaust every report detail. Use the same per-report facts for both systems and record the inventory digest with the scoring run.
- The pilot confirmed that report 3808's ADK answer added a medication unit absent from the source and report 4998's ADK answer omitted the documented rationale for continuing atenolol. The Simplifier and live Verifier prompts now explicitly address unspecified units, tablet counts, and medication rationale. Local workflow and scorer tests passed. The updated-prompt rerun above documents the observed effects and remaining issues.
- Record generation and scoring coverage for both systems alongside the released-answer metrics.
- Follow the [fixed counting policy](COMPARISON_PROTOCOL.md#fixed-counting-policy-for-the-50-report-comparison-november-20): show release counts out of all 50, keep held drafts and failures separate, and compare clinical quality only on identical eligible report IDs. Preserve first-attempt outcomes and report retry recoveries separately. The pilot scores above remain explicitly retry results.

The [MedAESQA calibration record](CALIBRATION.md) preserves the original held-out result of 74.2% agreement and κ = 0.498 and the later retrospective result of 80.65% and κ = 0.609. These are citation-support evaluation results.
