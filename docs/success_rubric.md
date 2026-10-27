# FaithfulMed success rubric

Owner: Carlin Verano (September task). 

**Implementation note (October 23):** Carlin's targets and open measurement
decisions remain the team's scoring guide. The newer live demo uses
[`faithfulmed_demo/roles/verifier.py`](../faithfulmed_demo/roles/verifier.py),
which returns `issues`, `supported_examples`, and `scope` after reading the
original note, atoms, draft, and retrieved passages. The `faithful`,
`unsupported_claims`, and `omissions` fields cited below describe the earlier
ADK scaffold; they are not the live demo's output schema. No demo run has yet
established the headline success rates in this rubric.

This page says what counts as success for FaithfulMed and how each result is
measured. Every target and definition here comes from a file already in the
repo, cited next to it. Anything the team has not decided yet is listed under
[Open decisions](#open-decisions) and has no made-up number.

## Inputs and outputs

The baseline's input and output fields are defined in the
[baseline task specification](../baseline/README.md#inputoutput-task-specification).
This rubric scores the `model_output` field. It uses `status` to decide which
records can be scored (see [Which outputs are scored](#which-outputs-are-scored)).

## Evaluation set

- **Source reports:** the 50 MTSamples reports in
  [`data/curated_baseline/`](../data/curated_baseline/README.md)
  (`mtsamples_curated_50.csv`). There are 48 medium-length reports plus two
  Allergy/Immunology exceptions.
- **Version:** `v3-medium-with-allergy-exceptions-frozen-2026-10-26`
  ([`selection_manifest.json`](../data/curated_baseline/selection_manifest.json)).
- **Source review completed; inputs frozen October 26.** All 50 source
  reports were retained unchanged: 31 accept and 19 accept-with-caveat decisions.
  [Per-report notes](../data/curated_baseline/REVIEW_AND_FREEZE.md) record source
  conflicts and preservation priorities. Use this fixed version for both
  baseline and ADK runs, preserving uncertainty in disputed source details.
- **Verifier calibration data:** MedAESQA's human accuracy and evidence-support
  labels ([`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md),
  "Datasets"; download steps in [`data/README.md`](../data/README.md)).

## Targets at a glance

All targets are from the "Success Criteria" section of
[`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md).

| Metric | Pass target |
| --- | --- |
| Readability | ≥80% of outputs at or below 8th-grade Flesch-Kincaid level |
| Faithfulness | ≥85% factual fidelity on the human-annotated test set |
| Hallucination (addition) rate | <10% of outputs contain a clinically meaningful unsupported claim |
| Improvement over baseline | ≥15% absolute improvement in faithfulness score, multi-agent vs. single-Gemini baseline |
| Verifier vs. human agreement | ≥80% agreement, Cohen's κ ≥ 0.6 |
| Omission rate | No target in the repo yet (tracked separately, see below) |

## Metrics

### 1. Readability pass rate

- **Definition:** the share of scored outputs that pass the readability check.
  An output passes when its Flesch-Kincaid (FK) grade is at or below 8, it is
  not a refusal, and it meets the optional word limit
  ([`evaluation/readability.py`](../evaluation/readability.py),
  `evaluate_readability`).
- **How it's computed:**
  - FK grade = `0.39 × words/sentences + 11.8 × syllables/words − 15.59`.
    Sentences are counted by `count_sentences`, which does not split on
    decimals or common abbreviations such as "Dr." and "e.g.".
  - The grade limit is `max_grade=8` by default. The word limit is
    `max_words=None` by default, which means no length limit.
  - An output counts as a refusal when it matches `REFUSAL_PATTERN` (for
    example, "I cannot help"). A refusal never passes.
  - `summarize_results` reports `readability_pass_rate`. Its denominator is
    outputs that were scored successfully (`evaluation_status == "ok"`).
- **Produced by:** the `evaluation/readability.py` script (`evaluate_outputs`,
  then `summarize_results`).
- **Pass target:** `readability_pass_rate` ≥ 0.80
  ([`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md)).
- **Data source:** `model_output` for each of the 50 evaluation reports.

### 2. Supporting readability measures (reported, no pass target)

The overview lists these alongside FK
([`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md),
"Evaluation metrics"). All of them are computed per output by
`evaluate_readability` in [`evaluation/readability.py`](../evaluation/readability.py):

| Measure | How it's computed |
| --- | --- |
| SMOG grade (secondary) | `1.043 × √(30 × words with 3+ syllables / sentences) + 3.1291`; left empty when an output has fewer than 3 sentences |
| Medical jargon density | words found in the starter `MEDICAL_TERMS` list ÷ total words |
| Output length | `word_count` and `sentence_count` |
| Refusal rate | refusals ÷ scored outputs (`summarize_results`) |

The data source is the same as for metric 1.

### 3. Faithfulness score

- **Definition:** how well an output sticks to the facts in the source note.
  The overview's target is "factual fidelity on the human-annotated test set,
  verified against human labels"
  ([`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md)).
- **How it's computed:** the Verifier compares the draft with the Extractor's
  atoms and returns `faithful`, `unsupported_claims`, and `omissions`
  ([`notebooks/adk_pipeline.py`](../notebooks/adk_pipeline.py), Verifier
  instruction). These field names come from the starter skeleton's
  placeholder Verifier and may change when the Verifier role
  (`faithfulmed_demo/roles/verifier.py`) is added. The exact score formula is
  not decided yet (see [Open decisions](#open-decisions)).
- **Faithfulness categories:** Rafi's rule-based rubric sorts MedAESQA
  sentences and answers into these categories
  ([`EDAs/MedAESQA/verifier_rubric.py`](../EDAs/MedAESQA/verifier_rubric.py)):

  | Category | Meaning |
  | --- | --- |
  | `fully_supported` | required sentence whose citations are all supporting |
  | `weakly_supported` | supporting evidence, but the sentence is not marked required, or another mixed case |
  | `unreferenced` | sentence with no citations |
  | `neutral` | at least one neutral evidence relation |
  | `irrelevant_evidence` | at least one "not relevant" relation |
  | `invalid_citation` | at least one invalid citation |
  | `contradictory` | at least one contradicting relation |
  | `empty_answer` | answer with no sentences |

  An answer takes its most serious sentence category, in this order:
  contradictory, invalid citation, irrelevant, neutral, unreferenced, weakly
  supported (`classify_answer`). This rubric is a baseline for analysis, not a
  replacement for human review
  ([`EDAs/MedAESQA/README.md`](../EDAs/MedAESQA/README.md)).
- **Produced by:** the Verifier agent. The rubric above is the rule-based
  reference for calibration.
- **Pass target:** ≥85%
  ([`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md)).
- **Data source:** human-annotated test set. Which set this is has not been
  decided yet (see [Open decisions](#open-decisions)).

### 4. Addition (hallucination) rate

- **Definition:** an *addition* is a claim in the output that is not supported
  by the source note or by the retrieved MedlinePlus text. The overview treats
  additions as hallucinations and asks for them to be tracked apart from
  omissions ([`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md),
  "Evaluation metrics").
- **How it's computed:** the share of outputs with at least one clinically
  meaningful addition. Additions come from the Verifier's `unsupported_claims`
  list ([`notebooks/adk_pipeline.py`](../notebooks/adk_pipeline.py)). That
  field comes from the starter skeleton and may change when
  `faithfulmed_demo/roles/verifier.py` is added. The skeleton Verifier only
  compares the draft with the Extractor's atoms, not with the source note or
  the retrieved MedlinePlus text, so it does not yet match this definition
  (see [Open decisions](#open-decisions), item 11).
- **Produced by:** the Verifier agent.
- **Pass target:** <10% of outputs
  ([`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md)).
- **Data source:** outputs for the 50 evaluation reports, checked against each
  source note and the `retrieved_context` saved with the output
  ([`baseline/README.md`](../baseline/README.md)).

### 5. Omission rate

- **Definition:** an *omission* is an Extractor atom that is missing from the
  draft. Each atom has a text, type, assertion status, and an exact source
  quote ([`extractor/EXTRACTOR_HANDOFF.md`](../extractor/EXTRACTOR_HANDOFF.md);
  schema in [`faithfulmed_demo/roles/extractor.py`](../faithfulmed_demo/roles/extractor.py)).
- **How it's computed:** the Verifier's `omissions` list for each output
  ([`notebooks/adk_pipeline.py`](../notebooks/adk_pipeline.py)). That field
  comes from the starter skeleton and may change when
  `faithfulmed_demo/roles/verifier.py` is added. The repo does not yet say
  whether the rate is counted per atom or per output.
- **Checking the Verifier:** MedAESQA has no omission labels, so it cannot be
  used to check the Verifier's omission calls. A small hand-labeled check is
  needed: a person marks which atoms are missing from a sample of drafts, and
  those marks are compared with the Verifier's.
- **Produced by:** the Extractor agent (atoms) and the Verifier agent
  (omissions).
- **Pass target:** none in the repo yet.
- **Data source:** outputs and Extractor atoms for the 50 evaluation reports,
  plus the hand-labeled sample.

### 6. Improvement over the single-Gemini baseline

- **Definition:** the multi-agent pipeline's faithfulness score minus the
  baseline's faithfulness score, in percentage points.
- **How it's computed:** run the frozen reports through the baseline and the
  multi-agent pipeline, then score both with the same faithfulness measure
  ([ADR-001](adr/ADR-001-september-single-model-baseline.md), Follow-up step 5).
  For a fair comparison, keep the example set, index snapshot, embedding model,
  SDK version, Gemini model, and prompt version the same, and record them
  ([`baseline/README.md`](../baseline/README.md), "Prompt and reproducibility").
- **Produced by:** the `baseline` package (one retrieval step, one Gemini call)
  and the ADK pipeline, both scored by the Verifier.
- **Pass target:** ≥15 percentage points (absolute)
  ([`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md)).
- **Data source:** the frozen 50-report evaluation set.

### 7. Verifier vs. human agreement

- **Definition:** how often the Verifier's faithfulness labels match human
  labels.
- **How it's computed:** `verifier_agreement` in
  [`notebooks/eval_harness.py`](../notebooks/eval_harness.py) returns accuracy
  and Cohen's κ (from scikit-learn) for two equal-length label lists.
- **Produced by:** the Verifier agent's labels, scored by
  `notebooks/eval_harness.py`.
- **Pass target:** accuracy ≥ 0.80 and Cohen's κ ≥ 0.6
  ([`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md)).
- **Data source:** MedAESQA human accuracy and evidence-support labels
  ([`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md), October
  milestone).

## Which outputs are scored

- Only records with `status == "ok"` are scored for readability. Retrieval or
  API failures are counted separately and are not scored as empty, easy-to-read
  answers ([`baseline/README.md`](../baseline/README.md), "Evaluation handoff").
  `evaluate_outputs` marks other records as `skipped`
  ([`evaluation/readability.py`](../evaluation/readability.py)).
- `status: ok` only means the code finished. It is not a faithfulness verdict
  ([`baseline/README.md`](../baseline/README.md)).
- Refusals are scored but always fail readability; they are reported as the
  refusal rate ([`evaluation/readability.py`](../evaluation/readability.py)).

## Other success criteria

The overview also requires an ablation table, a leaderboard of at least three
models, and the working artifacts (repo, demo, report). These are described in
[`Challenge-Project-Overview.md`](../Challenge-Project-Overview.md) and are not
repeated here.

## Open decisions

1. **Experiment provenance.** Source review and input freezing are completed.
   Record the frozen input version with the index snapshot, model, prompt,
   SDK, and retrieval settings ([ADR-001](adr/ADR-001-september-single-model-baseline.md)).
2. **Counting `no_context` and failed runs.** ADR-001 says how these count in
   final scores "still needs agreement". This matters most for the readability
   pass rate, whose current denominator leaves them out.
3. **Faithfulness score formula.** Decide whether it is the share of outputs
   the Verifier marks `faithful`, a per-claim or per-atom score, or something
   else.
4. **Which human-annotated set the 85% target uses.** MedAESQA has human
   labels, but the 50 MTSamples reports do not.
5. **Mapping rubric categories to labels.** Decide which `verifier_rubric.py`
   categories count as faithful when comparing the Verifier to humans (for
   example, where `weakly_supported` and `unreferenced` fall).
6. **What "clinically meaningful" means** for the hallucination target.
7. **Omission target and unit.** There is no pass target yet, and it is not
   decided whether omissions are counted per atom or per output.
8. **Omission hand-check.** Decide the sample size, who labels it, and whether
   it gets its own agreement target.
9. **Word limit.** `max_words` is off by default. Decide whether outputs need a
   length limit to pass readability.
10. **Two readability implementations.** They differ in two ways:
    - **FK grade:** `notebooks/eval_harness.py` uses textstat's built-in FK,
      while `evaluation/readability.py` uses its own sentence count.
    - **Jargon density:** `notebooks/eval_harness.py` counts textstat's
      "difficult words" (words not on the Dale-Chall familiar-word list),
      while `evaluation/readability.py` counts words from its `MEDICAL_TERMS`
      list.

    This rubric uses `evaluation/readability.py`. The team should confirm that
    choice so all reported numbers use the same one.
11. **What the Verifier checks additions against.** The addition definition
    covers the source note and MedlinePlus, but the skeleton Verifier in
    [`notebooks/adk_pipeline.py`](../notebooks/adk_pipeline.py) only compares
    the draft with the Extractor's atoms. Decide whether it should check
    against the atoms, the original `source_report`, the `retrieved_context`,
    or a mix of these. Checking only the atoms would wrongly flag correct
    plain-language definitions taken from MedlinePlus, and would miss facts
    the Extractor left out.
