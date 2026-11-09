# Clinical scoring v2 results - November 8, 2026

The revised clinical scorer produced **10/10 valid assessments**, versus **5/10**
previously, on the exact same saved five-report baseline/ADK pilot. All input digests,
restored quotations, IDs, coverage records and calculated metrics were revalidated.
This is improved scoring completion, not 100% clinical accuracy.

| Check | Result |
|---|---|
| Valid pilot assessments | **5/10 → 10/10** |
| Advisor examples | **4/4** match every expected count |
| Controlled regression cases, after transport recovery | **6/7 → 6/7**; no demonstrated accuracy gain |
| Individual controlled checks | **15/16 → 15/16** |
| Local scorer/regression tests | **42 passed**, plus four subtests |
| MedAESQA calibration | Not rerun; historical 50% agreement / kappa 0.00 remains unchanged |

## Improvements demonstrated

The model selects code-assigned output/report/context IDs; Python recovers exact
source text. This avoids generated quotations with missing Markdown or invented
ellipsis. Strict checks still require every output block and fixed key fact to be
accounted for. A new partial-coverage status represents included-but-incomplete facts.

Long non-streaming responses repeatedly disconnected. The streaming transport and
180-second per-request timeout completed those cases. Valid saved results were reused
after revalidation. Other proposals were allowed a bounded correction; for one
specific consistency failure, a compact model check revisits only report presence and
addition flags. Python applies the model's explicit corrections and validates the full
result. It does not assign preferred semantic labels or alter expected test outcomes.

Concrete findings now captured in the pilot include:

- Allergy draft: missing post-discharge update and missing atenolol warning/rationale.
- Cystitis draft: unqualified bladder-denial/source-discrepancy concern, added dose unit,
  and incomplete history coverage, instead of the old assessment's all-supported result.
- CT draft: missing noncontrast diagnostic limitation and partial explanation of the
  renal/adrenal wording discrepancy. Two linked checklist entries are not two nodules.

## Preserved failures and remaining concerns

The initial non-streaming ID run and the intermediate streaming run remain saved,
including disconnects and invalid consistency proposals. The final run reused eight
valid assessments and recovered the remaining two. Every correction is auditable in
the result's attempts and previous-result records. No source text or answer was changed.

The controlled regression labels were fixed before calls and excluded from model
inputs. Both scorers disagree with the predefined clinical-significance expectation
for an unstated dose unit, even though both flag a distortion. No expectation was
changed to claim a pass. These seven synthetic development checks are not independent
clinical gold or held-out calibration.

The revised scorer also counts a scope disclaimer in the cystitis output as an
unsupported proposition. That is a remaining false positive in claim selection.
It is retained and disclosed, not removed to improve reported faithfulness. Individual
claims and severity judgments still need validation; exact anchors do not prove meaning.

Claim segmentation differs between versions. Changes in model-assigned faithfulness
percentages are neither improvements in generated answers nor proof of judge accuracy.
Drafts remain outside released-answer summaries. The newer readability-rewrite outputs
were not rescored in this experiment; their older scores cannot be transferred.

## Reproduce and inspect

- [Implementation and commands](CLINICAL_SCORING_V2.md)
- [Detailed before/after report](../data/comparison_results/five_report_pilot_2026-11-07_v1/CLINICAL_SCORING_V2_COMPARISON.md)
- Final results: `data/comparison_results/five_report_pilot_2026-11-07_v1/clinical_scores_source_ids_final_v2.json`
- Offline report reproduction: `python -m evaluation.report_clinical_scoring_v2`

The live Verifier, Gradio release behavior and MedAESQA judge were not replaced by this
post-generation scorer. Nothing was committed or pushed. The remaining work is semantic
validation, especially claim granularity, nonclinical framing, and clinical significance.
