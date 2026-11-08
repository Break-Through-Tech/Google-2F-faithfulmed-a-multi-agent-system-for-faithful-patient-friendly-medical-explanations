# Document support development suite and judge v2

Prepared November 7, 2026. This is a development tool, not a calibrated production Verifier or an independent held-out score.

## What changed

The [v2 judge](calibrate_support_v2.py) asks Gemini to split an answer sentence into independently checkable propositions. For each, it returns an exact sentence quote, support status (`supported`, `contradicted`, or `not_established`), evidence quote, and reason. It also returns two separate conclusions:

- `complete_sentence_supported`: whether all returned propositions are supported by the cited document.
- `citation_support`: whether the document supports a cited assertion; `null` means the cited assertion cannot be determined reliably.

For example, if a sentence lists several drug classes but the paper covers only NSAIDs, the paper can support the citation while the complete sentence remains only partially supported. A sentence-level reference label does not establish a gold label for each proposition. The model's decomposition and conclusions still need evaluation; matching quotes alone cannot prove they are correct or complete.

The local validator checks exact quote membership, requires evidence quotes for support or contradiction, and checks consistency of the complete-coverage flag. It cannot prove that an anchor entails a claim or that all propositions were extracted. Only question, sentence, and title/abstract are sent to the judge; reference labels, flags, and model provenance stay out of its input. Outputs are untrusted judgments.

After the [development investigation](DOCUMENT_SUPPORT_V2_INVESTIGATION.md), prompt `document-support-rules-2026-11-07-v3` clarified partial support and reasonable paraphrases. It instructs the judge to retain population and causal limits, avoid treating combined interventions as independently proven, and quote context that actually supports a claim. This is an instruction change, not proof of improved semantic accuracy.

Future failures include a safe `error_stage` and `error_category`, such as `response_invalid_json`, `response_schema_invalid`, `evidence_quote_missing`, `evidence_quote_not_verbatim`, or `coverage_inconsistent`. Full model responses and raw exception messages are not saved. Categories apply to future attempts; the cause of the old failed case remains unknown. Attempt history is retained. Provider errors remain safely classified where possible.

Citation-reference agreement and coverage descriptions are separate. Agreement excludes ambiguous references, pending context, failed responses, and abstentions, and reports counts and kappa with their actual denominator. The coverage summary is descriptive, not an accuracy score. A development result cannot establish held-out performance, report-level omission quality, or project goals.

## Prepared suite

`data/calibration_results/medaesqa_document_development_v2_full.json` contains the same **40 originally selected development cases**. No held-out case text or model predictions are included. It records the original case IDs, source/reference metadata, split membership, context hashes, and flags.

| Development case status | Count |
| --- | ---: |
| Full title and abstract cached | 40 |
| Eligible for citation-reference agreement under the policy | 26 |
| Quarantined as reference-ambiguous | 14 |
| Newly generated Gemini judgments | See the [development run record](DOCUMENT_SUPPORT_V2_RUN.md) |

The eligible cases have passed structural checks, not semantic adjudication. The 14 ambiguous cases remain in the suite with their original reference records; the runner does not send them or calculate agreement against a selected label. The original six examples and historical results remain available in their earlier files. Do not compare the v2 eligible-only score with the old six-case result as a measured improvement: both the population and task changed.

The [development conflict review](DEVELOPMENT_CONFLICT_REVIEW.md) proposes provisional citation-support decisions for 13 of the 14 cases and identifies one context-dependent case. Those proposals have not been applied to this suite or its agreement calculation.

The first six abstracts came from the prior PubMed cache. The remaining 34 were retrieved from NCBI using only public PMID identifiers, with title/abstract hashes and retrieval provenance recorded in `data/calibration_results/pubmed_development_context_v3.json`. Current PubMed content is not a verified reconstruction of the original TREC snapshot. The updated structural audit is `data/calibration_results/support_conflict_audit_full_context_v2.json`. An earlier incomplete v2 suite remains at `data/calibration_results/medaesqa_document_development_v2.json` for provenance; use the `_full` suite for the next development run.

The suite and cache are local generated data; teammates need the local MedAESQA dataset, original selected suite, and cache to reproduce them. `evaluation/` code and documentation alone do not share these files. Never include `.env` or keys in a handoff.

## Reproduce the suite offline

With the existing local dataset, original suite, and full development cache, choose fresh output paths:

```powershell
.\.venv\Scripts\python.exe -m evaluation.audit_support_references --cache data/calibration_results/pubmed_development_context_v3.json --output data/calibration_results/support_conflict_audit_reproduction.json
.\.venv\Scripts\python.exe -m evaluation.calibrate_support_v2 prepare --original-suite data/calibration_results/medaesqa_support_v1.json --audit data/calibration_results/support_conflict_audit_reproduction.json --cache data/calibration_results/pubmed_development_context_v3.json --dataset data/MedAESQA_data/medaesqa_v1.json --output data/calibration_results/medaesqa_document_development_reproduction.json
```

Preparation verifies the dataset, suite and cache hashes, checks question separation, preserves conflicting labels, and refuses to overwrite a suite. Missing abstracts remain pending and never fall back to snippets.

## Later: bounded development check

This command **calls Gemini** and is included for when the team is ready. It uses only eligible cases with complete cached context, saves attempts as they complete, and requires a new output file if the suite, prompt, schema, model, or temperature changes. It defaults to at most six cases per invocation; `--limit` controls this. It has no held-out run mode.

```powershell
.\.venv\Scripts\python.exe -m evaluation.calibrate_support_v2 run --suite data/calibration_results/medaesqa_document_development_v2_full.json --output data/calibration_results/document_support_v3_development.json --model gemini-3.8-flash --limit 6
```

Review development disagreements, citation scope, partial support, and failures before freezing the method and selecting a versioned held-out cohort. Reusing a held-out case to tune the method would make it unsuitable as an independent test. See the [policy](SUPPORT_CONFLICT_POLICY.md) and [original audit](SUPPORT_CONFLICT_AUDIT.md).

The v3 prompt and schema/settings are included in the run signature. Use a new output path: the prior 68% / 0.31 development run cannot be resumed with changed rules. A subsequent [v3 development run](DOCUMENT_SUPPORT_V3_RUN.md) scored 24 cases at 62.5% agreement and 0.18 kappa; two cases still failed exact-quote validation after one retry.
