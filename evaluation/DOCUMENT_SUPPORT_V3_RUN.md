# Document-support v3 development run

The revised `document-support-rules-2026-11-07-v3` prompt was run on the same 26 eligible development cases with `gemini-3.8-flash`, temperature 0. Fourteen cases with conflicting references remained quarantined; no held-out cases were run.

## Results

| Measure | Previous v2 run | Revised v3 run |
| --- | ---: | ---: |
| Eligible cases attempted | 26 | 26 |
| Cases successfully scored | 25 | 24 |
| Remaining failed cases | 1 | 2 |
| Matches with selected reference | 17 / 25 | 15 / 24 |
| Agreement | 68.0% | 62.5% |
| Cohen's kappa | 0.31 | 0.18 |

The revised run's 95% Wilson interval for agreement is approximately 42.7% to 78.8%. Of the 24 scored references, 15 are supporting and 9 are non-supporting. The four confusion counts are: 11 support/support, 4 non-support/non-support, 5 reference non-support/judge support, and 4 reference support/judge non-support.

The two runs scored different numbers of cases. On the **24 cases scored by both**, the previous run matched 16 references and the revised run matched 15. This is a development comparison on cases already used to inform the prompt, not an independent estimate of improvement.

Three matched cases changed their citation-support decisions:

- Question 126 / PMID 33484483: neutral reference; changed from no support to support. A separate human reviewer also considered it supported. This remains a reference-scope disagreement, not proof that either label is correct.
- Question 126 / PMID 17911163: supporting reference; changed from no support to support. The extent to which the combined age, nondisjunction and meiosis claims follow from the abstract still requires interpretation.
- Question 150 / PMID 20397860: supporting reference; changed from support to no support. This needs inspection against the precise claim and evidence before calling the change an error or improvement.

## Failures and limitations

Four first attempts failed the `evidence_quote_not_verbatim` check. All four were retried once: two succeeded and two failed the same check again. The remaining failures are question 126 / PMID 15329821 and question 138 / PMID 15236629. Both attempts are retained in the result file. The category means the quote did not exactly match the supplied evidence; without saved raw responses it does not reveal whether the difference was formatting, wording, or something else.

Neither run meets the project's development agreement and kappa goals. The reference labels and the new document-level partial-support task can differ in scope, so reference disagreement does not automatically prove a judge error. Exact quote checks also do not verify semantic support or complete claim extraction. The results do not validate the live ADK Verifier, and no claim of held-out performance is made.

Saved result: `data/calibration_results/document_support_v3_development.json`. The previous v2 results remain in `data/calibration_results/document_support_v2_schemafix_development.json`. Both files are local generated data. The next step is to inspect quote-validation failures and the changed decisions before choosing another development change; do not tune on held-out cases.

The [offline v3 investigation](DOCUMENT_SUPPORT_V3_INVESTIGATION.md) now documents the three changed decisions, all four initial quote failures, and the limits of what can be inferred from the saved data.
