# Review of the 14 conflicting development cases

Reviewed November 7, 2026. These are **provisional development decisions**, not corrected MedAESQA gold labels, clinical validation, or held-out results. No Gemini calls or saved model predictions were used during this review; four cases had been discussed in the previous diagnostic, so the review is not historically blind to all past results.

The same sentence and PMID can have several reference records. In many groups, the records assess different snippets from the same abstract: one snippet contains a result while another contains background. Their labels may therefore differ without proving that either snippet label is wrong. Some groups also contain blank-snippet `not relevant` records, whose cause cannot be inferred from the available data.

Under the v2 development question?does this document substantively support at least one cited assertion??the review proposes **13 candidate yes decisions and 1 unresolved decision**. These proposals do not automatically replace the original labels or enter agreement/kappa. A yes on partial support does not mean the whole sentence is supported. The candidate labels are not independent human adjudications; four cases were previously seen, and current PubMed abstracts may differ from the original dataset snapshot.

The standalone sentence for question 139 / PMID 34121088 begins with ?This.? Its prior sentence changes what the phrase might mean; the current judge sees the question, standalone sentence, and abstract, but not the preceding answer. Keep that case unresolved until an explicitly versioned task decides how to include and assess surrounding context.

## Case-by-case decisions

| Question / PMID | Original references | Candidate citation support | Coverage | What the abstract establishes and what remains uncertain |
| --- | --- | --- | --- | --- |
| 144 / 16810473 | not relevant: 2, supporting: 2 | yes, provisional | partial | The abstract recommends lifestyle measures for hypertension, but does not enumerate the sentence's individual examples. |
| 128 / 36968131 | not relevant: 1, supporting: 4, neutral: 2 | yes, provisional | partial | The study directly compares ALT and AST; the sentence's broad phrase liver enzymes could include other measures and populations. |
| 139 / 35172902 | supporting: 8, neutral: 1, not relevant: 1 | yes, provisional | partial | The abstract describes anemia and obstetric complications in active anorexia; hyperemesis is not mentioned. |
| 146 / 24422773 | supporting: 1, neutral: 1 | yes, provisional | partial | SSRIs and residual symptoms after nondrug care are discussed; SNRIs and inability to access psychotherapy are not explicitly established. |
| 146 / 36920821 | neutral: 1, supporting: 1 | yes, provisional | substantially supported | The abstract supports prazosin for PTSD-related sleep disturbance and separately names paroxetine as an effective SSRI for primary symptoms. |
| 142 / 34414219 | neutral: 1, supporting: 2 | yes, provisional | partial | The review covers some antidepressants and hypertension risk, not the full list of other drug classes, avoidance, or frequency in the answer. |
| 140 / 21409500 | supporting: 1, neutral: 1 | yes, provisional | partial | The abstract associates the scaphoid condition with systemic disease and steroid exposure, but also describes fractures as preceding the condition and a form without fracture. |
| 139 / 15478133 | supporting: 6, neutral: 2 | yes, provisional | partial | The abstract states an association with mortality but does not compare untreated versus treated anorexia. |
| 139 / 34121088 | supporting: 2, neutral: 1 | unresolved | unclear | The sentence starts with 'This'; the prior sentence concerns persistent lipedema-related tissue, while the abstract attributes reduced body-image acceptance to poor awareness and confusion with obesity. |
| 141 / 32965473 | supporting: 1, neutral: 1 | yes, provisional | substantially supported | The abstract reports a 20-50% case-fatality range, though 'in some cases' does not specify the study population. |
| 120 / 31723507 | neutral: 1, supporting: 1 | yes, provisional | partial | The case report links metastatic adenocarcinoma to facial numbness; it does not establish the meningioma example, and its abstract does not explicitly state nerve compression. |
| 126 / 16192699 | supporting: 4, neutral: 1 | yes, provisional | partial | The abstract discusses meiotic and mitotic nondisjunction in oocytes and embryos, but does not fully define meiosis and mitosis as phrased. |
| 146 / 27716776 | neutral: 1, supporting: 1 | yes, provisional | substantially supported | The modeling paper describes limited simulated effects of current screening and treatment policies and argues for change. |
| 134 / 16368443 | neutral: 1, supporting: 1 | yes, provisional | partial | The review discusses serotonergic treatments and antidiarrheals, but does not explicitly identify laxatives; it also notes limited trial efficacy for traditional therapies. |

## How to use this review

- The [machine-readable review decisions](development_conflict_review_v1.json) include an evidence anchor and rationale for each case. A richer local record, with case IDs and every original reference record, is at `data/calibration_results/development_conflict_review_v1.json`.
- These are proposed document-level judgments for development experiments only. They do not silently replace the dataset labels. The existing v2 suite continues to quarantine all 14.
- If the team chooses to use these proposed labels in an experiment, create a new versioned cohort containing the review provenance, evidence hashes, original labels, candidate labels, and an explicit scope. Keep results reported separately from the 26 original structurally eligible cases. Do not claim the new labels are independent or use them as held-out truth.
- A label based on a partially supported claim concerns citation/assertion support only; full-sentence coverage must be assessed separately.
- The earlier results and the 40 held-out cases remain untouched. No new calibration calls were made.

Source suite digest: `5c4160ed0b91daff5d72bf84a5e0cc7eb0c6dffc91d778baffae42609273d33d`. Review definitions SHA-256: `45b19bdb7073f68a9e6949f70cb56039941b4122ddd2d6e717ca0991654a5e65`.
