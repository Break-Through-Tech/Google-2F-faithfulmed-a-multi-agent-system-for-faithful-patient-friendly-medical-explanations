# Document-support v2 development run

Run on November 7, 2026, using `gemini-3.8-flash`, temperature 0, and the 40-case development suite described in [DOCUMENT_SUPPORT_V2.md](DOCUMENT_SUPPORT_V2.md). This is development testing; no held-out cases were evaluated.

## Schema correction

The first attempt returned HTTP 400 with the saved classification `SCHEMA_REJECTED`; no case was scored. The judge had supplied its strict Pydantic class directly as the service response schema. The corrected run uses the existing `generation_schema` helper to remove `additionalProperties` from the schema sent to Gemini, while preserving strict local validation. The failed first run is retained separately at `data/calibration_results/document_support_v2_development.json`.

## First six

All six returned locally valid outputs. Citation-support decisions matched the selected references in **5/6** cases (83.3% agreement; kappa 0.67). For the drug-list example the output separated NSAID support from other unsupported classes. This small initial check showed the pipeline could produce parseable responses and separated some partial coverage; it did not establish semantic reliability.

## All eligible development cases

| Measure | Result |
| --- | --- |
| Eligible cases attempted | 26 / 26 |
| Successfully scored | 25 / 26 |
| Failed validation after one retry | 1 / 26 |
| Matching selected reference | 17 / 25 |
| Agreement | 68% |
| Agreement 95% Wilson interval | 48.4% to 82.8% |
| Cohen's kappa | 0.31 |
| Reference supporting predicted supporting | 12 |
| Reference non-support predicted non-support | 5 |
| Reference non-support predicted supporting | 4 |
| Reference supporting predicted non-support | 4 |

Fourteen additional development cases with conflicting references remain quarantined and were not sent to the judge. One case produced `ValueError` twice; the runner saves the error type but not the detailed validation error or response, so its exact cause is unknown. Both attempts remain in the result file. No score was assigned to that case.

The selected references contain 16 support and 9 non-support labels among the 25 scored cases. Results are not prevalence estimates. Current PubMed titles/abstracts are not a verified snapshot of the original dataset. Reference labels are imperfect proxies for the document-level support task; disagreements are not automatically judge errors or reference errors. The 80% agreement and 0.6 kappa goals are not met by this development result.

## What the disagreements illustrate

- Question 146 / PMID 34132818: the reference is neutral, while the judge found partial support in the full abstract for a sentence about adolescent psychotherapy; the judge's quoted background sentence says treatment can be effective without itself specifying psychotherapy. The broader abstract and scope need careful interpretation.
- Question 126 / PMID 17911163: the reference is supporting, while the judge rejected the age/nondisjunction claim as not explicit enough. This may reflect strict literal interpretation and needs a scope review, not an automatic relabel.
- Question 137 / PMID 32641437: the reference is supporting, while the judge declined to attribute outcomes to ketogenic diet alone because the case also used intermittent fasting. That distinction needs assessment against the exact cited assertion and reference task.

Local quote validation verifies that quotes occur in the text; it cannot establish that they support the claim or that every proposition was captured. The three complete-sentence-supported outputs and 70 proposition statuses are descriptive outputs, not independently measured coverage accuracy.

The saved corrected result, including every attempt and reason, is `data/calibration_results/document_support_v2_schemafix_development.json`. Do not treat this score as held-out performance or evidence that the live ADK Verifier is calibrated. Investigate task/reference alignment and failed response handling before selecting changes or running an independent held-out assessment.

The [follow-up investigation](DOCUMENT_SUPPORT_V2_INVESTIGATION.md) examines all eight disagreements and the failed case without changing their results.
