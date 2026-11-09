# Clinical scoring with source IDs

The clinical evaluator now has a versioned alternative to copied quotations:
`python -m evaluation.clinical_scoring_v2`. This evaluates saved answers; it does not
change the live ADK Verifier or the MedAESQA calibration results.

## What changed

- The model selects output and evidence block IDs. Python recovers exact source text
  and offsets, so a model cannot invent an evidence quotation or omit Markdown markers
  from an output quotation. All original characters are preserved in the block tables.
- Every output block must be claimed or explicitly ignored as nonfactual/duplicate.
  Several independent claims can link to one block. This structural check is not proof
  that the model extracted every proposition or correctly ignored a block.
- `partial` coverage distinguishes an incomplete combined fact from a completely
  missing fact. Full coverage requires all specified parts and qualifications.
- Instructions explicitly address unstated units, medication rationale, background
  additions, source conflicts, and negative history versus a clearly new diagnosis.
- Strict schema/ID/coverage checks still reject invalid assessments. One bounded
  correction can receive the validation category and previous proposal, never reference
  labels or expected counts. A transient connection error can also use that one retry.
  There are at most two new evaluator requests per output per invocation. Deliberate
  recovery runs retain earlier requests separately. Access/quota errors stop the run.
- Large responses use streaming with a 180-second per-request timeout. This addresses
  observed disconnects on long non-streaming assessments. An interrupted earlier run
  remains preserved. `--initial` reuses valid v2 assessments only after input-digest
  and ID/coverage revalidation; prior failed records are retained in the new result.
- Raw structured proposals and failed/valid attempts are preserved. No semantic labels
  are changed by Python to increase a score; the program restores anchors and computes
  counts from the model's accepted assessment.

For the specific context-only/nonaddition inconsistency, the correction is compact:
the model checks only the flagged claims against the report and returns addition flags
and report IDs. It may retain `is_addition=false` if it supplies actual report evidence.
Otherwise it can identify an addition. Python applies only those model-provided fields,
retains the original proposal and correction, and validates the complete assessment
again. It does not force a preferred clinical support label or regenerate unrelated claims.

The original scorer and historical results remain available. The pilot's earlier
Markdown-restoration helper remains historical; this implementation does not need
to accept shortened or paraphrased evidence as a quotation.

## Metrics and denominators

The existing claim-level faithfulness, additions/distortions, and output-level
hallucination formulas are retained. Drafts stay outside released-answer summaries.
Generation failures, refusals, no-claim outputs, and evaluation failures are reported
separately and never receive a perfect score.

Additional fields:

| Field | Meaning |
|---|---|
| `omissions` | Entire fixed facts absent from the answer. |
| `partial_key_facts` | Fixed facts with a correct included part and an absent required part. |
| `incomplete_key_facts` | Missing plus partial facts; distorted facts are counted separately. |
| `fully_covered_key_facts` | Facts with all required parts represented correctly. |
| `missing_detail` | The absent part, written explicitly for missing/partial coverage. |

These counts refer to fixed checklist entries. Two linked entries describing the
same source discrepancy do not establish two independent clinical errors; retain
their fact IDs and report affected outputs separately.

Pure missing counts are not directly comparable with v1 when v1 represented a partly
included combined fact as wholly missing. Compare the detailed coverage categories.
Claim segmentation can differ between versions, so a changed faithfulness fraction
does not by itself show a more accurate judge or a better generated answer.

## Run

Use the standard paired-runner scoring export and existing frozen key-fact inventories:

```powershell
.\.venv\Scripts\python.exe -m evaluation.clinical_scoring_v2 --input data/comparison_results/five_report_pilot_2026-11-07_v1/scoring_inputs.json --output data/scoring_results/my_clinical_source_ids_run.json
```

The command resumes completed records only when inputs, model, prompt, schema, version,
and retry policy match. Changed settings require a new result path. The standard input
fields are `case_id`, `system`, `generation_model`, `output_kind`, `run_status`,
`source_report`, `output`, `key_facts`, and `retrieved_context`.

The final pilot result is `clinical_scores_source_ids_final_v2.json`, which resumes
`clinical_scores_source_ids_stream_v2.json` via `--initial`. That streaming pass retains
the earlier non-streaming ID run, `clinical_scores_source_ids_v2.json`. All are in the
original pilot result directory. For a fresh run, omit `--initial` and choose a fresh
output path. Reusing a valid record is not counted as a new model call.

## Validation and interpretation

Local tests check exact character recovery, invalid IDs, missing output/fact accounting,
partial coverage, duplicate claims, context-only patient evidence, addition consistency,
bounded correction/transport retries, and exclusion of reference labels from requests.
The four advisor examples retain their expected arithmetic and live judgments.

Seven new controlled synthetic development cases test policy distinctions. They are
not independently annotated clinical gold or MedAESQA held-out cases. On matched
completed assessments, both the old and new scorers passed **6/7** case-level checks
(15/16 individual checks). Both disagree with the predefined clinical-significance
expectation for an unstated dose unit, despite flagging it as a distortion. That
remaining judgment issue is preserved; no test expectation was changed after the run.
The new representation correctly labels the partly included follow-up as `partial`,
where the old schema could only label the combined fact wholly missing.

Technical validity, semantic correctness, and answer faithfulness are distinct results.
No improvement in MedAESQA agreement or kappa is claimed by this clinical-scoring work.
For measured pilot completion and case findings see [the run report](CLINICAL_SCORING_V2_RUN.md).
