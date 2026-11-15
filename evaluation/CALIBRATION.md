# Citation calibration and report-evaluator status

Updated November 15, 2026. Consolidated findings; intermediate experiment scripts
and detailed investigations remain local.

## Latest candidate and results

The current citation-only candidate uses whitespace-safe source-quote validation
and is frozen as `citation-judge-frozen-2026-11-15-v1`. Its configuration, policy,
verification commands, and limitations are consolidated below. This does not
switch the live report Verifier or establish its clinical accuracy.

| Measurement | Valid assessments | Reference matches / valid | Kappa on valid | Failed | Correct / all 31 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Original held-out run | 31/31 | 23/31 (74.2%) | 0.498 | 0 | 23/31 |
| Citation-only development run | 29/31 | 24/29 (82.8%) | 0.652 | 2 | 24/31 |
| Full reliability repeat, before/after its one technical retry | 30/31 | 25/30 (83.3%) | 0.661 | 1 | 25/31 |
| Whitespace-only offline replay of all first responses | 31/31 | 26/31 (83.9%) | 0.668 | 0 | 26/31 |

The last row is a retrospective validation replay, not a new model run or fresh
held-out result. The same 31 cases had already been inspected. The model's
decisions did not change during replay: one quote became valid when its source
line breaks were restored. Five reference disagreements and a severity-qualifier
reasoning concern remain. Independent validation is still required.

[Compact current results](results/citation_judge_summary_2026-11-15.json) retain
case identities, unchanged references, decisions/failures across these runs,
source/response hashes, restored-quote locations, aggregate metrics, and provenance.
Raw responses and full abstracts remain local under ignored
`data/calibration_results/`; individual intermediate reports are not required to
understand this status.

## Original held-out result

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

## Original held-out protocol and reproduction

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

### November 15: configuration frozen for independent validation

The [citation judge and retry policy are frozen](#frozen-candidate-and-retry-policy) as
`citation-judge-frozen-2026-11-15-v1`. The machine-readable manifest records the
prompt, schema, model/settings, whitespace validator, source snapshots/hashes,
runtime versions, and bounded technical-retry rules. A verification helper rejects
drift and requires a separately frozen cohort before model calls. No independent
cohort has been selected and no new API run has started. The next step is exposure,
duplicate, and reference-conflict auditing before freezing the validation sample.

### November 15: whitespace-only source quote recovery

A [separate validation implementation](citation_quote_validation.py) restores original
source text only when whitespace normalization gives one unique contiguous span.
It rejects altered content, token fragments, and ambiguous locations. Replaying
all 31 captured first responses, with no new model calls, produced **26/31 valid
reference matches (83.9%), kappa 0.668**, zero failed assessments. One invalid
response became valid; the other decisions and all earlier scored runs stayed
unchanged. This is improved evidence-location coverage on reviewed data, not a
new held-out score or a demonstrated improvement in the model's reasoning.

### November 15: predeclared full-cohort reliability repeat

The [31-case repeat](citation_reliability.py) froze the citation-only settings
before calls and allowed at most one technical retry per failed case, with SDK
automatic retries disabled. First-attempt and post-retry scores were identical:
**25/30 valid matches (83.3%), kappa 0.661**, one unresolved failure, no pending
cases. Across all 31 attempted pairs, 25 matched the reference (80.6%). There
were 32 calls: every case was attempted first, then the one eligible failure
was retried once. No valid disagreement was retried.

The remaining failure collapsed source newlines into spaces on both attempts.
The 29 shared valid decisions from the earlier citation-only run were unchanged;
the additional reference match came from better coverage, not altered judgments.
All prior artifacts and scores remain preserved. This is reviewed-case reliability
evidence, not fresh held-out validation, and does not calibrate the live Verifier.

### November 11: focused citation-only follow-up

The [citation-attribution experiment](citation_attribution.py) separates the
single-document citation label from whole-sentence coverage. The live report
Verifier and report evaluator were not changed. On the 31 now-reviewed cases,
the revision achieved **24/29 valid matches (82.8%), kappa 0.652**, with two
quote-validation failures. The contemporaneous original achieved 23/30,
kappa 0.541, with one failure. On the same 29 valid paired cases, the original
scored 22/29, kappa 0.529, versus 24/29, kappa 0.652 for the revision: two gains,
zero losses. Across all 31 attempts the revision had 24 correct matches (77.4%).

This is a development improvement on valid paired cases, **not completed
held-out calibration**. One improved reference match still drops a severity
qualifier in its explanation. Failed assessments and that reasoning concern
prevent promoting it as a reliable live configuration. The original frozen
23/31, kappa 0.498 result remains unchanged. See the
[compact current results](results/citation_judge_summary_2026-11-15.json) for
case-level decisions and failures.

November 12: two separate quote-diagnostic calls
both passed unchanged exact-quote validation. This did not reproduce or explain
the lost invalid responses. Capture was added for future failures; the scored
run, its two failures, and all published metrics remain unchanged.

## Frozen candidate and retry policy

The [frozen manifest](frozen/citation_judge_2026-11-15_v1.json) records the exact
prompt, schema, request settings, validator version, installed runtime versions,
and canonical source hashes/snapshots for nine relevant files. Its fingerprint is
`7d62257ab926bd5fd17b78e6ce47d4108706f2a8e2ce2cff069bb235b67d297b`.
It contains no API key or evaluation reference labels.

- **Citation task:** one complete substantive supported claim suffices unless a
  claim is contradicted. Preserve necessary qualifiers; missing evidence is not
  contradiction. Whole-sentence coverage is separate from this citation label.
- **Request:** `gemini-3.8-flash`, temperature zero, the JSON schema in
  [citation_attribution.py](citation_attribution.py), and a 60-second timeout.
  Send only question, sentence, and the cited document's cached title/abstract.
  Do not supply reference labels, external knowledge, or a snippet fallback.
- **Quote validation:** [citation_quote_validation.py](citation_quote_validation.py)
  collapses whitespace only to locate a unique contiguous source span, restores
  its original text, and records offsets and hashes. It rejects changed words,
  punctuation, numbers, negation, ambiguous matches, and token fragments. It
  never fuzzy-matches or joins passages across an ellipsis. Original response
  consistency checks still apply, and model decisions/reasons stay unchanged.
- **Retry budget:** at most two attempts per case, with SDK automatic retries
  disabled. Attempt every case once before retrying eligible technical failures.
  Allow one identical-call retry for invalid output or a listed transient
  connection/server error, including ambiguous/malformed quotes. Never retry a
  valid disagreement. Send no preferred answer or correction feedback.
- **Stops:** HTTP 400/401/403/404/429 stop the run. Blocked/refused outputs and
  unclassified errors do not automatically retry. An uncertain interrupted
  request cannot be silently repeated. A retryable error category does not
  bypass the two-attempt budget.
- **Reporting:** retain every attempt/response/failure, select the first valid
  attempt, and report first-attempt and post-retry metrics separately. Include
  valid coverage and correct/all-attempt denominators. Never assign a preferred
  binary label to a failed assessment. Targets remain agreement >=80% and
  kappa >=0.6, with coverage and sample independence reported explicitly.

[freeze_citation_judge.py](freeze_citation_judge.py) checks the manifest fingerprint,
code, prompt, schema, settings, and runtime. It tolerates Git CRLF/LF differences
only; intentional changes need a new freeze version. Repeating `freeze` verifies
the existing file rather than replacing it. Model-provider updates behind the
model identifier can still cause variation.

Use `evaluation.freeze_citation_judge.judge(..., cohort_manifest=...)` for a future
bound sample and its `retry_allowed` helper for the declared attempt budget. The
entry point requires a separately frozen cohort bound to this configuration,
including sampling/exclusion provenance and per-case input/reference hashes.
Those hashes detect later edits; they do not themselves prove sample independence.
No independent sample or new held-out score is included in this commit. Unused-case
auditing and sample preparation remain separate work.

```powershell
.\.venv\Scripts\python.exe -m evaluation.freeze_citation_judge verify
.\.venv\Scripts\python.exe -m pytest tests/test_citation_attribution.py tests/test_citation_quote_validation.py tests/test_citation_reliability.py tests/test_freeze_citation_judge.py -q
```

The frozen runtime is Python 3.12.4, Google GenAI SDK 2.25.0, and Pydantic 2.13.5.
The verification/test commands need no API calls or ignored run artifacts. Full
historical-run reproduction or replay needs the local data and captured responses;
the compact records allow score inspection without distributing those raw files.

## Earlier development experiments

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
