# Why the 26-case run reached only 50% agreement

## Main finding

The latest rule mixed citation attribution with question relevance and strength of
clinical evidence. It therefore rejected some statements that it had itself marked
supported. At the same time, it still accepted partial support in five cases whose
references are neutral. Making the rule uniformly stricter or looser is not a sufficient
fix. These findings do not establish that all 13 reference labels are right or wrong.

The current result remains **13/26 agreement, kappa 0.00**, with no failed outputs.
No labels, predictions, prompts, or live Verifier behavior were changed during this
investigation. No Gemini calls were made. Held-out cases were not inspected.

## What the dataset actually asks

The dataset separates sentence relevance from citation support. Its support definition
requires an agreeing source sentence and no contradictory source sentence. Neutral
means topical relevance without evidence validating or invalidating the assertion.
Experts supplied excerpts explaining their judgments; the evaluated documents were
PubMed titles and abstracts, not excerpts alone. The published description does not
fully resolve how to aggregate every compound assertion. The original collection used
a historical PubMed snapshot; our cached abstracts have not been verified against that
exact snapshot. [Original dataset methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12179289/)

The dataset card also defines `evidence_relation` at the assertion/document level and
`evidence_support` as the supporting snippet for that relation.
[Dataset card](https://huggingface.co/datasets/deepak8452/MedAESQA/blob/main/README.md)

**Correction to the earlier suggestion:** full abstracts are an appropriate evidence
scope. Reverting to excerpts alone would not reproduce the documented document-level
task. Likewise, excluding definitions merely because they are background introduces an
extra criterion. Support and usefulness to the question must be reported separately.

## Checks performed

- Recomputed the 13 disagreements from all 26 saved outputs.
- Matched every original citation record by question, model, sentence ID, citation
  index, PMID, and normalized assertion; confirmed all original relation labels.
- Read the reference excerpts, cached abstracts, selected evidence, and judge reasons.
- Preserved original neighboring sentences in the local evidence packet where needed
  for interpretation. These were not added to any model input during this investigation.
- Compared v3 and v5 on the same 24 cases with successful outputs in both runs.
  V3 agreed on 15/24; v5 on 12/24. One disagreement was corrected, while four previously
  agreeing decisions became disagreements. This is an observational comparison across
  different prompts/output formats, not proof that a single wording change caused it.

## The 13 disagreements, side by side

The categories below are investigative explanations, not new reference labels. Several
cases involve more than one issue. All evidence descriptions are from the local records.

| Question / PMID | Reference / judge | Assertion and actual evidence | Finding |
|---|---|---|---|
| 126 / 33484483 | Neutral / supported | The answer defines nondisjunction and its chromosome-count consequence. The original excerpt already links nondisjunction to an aneuploid egg. The judge accepts that consequence but not the full definition. | Partial-support and terminology boundary. The disagreement is not explained simply by added abstract context. The supplied independent review also accepted support, but does not override the dataset label. |
| 146 / 34132818 | Neutral / supported | The sentence joins adolescent psychotherapy benefit with limited self-management efficacy. The excerpt describes background treatment evidence; the full abstract adds improvement in a small adolescent PTSD/BPD study without a control group. Nothing establishes the self-management clause. | Compound-claim scope plus evidence-strength uncertainty. Extra context helps one clause but not the other; neither a blanket yes nor a claim that the reference is wrong is established. |
| 140 / 29869038 | Neutral / supported | The answer lists four osteoporosis factors. Both the original excerpt and abstract identify vitamin D deficiency among secondary etiologies for bone loss. The other three factors are absent. | The judge applies the one-list-item rule. The neutral label demonstrates that rule does not reliably reproduce this reference. There is no missing-context explanation for the supported item. |
| 146 / 34191936 | Supporting / not supported | The answer says cognitive therapy is particularly beneficial after ICU admission and also discusses exposure therapy. The paper describes first-line CT-PTSD and its application after ICU, but does not establish comparative benefit or the exposure-therapy clause. | A defensible qualification concern remains. The reference accepts narrower treatment evidence; the judge insists on the stronger qualification. Do not simply remove the qualification to gain agreement. |
| 148 / 18481559 | Neutral / supported | The answer lists bleeding disorders, connective-tissue disorders, and acquired causes of bruising. The excerpt discusses detecting von Willebrand disease; the abstract describes a bruising/bleeding diagnostic work-up. | Indirect causal inference and partial list coverage. The judge infers a cause from diagnostic context. That may be reasonable background knowledge but is not explicit support for the entire assertion. |
| 137 / 32641437 | Supporting / not supported | The answer attributes glucose, weight, and medication improvements to ketogenic diet. The paper is one case using diet plus intermittent fasting; BMI changed minimally and medication was restarted later. | Real scope and intervention-attribution concerns. A stricter evidence judgment is defensible, although it disagrees with the citation label. This should not be resolved by pretending the study proves all three effects. |
| 129 / 15660353 | Supporting / not supported | The answer says withdrawal can cause variant angina, heart failure, and bradycardia. The excerpt reports variant angina after beta-blocker withdrawal in one patient. | Likely over-strict evidence threshold: a case can provide evidence for a qualified possibility without establishing incidence or general effectiveness. V5 rejects the case categorically. The other listed effects remain unsupported by this document. The preceding answer sentence identifies what 'It' refers to; the judge already inferred withdrawal correctly. |
| 137 / 33163300 | Supporting / not supported | The answer combines HbA1c improvement with specific comparators and durations. The excerpt and abstract support HbA1c benefit versus controls but do not specify all comparators or times. | Coverage/attribution conflation: the judge lets missing qualifications erase a documented effect. Report unsupported timing separately; the exact binary treatment of the compound sentence still needs a fixed interpretation. |
| 128 / 32374168 | Supporting / not supported | The sentence connects CBD, liver function, NF-kB, and NLRP3. The paper supports CBD effects on NLRP3 in human monocytes, without establishing the liver or NF-kB connection. | Mechanism-to-organ extrapolation concern. The judge's objection is defensible under the supplied evidence. The reference appears to accept narrower mechanism evidence; that does not validate the liver claim. |
| 150 / 20397860 | Supporting / not supported | The sentence says physical therapy interventions can reduce pain and disability. The paper reports improvement in one patient using extension exercises followed by added traction. It does not test education or manual therapy. | Likely over-strict treatment of 'can' and case evidence. The case supports a limited possibility; it does not isolate effects or establish general effectiveness. A categorical dismissal loses that distinction. |
| 138 / 15236629 | Neutral / supported | The sentence identifies ingredients and routes for Sudafed and Afrin. The original snippets explicitly identify oral pseudoephedrine as Sudafed and report congestion effects, but say nothing about Afrin. | Partial-support/reference-scope ambiguity. The evidence is explicit for one clause even in the original snippets, so additional context is not the whole explanation. |
| 127 / 16782218 | Supporting / not supported | The paper explicitly describes gene therapy's therapeutic strategies. The judge marks the therapeutic-purpose proposition supported, then rejects citation support because it calls that fact background and cannot establish future standard practice. | Clear task-rule defect: supported background was excluded by an added relevance criterion. Whether the future-practice clause is supported remains a separate question. |
| 126 / 18558649 | Supporting / not supported | The source explicitly defines aneuploidy; this definition is also the original supporting excerpt. The judge marks it supported but rejects the citation because the paper does not explain nondisjunction or establish all downstream causal claims. | Same task-rule defect: dismissing a supported definition because it is not the preferred central answer. The causal claims still need separate coverage checks. |

## Why a simple binary change will not rescue this run

Recomputing diagnostic aggregates from the existing proposition judgments, without
calling Gemini or replacing the official predictions:

| Diagnostic rule | Agreement with the 26 references |
|---|---:|
| Saved v5 citation decision | 13/26 |
| Any proposition marked supported | 15/26 |
| Every proposition marked supported | 13/26 |

These are post-hoc diagnostics, not candidate validation scores. They show that merely
changing the aggregation threshold would still miss the project target. The model's
proposition choices and reasoning matter too. None of the 26 outputs marked a
proposition contradicted; this set therefore does not validate contradiction handling.

The broad pattern is five partial-support/inference disagreements, two clear added
relevance-rule problems, three probable over-strict evidence/coverage problems, and
three unresolved qualification or extrapolation cases. This grouping is an analysis
aid, not an independently adjudicated set of 13 error labels.

## Recommended next experiment

1. Implement a separate, direct sentence-to-document citation classifier following
   the published categories: supporting, contradicting, neutral, not relevant.
   Map supporting to true only after classification. Keep the current runs intact.
2. Remove the added rule that background or definitions cannot qualify. Keep relevance,
   whole-sentence coverage, and evidence-strength limitations in separate fields.
   Explicitly check contradictory passages; a supported fragment must not conceal a
   contradiction elsewhere in the document.
3. Use existing question context only to resolve meaning. If adding preceding answer
   text for pronouns, version that input change and never treat neighboring model claims
   as independent source evidence. Do not silently replace the judged sentence.
4. Test the logic locally on simple supported-definition, irrelevant-definition,
   contradiction, qualified-possibility, and unsupported-generalization fixtures before
   another live run. These would test implementation behavior, not supply clinical gold.
5. Run one predeclared development comparison on the same 26, with unchanged references
   and no correctness-based exclusions. Report all errors and abstentions. If it still
   falls short, compare an independent judging approach under the same fixed task rather
   than continue changing the meaning of support to fit these cases.

The published task gives us a basis to correct concrete mistakes without contacting
the advisor. It does not guarantee 80% agreement or kappa 0.6, or settle every partial
support ambiguity. Freeze the task and settings before using held-out cases.

## Reproducible local evidence packet

Run `python -m evaluation.investigate_support_v5` to reproduce
`data/calibration_results/document_support_v5_investigation.json`. It includes the 13
full assertions, cached abstracts, original citation excerpts and locations, saved
judge outputs, input file hashes, and matched-run counts. The script makes no API calls
and refuses to overwrite a different existing investigation. It does not change any
reference label. The JSON is a local data artifact, not a new benchmark or gold review.
