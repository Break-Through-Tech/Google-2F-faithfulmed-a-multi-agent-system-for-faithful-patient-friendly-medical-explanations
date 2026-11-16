# Citation calibration and report-evaluator status

Updated November 16, 2026. Consolidated findings; intermediate experiment scripts
and detailed investigations remain local.

## Final reported result

**Citation-support agreement: 25/31 (80.65%); Cohen's kappa: 0.609.** This is
the project's final reported retrospective citation-evaluator comparison. Both
numerical goals (80% agreement and kappa 0.60) were met on this sample, with no
technical failures or retries. The original evaluator scored 23/31 (74.2%), kappa
0.498, on the same cases: two additional reference matches and no losses.

The available-data constraint was question-level independence. After the last
four reserved question groups were evaluated, no unexposed held-out question
groups remained under the existing split and recorded-exposure rules. Additional
raw pairs still existed, but they did not provide another untouched question-level
validation sample. We finalized using the existing MedAESQA collection, preserving
the original independent result and clearly separating subsequent development
and retrospective results. This score evaluates citation support, not the full
medical-report Verifier, omissions, or clinical accuracy.

Only the final implementation and compact evidence are needed from GitHub:

- [Portable final evaluator](citation_evaluator.py), including `judge(case)` and
  the bounded retry-policy helper. Only question, sentence and evidence are sent
  to the model; the existing contiguous-source validator remains unchanged.
- [Locked final prompt and settings](frozen/citation_evaluator_final_2026-11-16.json).
  The full prompt is in `specification.prompt`; its fingerprint, schema, model,
  transport settings, retry policy and dependency hashes are included.
- [Final case-level results](results/citation_evaluator_final_2026-11-16.json).
  Includes the 31-case original/improved comparison, the separate 32-case
  development comparison, ablation outcomes, original labels, decisions, reasons,
  quote locations, source/response hashes, coverage, confusion counts and gains/losses.

Verify every published score offline, without an API key or raw data downloads:

```powershell
.\.venv\Scripts\python.exe -m evaluation.citation_evaluator verify
.\.venv\Scripts\python.exe -m pytest tests/test_citation_evaluator.py -q
```

The seven portable evaluator checks passed. Raw responses, full abstracts,
exposure inventories, intermediate scripts and detailed reports remain local;
they are not required to recompute the published metrics. The experimental
script names below describe that local archive, rather than additional files
needed to use the final evaluator. The live ADK/Gradio Verifier was not switched
by finalizing these citation-evaluation results.

## Comparison and investigation record

### November 16: locked improved candidate on the earlier 31-case batch

**Retrospective result: 25/31 agreement (80.65%), Cohen's kappa 0.609, zero
technical failures and zero retries.** All 31 assessments were valid on the first
attempt. Both numerical targets were met on this retrospective comparison.

| Evaluator | Matches / cases | Agreement | Kappa | Failed |
| --- | ---: | ---: | ---: | ---: |
| Preserved original baseline | 23/31 | 74.2% | 0.498 | 0 |
| Locked improved candidate | 25/31 | 80.65% | 0.609 | 0 |

This uses the exact combined prompt previously tested on the 32-case development
sample: population preservation, descriptive-versus-associational inference, and
one contiguous exact source witness. The earlier 31 case IDs, original references,
cached full title/abstract inputs, schema, model, temperature, and bounded retry
policy were fixed before calls. No earlier response was substituted into this run.

Two original disagreements changed to reference matches, with **no losses**:
question 116 / PMID 33659106 (weight loss and obstructive sleep apnea), and
question 147 / PMID 34251531 (investigational anti-inflammatory therapies for
atherosclerosis). Six reference disagreements remain. Confusion counts are 15
supporting matches, 10 non-supporting matches, five false negatives and one false
positive relative to the original labels.

The older cases had already been inspected during prior work. This is a
retrospective comparison, not fresh independent held-out validation. The original
74.2%, kappa 0.498 result and the newer 32-case results remain preserved. Because
the comparison uses a historical baseline, the two gains cannot be attributed
solely to the newest clarifications rather than model variation or earlier
prompt changes. No runtime Verifier configuration was switched.

Protocol, complete raw responses, and summary are local under
`data/calibration_results/retrospective_31_2026-11-16_v1/` as `protocol.json`,
`run.json`, and `summary.json`. The run digest is
`b1d2cde6187e649d75881c6fd69abbfd588d77af50e70c4a18611c1d7b554fa0`.
Agreement/kappa were independently recomputed; all 31 source/reference bindings,
quote offsets, original artifacts and the locked candidate were verified.
An offline reporting adapter removed a redundant legacy `case_id` field inside
historical attempts for the paired summary; no decision or label changed. The
portable verification command above recomputes the published comparison without
needing that local adapter or making model calls.

### Development improvement after inspecting the 32 cases

**The combined development candidate reached 26/32 agreement (81.25%), kappa
0.625, with zero technical failures and no retries.** The preserved fresh run
remains 24/32 (75.0%), kappa 0.500. These are now inspected development cases:
the new result meets the numerical targets on this sample, but is not a new
held-out calibration result and does not switch the live report Verifier.

Two prompt clarifications were first tested independently: preserve the population
of a clinical outcome, and distinguish descriptive subgroup observations from
association or causation. Each passed six artificial boundary checks, as did the
unchanged control. Those checks establish expected boundary behavior, not an
independent human-labeled accuracy gain.

| Development arm | Matches / valid assessments | Agreement on valid | Kappa | Unresolved failures | Matches / all 32 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Repeated unchanged control | 23/31 | 74.2% | 0.485 | 1 | 23/32 |
| Population clarification alone | 24/31 | 77.4% | 0.549 | 1 | 24/32 |
| Inference clarification alone | 24/31 | 77.4% | 0.547 | 1 | 24/32 |
| Combined clarifications and explicit contiguous-quote instruction | 26/32 | 81.25% | 0.625 | 0 | 26/32 |

Do not mistake the population-only percentage for a clear improvement: on its
30 shared valid pairs with the control, it had one gain and one loss, with both
scoring 23/30, kappa 0.533. Inference-only had two gains and one loss on 31 shared
valid cases: 24/31, kappa 0.547, versus control 23/31, kappa 0.485. It was a modest
development gain rather than a regression-free fix.

The remaining output failures included joined, noncontiguous quotations and an
invented Unicode sequence. They were retained as invalid; neither the validator
nor old responses were repaired to manufacture a score. The subsequent combined
candidate explicitly asks for one complete supported assertion with a short,
contiguous, exact source witness. It retains the same schema, whitespace-only
validator, full inputs, original references, model, temperature, and retry policy.
No answer-context expansion or whole-sentence-support requirement was introduced.

Before cohort calls, this adaptive combined experiment froze its prompt and a
16-case artificial boundary gate, covering both clarifications and quote/dose
integrity. All 16 passed, then all 32 development cases returned valid first
responses. Combining rules and formatting means the overall improvement cannot
be attributed to just one change. Model variation and this sample's four question
clusters remain limitations.

Compared with the preserved 32-case run, there were **three gains and one loss**:
the mouse age/healing claim (118/35602595), descriptive thyroid-adherence inference
(135/30636753), and antihypertensive causal inference (135/21041167) changed to
match their references. The survival-efficacy claim (145/25022950) changed from
support to neutral, creating a new reference disagreement: the model now requires
stronger evidence of improved survival from a noncomparative phase-II study.
That disagreement is retained, not relabeled or hidden.

Final confusion counts: 12 supporting matches, 14 non-supporting matches, two
false positives relative to the references, and four false negatives. Previously,
there were five false positives and three false negatives. Thus the gain includes
a tradeoff toward more conservative support decisions. On the 31 shared valid
pairs with the repeated control, the combined candidate scored 25/31, kappa 0.611,
versus 23/31, kappa 0.485. This paired comparison also had three gains and one loss.

The experimental prompts are in `citation_scope_development.py` and
`citation_scope_combined.py`; their versioned protocols, every response, attempts,
first/post-retry summaries, and gain/loss identities are preserved locally in
`data/calibration_results/citation_scope_development_2026-11-15_v1/` and
`data/calibration_results/citation_scope_combined_2026-11-15_v1/`.
The combined run digest is
`8c115ca2977de3ef29c5b168deb570f38f14589f1b27b7a07640e9389475517d`.
The scores were independently recomputed, all source quote offsets and original
case/reference bindings checked, and the frozen baseline verified unchanged.
Eight local request-isolation/validation checks passed. A transient Windows
checkpoint-replacement error was handled by retrying only local storage; the
failed write occurred before the next API call, and completed calls were not repeated.

Keep the combined version as the preferred **development candidate**, not a
replacement for the frozen independent result. Six reference disagreements remain.
Any later independent evaluation needs a new reserved sample; do not claim this
retuned sample is still untouched. No Git commit/push or runtime promotion was made.

### Fresh fixed 32-case evaluation completed November 15

**Final agreement: 24/32 (75.0%); Cohen's kappa: 0.500. The 80% agreement and
0.60 kappa targets were not met.** No settings, references, or cases were changed
after seeing these outcomes.

| Pass | Valid assessments | Matches / valid | Agreement on valid | Kappa | Failed | Matches / all selected |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| First attempt | 30/32 | 23/30 | 76.7% | 0.533 | 2 | 23/32 (71.9%) |
| After predefined technical retries | 32/32 | 24/32 | 75.0% | 0.500 | 0 | 24/32 (75.0%) |

There were 34 model calls: all 32 first attempts, then one identical-call retry
for each of two `quote_not_in_document` failures. Both retries became valid;
one matched its reference and one did not. No valid disagreements were retried.
Final counts: 13 supporting matches, 11 non-supporting matches, five predicted
support/reference non-support disagreements, and three in the opposite direction.
All responses, including invalid first responses, are saved. Eight disagreements remain.

The summary and complete attempts are respectively
`data/calibration_results/unused_validation_summary_2026-11-15_v1.json` and
`data/calibration_results/unused_validation_run_2026-11-15_v1.json`.
The run digest is `eaaed1d637e0859bf363831c9a3867c66f24d653f938aa7ef3639fb95ec1e713`.
All 32 bindings, 34 captured responses, retry eligibility/order, and independently
recomputed agreement/kappa were verified. All 24 preparation/execution checks passed.

This is a different sample from the reviewed 31-case replay (83.9%, kappa 0.668),
so the difference is not a paired code-regression measurement. Technical coverage
is complete, but the live whole-report Verifier remains uncalibrated. The descriptive
case-level agreement Wilson interval is 57.9%-86.7%, without adjustment for four
question clusters. Future tuning on these disagreements makes this sample
development data for that revision; another run on it is not fresh validation.

### Offline inspection of the eight disagreements

Checked each saved judgment against the full cached abstract, its original
dataset annotations, and preceding answer sentences where needed to identify
missing context. No model calls, prompt changes, reference changes, or score
changes were made. These interpretations are diagnostic, not replacement gold labels.

| Question / PMID | What the inspection found | Recommended handling |
| --- | --- | --- |
| 131 / 33273813 | Similar-to-placebo adverse events are not identical to saying the preceding high-dose effects are clinically insignificant. The payload also omits the antecedent of “these effects.” | Context/paraphrase boundary; do not automatically flip it. |
| 118 / 25165705 | A treated alkali-burn experiment reports healing in 48 hours; this does not establish typical untreated healing of most minor injuries. | The model's conservative decision is defensible; preserve the reference disagreement. |
| 118 / 30059040 | A mouse abrasion abstract directly describes re-epithelialization. The model supports the regeneration component; human applicability and remaining wording are separate questions. | Partial-support/population boundary, not a clear quote or extraction error. |
| 118 / 35602595 | The model generalizes an age-related healing result observed in mice to a patient-facing claim without retaining species. | First development candidate: population preservation, with supported-mechanism controls. |
| 135 / 30636753 | The model treats uncontrolled TSH in many non-adherent patients as an association, despite the abstract reporting no statistically significant association with adherence. | First development candidate: descriptive observations versus association/causation. Nonsignificance is not proof of no effect or an automatic contradiction. |
| 135 / 21041167 | Blood pressure fell after supervised antihypertensives, but the model calls this confirmation of a causal nonadherence claim. | Reasoning is overstated; the binary label remains debatable under “can lead” wording. |
| 145 / 32489011 | Cardiac side effects are mentioned; myocarditis is not. The model supports the broad category under the current illustrative-example rule. | General-category versus essential-specific-example boundary; do not silently require complete coverage. |
| 131 / 23392793 | The source recommends LABA plus ICS in asthma but does not name formoterol. An earlier answer sentence supplied the LABA/formoterol bridge, omitted from the payload. | Test context separately. Generated answer context can clarify meaning but is not independently verified evidence; retain asthma/COPD restrictions. |

No conflicting duplicate binary references were found in these eight cases.
Semantic ambiguity here is different from two annotations explicitly disagreeing
on the same pair. Also checked two correctly matched controls: PMID 14985101 has
a supporting mouse-mechanism reference, and PMID 31598519 supports one component
while other listed factors remain unaddressed. Consequently, blanket rejection
of animal studies or every partially supported sentence would risk regressions.

The detailed local review, original annotation excerpts, saved reasons, source
quotes, and diagnostic answer context are in
`data/calibration_results/unused_validation_disagreement_review_2026-11-15_v1.json`.
Every quoted source span and case/reference identity was checked against the
preserved artifacts. Next: test population preservation and descriptive-versus-
associational evidence as separate development changes, including positive
controls. Handle answer-context input in a separate experiment. None of these
findings guarantees a label flip or a higher score; retain all original results.

**Independent evaluation sample prepared November 15:** 32 previously unused
statement-document pairs, with 16 supporting and 16 non-supporting references
across four original held-out question groups. All 32 PMID-matched titles and
complete available PubMed abstracts were retrieved and verified. No repeated
documents or normalized statements are included. Selection was fixed before
source retrieval; no cases were replaced. Its completed run is recorded above.

The separate local cohort manifest,
`evaluation/frozen/unused_validation_cohort_2026-11-15_v1.json`, binds every payload
and original reference to the frozen evaluator fingerprint. The published final
case-level results retain the case identities, references and payload/source hashes.
Its cohort fingerprint is
`f3698e1674e1183cb76a9b9bad4b2a1bd3e70641a3273fca52a32ba65a35cbb6`.
This is a balanced diagnostic sample from four clustered topics, rather than a
deployment prevalence sample or 32 independent topics. Unused status is relative
to the recorded exposure audit; unrecorded external use cannot be certified.
Current PubMed abstracts are not guaranteed to reproduce annotation-time text.

Selection, raw PubMed XML, parsed sources, and the ready-to-run suite are kept
locally under `data/calibration_results/unused_validation_*_2026-11-15_v1.*`.
Preparation is reproducible with `python -m evaluation.prepare_unused_cohort`
and its `select`, `fetch`, and `freeze` actions. These actions never call Gemini
and refuse to replace differing frozen artifacts. A future run must use this
cohort with the frozen configuration and its existing bounded retry policy,
retain every selected case, and report first-attempt and post-retry results
separately. The configuration manifest's `not_selected` field records the earlier
configuration-freeze stage; this later, separate cohort supplies the dataset binding.

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
drift and requires a separately frozen cohort before model calls. At configuration
freeze, no independent cohort had been selected. The later 32-case selection,
source verification, and completed evaluation are recorded above.

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
The original configuration-freeze commit contained no independent sample. The
separate cohort and its completed evaluation are now recorded above.

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
