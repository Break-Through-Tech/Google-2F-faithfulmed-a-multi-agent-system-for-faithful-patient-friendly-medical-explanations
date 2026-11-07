# Offline support/reference audit - November 7, 2026

Applied [support-conflict-v1](SUPPORT_CONFLICT_POLICY.md) without service calls. Read the original dataset, fixed 80-case suite, and existing six-document cache. Did not read new model predictions, change labels, discard old results, or build a new benchmark.

## What the audit found

| Check | Development | Held-out |
| --- | ---: | ---: |
| Selected cases inspected structurally | 40 | 40 |
| Opposite binary references in the same document/assertion group | 14 | 8 |
| Missing cached title/abstract | 34 | 40 |
| Additional selected occurrence of an already selected document/assertion | 0 | 1 |
| No structural flags with context already cached | 2 | 0 |

Flags overlap; do not subtract every column to calculate a new cohort. The two structurally ready cases are **not** evidence of semantic validity or a passing benchmark. Blank snippets were included when inspecting document labels. This is why the prior six-case investigation's three nonblank binary conflicts become four when all document references are considered. No majority voting was used.

All 80 selected cases were matched against the dataset's citation records, including unselected duplicates. The audit did not semantically annotate all dataset sentences. Held-out review was limited to identifiers, reference consistency, duplicates, and cache availability; no held-out answer text appears here.

Machine-readable evidence, including every selected case and its matching reference records:
`data/calibration_results/support_conflict_audit_2026-11-07_v1.json`.

## Six already-seen development cases: coverage concerns

These are desk-review observations against the cached titles/abstracts, not replacement gold labels or fresh model results.

| Question / PMID | Evidence establishes | What it does not establish clearly | Action |
| --- | --- | --- | --- |
| 144 / 16810473 | Lifestyle measures for hypertension are recommended. | The abstract does not enumerate every item in the sentence's weight/diet/exercise/alcohol list. | Flag partial coverage and conflicting supporting/not-relevant references. |
| 128 / 36968131 | Results explicitly compare elevated ALT/AST prevalence with the adult population. | A selected neutral label is not an uncontested reference; the study population/context also matters. | Keep supporting/neutral/not-relevant references together as ambiguous; no automatic relabel. |
| 139 / 35172902 | Anaemia and several obstetric complications in active anorexia pregnancies. | Hyperemesis gravidarum is not established in the cached abstract. | Flag partial coverage and mixed references. |
| 126 / 33484483 | Nondisjunction can result in an aneuploid egg. | The broad cell-division definition in the answer is not spelled out completely. | Keep the neutral reference; treat the broad-definition support question as a scope diagnostic. |
| 142 / 24042856 | NSAID use can raise systolic blood pressure in users of antihypertensives. | The long sentence's other drug classes are not covered by this study. | Explicitly distinguish support for the NSAID assertion from full-sentence coverage, despite consistent supporting labels. |
| 146 / 24422773 | SSRIs have evidence for PTSD, including discussion of residual symptoms after nondrug care. | SNRIs and inability to access psychotherapy are not explicitly established here. | Flag partial coverage and conflicting supporting/neutral references. |

Cases 126 and 142 have no structural flags, but both still illustrate why reference scope must be settled before treating `supports_sentence` as complete sentence coverage. More context alone does not solve this.

## What remains unchanged

- Original snippet pilot: 3/6 agreement, kappa 0.00.
- Same-six title/abstract diagnostic: 4/6 agreement, kappa 0.33.
- These remain historical development diagnostics. There is no new accuracy or kappa result from this audit.
- The original 34 untested development cases and all 40 held-out cases remain unscored.
- No production Verifier, Refiner, calibration prompt, or scorer behavior was changed.

## Reproduce without network access

Choose a new output filename if the audit already exists:

```powershell
.\.venv\Scripts\python.exe -m evaluation.audit_support_references --output data/calibration_results/support_conflict_audit_reproduction.json
```

The script validates the dataset hash and question separation, retains original reference records, checks context hashes, and refuses to overwrite existing output. It has no service-call path. Next steps and the API gate are in the policy; do not simply resume the old snippet runner as if this audit fixed its task definition.
