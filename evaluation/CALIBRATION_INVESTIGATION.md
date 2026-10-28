# Calibration mismatch investigation — October 27, 2026

## Findings

The first pilot mixed two different evaluation units: a **short annotated snippet** was supplied to the judge, while the dataset defines the reference relation between the answer assertion and the **cited document**. The [MedAESQA paper](https://www.nature.com/articles/s41597-025-05233-z) says the evaluated documents were PubMed titles/abstracts, not full papers. The local dataset README likewise distinguishes `evidence_relation` (sentence/document relation) from `evidence_support` (a snippet supporting the annotation).

This was an input-alignment mistake in our first adapter. The six-case zero-kappa result therefore did not isolate the Verifier's ability to judge the same evidence the dataset assessors saw.

A second problem remains: some normalized sentence/PMID groups contain different reference labels across dataset entries. The first preparation removed conflicts for identical **snippet** inputs; it did not catch conflicts that emerge at the **document** level when excerpts differ. No labels were changed and no pilot cases were removed in this investigation.

## Controlled context check

Fetched the public titles/abstracts for **all six** already-tested PMIDs using NCBI EFetch. The original snippets occur within all six retrieved abstracts. Kept the same six case IDs, reference labels, model (`gemini-3.8-flash`), temperature, and judge prompt. Only the evidence text changed. Reference labels and highlighted snippets were excluded from the judge payload; it saw the question, sentence, and complete title/abstract.

| Result | Original snippet pilot | Title/abstract diagnostic |
| --- | --- | --- |
| Cases scored | 6 | The same 6 |
| Matching labels | 3/6 | **4/6** |
| Agreement | 50% | **66.7%** |
| Cohen's kappa | 0.00 | **0.33** |
| False negatives | 3 | **0** |
| False positives against selected labels | 0 | **2** |
| API failures | 0 | 0 |

All three original supporting-label disagreements changed to supported. Two neutral-label cases changed to supported as well, creating the remaining reference disagreements. The 80%/0.6 targets are **not met**. This is a development diagnostic on already-seen cases, not an independent or held-out performance improvement claim.

| Question | PMID | Selected label | Snippet prediction | Abstract prediction | Reference match after change |
| --- | --- | --- | --- | --- | --- |
| 144 | 16810473 | supporting | Not supported | Supported | Yes |
| 128 | 36968131 | neutral | Not supported | Supported | No |
| 139 | 35172902 | supporting | Not supported | Supported | Yes |
| 126 | 33484483 | neutral | Not supported | Not supported | Yes |
| 142 | 24042856 | supporting | Not supported | Supported | Yes |
| 146 | 24422773 | neutral | Not supported | Supported | No |

## Why the added context mattered

- **144:** the supplied snippet discussed reversible risk factors broadly; the complete [hypertension guideline abstract](https://pubmed.ncbi.nlm.nih.gov/16810473/) also recommends lifestyle measures. This supports the general lifestyle assertion without relying on external knowledge.
- **139:** the [pregnancy review abstract](https://pubmed.ncbi.nlm.nih.gov/35172902/) contains results about complications, whereas the snippet supplied only the background/aim. Partial support for the sentence can therefore be assessed from actual findings.
- **142:** the [NSAID study title and abstract](https://pubmed.ncbi.nlm.nih.gov/24042856/) explicitly describe increased blood pressure. The direction was absent from the selected conclusion snippet.
- **128:** the [CBD abstract](https://pubmed.ncbi.nlm.nih.gov/36968131/) contains a result corresponding to the liver-test comparison, beyond the study-aim snippet. The selected neutral label now disagrees with the judge's supported decision.
- **146:** the [PTSD abstract](https://pubmed.ncbi.nlm.nih.gov/24422773/) discusses SSRIs and residual symptoms after nondrug treatment; the snippet concerned other medication options. The selected neutral label again disagrees with the supported prediction.

These observations identify a mismatch; they do not justify automatically replacing the reference labels. The downloaded abstracts are current PubMed records, not a verified reconstruction of the exact TREC 2024 snapshot. Cache provenance and content hashes are saved.

## Document-level label audit

Within the six development questions, compared the same normalized assertion and cited PMID across machine-answer entries. Normalization removes numeric citation markers and punctuation/case differences while retaining the assertion's words, negation, and numbers. This audit reports ambiguity; it never uses model correctness to filter cases.

| Question / PMID | Relations found for the normalized assertion/document group |
| --- | --- |
| 144 / 16810473 | supporting: 2; not relevant: 2 |
| 128 / 36968131 | supporting: 4; neutral: 2; not relevant: 1 |
| 139 / 35172902 | supporting: 8; neutral: 1; not relevant: 1 |
| 126 / 33484483 | neutral: 1 |
| 142 / 24042856 | supporting: 2 |
| 146 / 24422773 | supporting: 1; neutral: 1 |

Four of six groups have mixed relations. Three have opposite binary support labels even when restricted to nonblank excerpt records. Both remaining diagnostic disagreements belong to those mixed groups. It would be misleading to claim that removing them establishes a better kappa; all six remain in the reported results.

## Implemented changes and reproduction

- [Context investigation utility](investigate_calibration.py): restricts analysis to attempted development cases, fetches PMID-matched title/abstract context, preserves original cases/labels, validates cache hashes, and audits document-level reference conflicts.
- The calibration runner records context version/input unit and refuses an empty held-out split. The six-case diagnostic suite has no held-out execution path.
- The judge prompt and clinical-demo Verifier/Refiner are unchanged. No extra clinical-report run was made.

Prepare the same diagnostic suite from the cached documents, choosing a new output path if reproducing:

```powershell
.\.venv\Scripts\python.exe -m evaluation.investigate_calibration --suite data/calibration_results/medaesqa_support_v1.json --pilot data/calibration_results/development_v1.json --cache data/calibration_results/pubmed_pilot_context_v2.json --output data/calibration_results/context_suite_reproduction.json
```

The cached fetch uses numeric PMIDs only; no questions, labels, or keys are sent to NCBI. If the cache is absent, the command fetches those public records. No partial suite or silent snippet fallback is allowed when a document is missing.

Local evidence:

- `pubmed_pilot_context_v2.json`: title/abstract cache, source URLs, timestamp, and hashes.
- `development_context_suite_v2.json`: same six cases with expanded evidence.
- `development_context_v2.json`: new live predictions and summary.
- `pilot_document_label_audit.json`: reference-group counts and source record identifiers.
- `context_comparison_v2.json`: paired before/after decisions and unchanged-setting checks.

These files are under ignored `data/calibration_results/`.

## Next calibration work

Use the documented title/abstract scope for a document-level benchmark, with a prospectively specified document-identity deduplication and reference-conflict policy. Record ambiguous groups separately; do not choose a preferred label or discard cases based on predictions. Any revised cohort must be versioned before evaluating it, preserving question-level separation.

Alternatively, an explicitly snippet-level test needs references that apply to those snippets; the document labels should not silently be presented as snippet-entailment truth. Do not lower the clinical scorer's support standards to force agreement.

The original **34 untested development and 40 held-out cases remain unscored**. The frozen clinical-report set is unchanged. This investigation explains part of the first pilot's failure and establishes the next data/protocol correction; it does not mark full Verifier calibration complete.
