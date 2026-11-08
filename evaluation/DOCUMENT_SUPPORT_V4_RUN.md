# Numbered-passage development check

The v4 numbered-passage judge was tested with `gemini-3.8-flash`, temperature 0, on six eligible development cases, followed by a separate targeted test of the two cases that repeatedly failed quote validation in v3. These are eight distinct development cases and eight calls; no held-out cases were evaluated.

## Six-case check

- All six returned locally valid decisions; all retrieved evidence text was verified against original source offsets.
- Citation agreement: 4/6 (66.7%); Cohen's kappa: 0.33. Three reference labels are supporting and three non-supporting.
- Two selected neutral references were predicted supporting: question 126 / PMID 33484483 and question 146 / PMID 34132818. Both were also considered supporting in the supplied human review. That comparison illustrates label/task disagreement; it does not replace the original references or establish which interpretation is authoritative.
- No result was removed based on correctness. Twenty other eligible cases in the full suite were not run with v4; fourteen reference-ambiguous cases remain quarantined.

Saved results: `data/calibration_results/document_support_v4_development.json`.

## Targeted engineering check

Question 126 / PMID 15329821 and question 138 / PMID 15236629 had repeatedly failed quote validation. Both now returned valid source passage IDs on their first v4 attempts. Python retrieved the selected passages exactly from the cached source. Both were judged citation-supported and only partially supported at whole-sentence level.

The targeted reference agreement is 1/2 (one supporting reference, one neutral), with kappa 0.00. This subset was selected because of prior failures and is not an independent accuracy benchmark. Keep its results separate from the six-case check.

Saved targeted suite/results: `data/calibration_results/document_support_v4_targeted_suite.json` and `data/calibration_results/document_support_v4_targeted_failures.json`.

## Decision

Evidence anchoring works on all eight attempted cases; this small sample does not guarantee that every later passage-ID response will be valid. Selecting an existing ID also does not establish semantic support. The scores do not meet the project goals and do not validate the live ADK Verifier.

Further broad prompt tuning is not the next priority. The project overview and success rubric explicitly require comparison against MedAESQA human reference labels. Before treating a different, document-level partial-support interpretation as a substitute, confirm the expected assertion granularity and inference standard. Preserve the existing references, human review, all historical results, and untouched held-out cases. After the task definition is fixed, use a bounded new development experiment and freeze settings before held-out assessment.
