# Extractor Pilot Review

Owner: Vaibhavi Srivastava
Review date: 2026-11-18
Status: Five of five saved pilot traces inspected; fixes pending.

## Purpose and Method

Compare saved Extractor atoms with their source reports, focusing on:
- Medication doses, schedules, and durations.
- Negation and assertion status.
- Left/right locations.
- Measurements and qualifiers.
- Uncertainty, pending results, and conditional instructions.
- Missing information and source discrepancies.
- Whether source quotes provide enough supporting context.

This review was completed with LLM assistance using the saved
November 8 readability-pilot traces. No new model calls were made
to the FaithfulMed pipeline, and no pipeline code was changed.

Results folder:
data/comparison_results/five_report_readability_2026-11-08_v2/traces/

Saved traces remain unchanged and are not included in this commit.

## Report 3606: CT Abdomen and Pelvis

Trace: row3606-adk-gemini-3.8-flash-1750db84e3-attempt1.json

### Details Preserved

- Measurements including 1.9 cm, approximately 29 Hounsfield
  units, 8 mm, and approximately 2.7 cm.
- Left/right locations in the inspected findings.
- Uncertainty such as "suggestive of cirrhosis."
- Recommended lung-nodule follow-up in 3 months.
- Dedicated adrenal CT or MRI described as a possible further
  assessment, rather than a completed procedure.

### Issues Observed

1. Missing examination limitation:
   The source states that noncontrast technique limits evaluation
   of the solid abdominal organs. No atom explicitly preserves
   this limitation.

2. Source discrepancy not explicitly flagged:
   The findings describe a left renal nodule, while the impression
   describes an indeterminate left adrenal nodule.
   Both statements appear in separate atoms without identifying
   the discrepancy. Downstream text could present them as two
   independent findings.
   Their relationship must remain unresolved rather than guessed.

### Follow-Up

Preserve examination limitations explicitly. Discuss how the
Extractor and downstream agents should represent source
discrepancies without deciding which statement is correct.

## Report 3808: Cystitis / Diabetes

Trace: row3808-adk-gemini-3.8-flash-1750db84e3-attempt1.json

### Details Preserved

- Micronase 2.5 mg, QAM schedule, and quantity #30.
- Bactrim 400/80, BID schedule, and quantity #30.
- No unit added to Bactrim and no treatment duration invented
  from the tablet quantity.
- Uncontrolled type II diabetes and acute cystitis.
- Endocrinology consultation and CBC described as planned,
  not completed.

### Issues Observed

1. Source discrepancy not flagged:
   The source denies bladder disorder but later diagnoses acute
   cystitis. Both statements are extracted without identifying
   the apparent discrepancy.

2. Quotes lose negation context:
   Several negated atoms quote only a condition name.
   For example, the hypertension atom quotes only "hypertension",
   omitting the surrounding "does not have" wording.
   The full source supports the negation, but the quote alone
   does not demonstrate it.

3. Assertion-label ambiguity:
   "Patient is afebrile" is marked negated.
   The intended meaning is no fever, but the relationship between
   an already-negative description and its assertion label needs
   a documented convention. Similar examples include "nontender".
   This is a representation concern, not proof that downstream
   agents reversed the meaning.

### Attribution

The added Bactrim unit observed in the generated explanation
was not present in these saved Extractor atoms. It should not
be attributed to the Extractor.

### Follow-Up

Retain enough quote context to support negation. Clarify the
assertion convention and handling of apparent source discrepancies.

## Report 3938: COPD Discharge

Trace: row3938-adk-gemini-3.8-flash-1750db84e3-attempt1.json

### Details Preserved

- All five prednisone taper steps:
  - 40 mg orally daily for 3 days.
  - 30 mg orally daily for 3 days.
  - 20 mg orally daily for 3 days.
  - 10 mg orally daily for 3 days.
  - 5 mg orally daily for 2 days.
- Levaquin 750 mg orally daily for 5 more days.
- Protonix 40 mg orally daily.
- Negative pulmonary embolism test distinguished from the
  abnormal cardiac scan and positive reversible ischemia finding.
- Ejection fraction of 55%.
- Cardiology follow-up in one week.
- Primary-care follow-up tomorrow.
- Hematology follow-up without inventing a date.
- Conditional emergency-return instructions.

### Issues Observed

1. Allergy quotes lack context:
   The allergy atoms quote only the medication names lisinopril
   and penicillin. The full source supports the allergies, but
   including the ALLERGIES heading would make that relationship
   explicit in the supporting quotes.

2. Assertion-label ambiguity:
   "Patient is afebrile" is marked negated, repeating the
   representation concern observed in report 3808.

### Follow-Up

Include allergy-heading context in quotes and clarify assertion
labeling. The targeted checks did not identify a changed taper
schedule or reversed cardiac finding.

## Report 2964: Carotid Ultrasound

Trace: row2964-adk-gemini-3.8-flash-1750db84e3-attempt1.json

### Details Preserved

- Left internal carotid narrowing retains "at least 50%"
  rather than becoming exactly 50%.
- Right-sided plaque retains the absence of evidence for
  greater-than-50% narrowing, rather than becoming no narrowing.
- Left/right locations and recorded velocity values are preserved
  in the inspected atoms.
- CTA remains recommended for further assessment,
  not described as completed.
- No follow-up date is invented.

### Issue Observed

Some supporting quotes omit context needed to interpret the atom
independently:
- The left common carotid atom's quote omits "On the left".
- One CTA recommendation quotes "This should be further
  assessed..." without the preceding finding.

The full report supports these relationships, but longer quotes
would make the evidence clearer.

### Follow-Up

Include the location or preceding finding when it is needed to
support an atom's meaning. The targeted checks did not identify
reversed laterality or a changed percentage qualifier.

## Report 4998: Allergy Evaluation

Trace: row4998-adk-gemini-3.8-flash-1750db84e3-attempt1.json

### Details Preserved

- Keflex is a suspected cause, not a confirmed cause.
- Allergy testing was performed, with results still pending.
- Avoidance advice remains conditional on test results.
- Recommendation to stop cephalosporin antibiotics.
- Heparin allergy and thrombocytopenia.
- Emergency-room instruction after EpiPen administration.

### Issues Observed

1. Missing medication-risk context:
   No atom explicitly states that atenolol makes acute anaphylaxis
   harder to treat while remaining medically necessary according
   to the source.

2. Missing post-treatment status:
   No atom explicitly preserves that no further problems were
   reported after discharge and treatment.

3. EpiPen conditions appear only in the quote:
   The atom text says only "EpiPen prescribed".
   Its quote includes acute angioedema, allergic reaction, or a
   sensation of an impending reaction. These conditions are
   available in the quote but not explicit in the atom text.

### Follow-Up

Preserve medication-risk explanations, post-treatment status,
and conditions attached to medication instructions explicitly.

## Findings Across Reports

The targeted inspection found examples of preserved medication
schedules, measurements, laterality, uncertainty, and follow-up
instructions.

Recurring improvement areas:
- Missing examination limitations and medication-risk context.
- Quotes too short to demonstrate negation, allergy status,
  location, or the relationship between statements.
- Ambiguous assertion conventions for negative descriptions.
- Source discrepancies preserved as separate facts without
  explicitly flagging their unresolved relationship.
- Medication conditions available only in quotes, not atom text.

These observations are not aggregate accuracy scores.

## Proposed Next Steps

1. Share these findings with the team.
2. Clarify assertion-label and source-discrepancy conventions
   before changing the shared output contract.
3. Make focused Extractor instruction changes for demonstrated
   omissions and insufficient quote context.
4. Add focused synthetic regression examples for the changes.
5. Save any new runs separately and compare them with these
   original traces.
6. Update the Extractor context document after implementation
   and testing.

## Second-Computer Setup

Not documented in this review.

Opening and inspecting saved traces does not establish that the
full local pipeline, shared vector index, or live generation
works on this computer.

## Limitations

- This is an LLM-assisted, targeted inspection of five hand-picked
  pilot reports, not independent clinical adjudication.
- No exhaustive fact inventory or aggregate accuracy was computed.
- Exact quote matching alone does not establish semantic support.
- Reported discrepancies require preservation and review,
  not an invented resolution.
- The traces describe saved November 8 behavior. They do not
  establish how later code changes perform.
- No Extractor fixes or regression tests were completed during
  this review.

## Follow-Up: Extractor-Only Rerun, November 18, 2026

Ran the updated Extractor once on each pilot's saved source report
using gemini-3.8-flash at temperature 0. Original traces were unchanged.
These were Extractor-only runs, not full-pipeline evaluations.

### Saved Results

All paths below are under data/extractor_reruns/:

- 3606: 20261118T233610799507Z/3606.json
- 4998: 20261118T233807172380Z/4998.json
- 3938: 20261118T234007484167Z/3938.json
- 3808: 20261118T234007484167Z/3808.json
- 2964: 20261118T234007484167Z/2964.json

### Validation Outcome

Four of five attempts passed schema and exact-quote validation.
Report 4998 failed because a generated quote changed source spacing.
This is a validation count, not a clinical accuracy score.

### Targeted Observations

- 3606: The previously omitted noncontrast examination limitation
  is now included. The adrenal statement identifies the impression,
  but the renal statement lacks section attribution and the
  discrepancy remains unflagged. The limitation is categorized
  as diagnosis, which needs review.

- 3808: Negation quotes now retain governing phrases such as
  "does not have". Bactrim retains 400/80 without an added unit
  or invented duration. Source discrepancies and assertion-label
  ambiguity remain. One atom incorrectly attributes the Endocrine
  statement to review of systems rather than physical examination.

- 3938: Allergy quotes now include the ALLERGIES heading.
  All five prednisone taper steps, antibiotic duration, follow-ups,
  and the abnormal cardiac finding remain preserved.
  Later taper-step quotes omit the medication name.
  Assertion and type-label concerns remain.

- 2964: At least 50% narrowing, laterality, and the recommended
  CTA remain preserved. The left common carotid quote now includes
  "On the left". Other quotes still omit needed location or
  antecedent context, including a CTA quote beginning with "This".

- 4998: The rejected output includes the previously missing
  atenolol risk, medical-necessity explanation, post-discharge
  status, and EpiPen conditions. It is not a validated result.
  The urticaria quote does not exactly match source spacing.
  Some other quotes still depend on surrounding context.

### Runner Behavior

The first batch stopped on report 4998's validation failure.
The failure and generated output were saved.
The runner was then updated to save ValueError failures and continue.
The three unattempted reports were run separately.
The failed allergy report was not retried or silently corrected.

### Interpretation and Remaining Work

The observations show partial improvement and unresolved problems.
One attempt per report cannot establish consistent behavior or
attribute every difference solely to the prompt change.

Keep exact-quote validation strict. Preserve failed attempts.
Prioritize quote fidelity, correct section attribution, source
discrepancies, and assertion/type conventions in further work.

No full-pipeline rerun or independent clinical adjudication was
completed. Second-computer vector-store integration remains unverified.