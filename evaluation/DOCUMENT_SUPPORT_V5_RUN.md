# Revised substantive-assertion support: development results

Follow-up: [offline investigation of all 13 disagreements](DOCUMENT_SUPPORT_V5_INVESTIGATION.md).

## Rule tested

`evaluation/calibrate_support_v5.py` defines support as evidence establishing a
substantive clinical assertion at its stated scope, rather than any related fragment.
Important qualifications stay attached. Ordinary paraphrases remain allowed, and one
complete independent claim in a list can qualify without establishing the whole list.
Incidental background alone is insufficient. This is a development hypothesis, not a
confirmed interpretation of the MedAESQA annotation instructions.

The v4 lossless source-span suite and validation are reused unchanged. The full new
prompt is included in the run fingerprint; the suite version remains v4 because the
cases and evidence did not change. Historical runs and reference labels are preserved.

## Result

Six calls using `gemini-3.8-flash`, temperature 0, on the same first six eligible
development cases as v4. All six returned valid decisions, and every selected evidence
span was checked against its original source offsets. Local validation tests: 29 passed.

- Agreement: **4/6 (66.7%)**; Cohen's kappa: **0.33**.
- Three supporting and three non-supporting references; three true positives, one
  true negative, two false positives against those references.
- No service failures or abstentions. Two sentences were judged completely supported;
  whole-sentence coverage is a separate diagnostic without proposition-level gold labels.
- The same disagreements remain: question 126 / PMID 33484483 and question 146 /
  PMID 34132818. The judge sees support for the chromosome-count consequence and for
  adolescent psychotherapy respectively, while the selected references are neutral.

Saved results: `data/calibration_results/document_support_v5_development.json`.

## Initial stopping decision

The user required **6/6 agreement before continuing**. That gate failed, so the remaining
20 eligible cases were not run. No extra retries or alternate rule searches were made.
Held-out cases remain untouched. The revised rule did not improve binary agreement on
these six cases. This repeatedly inspected development set cannot establish independent
calibration performance, even if a future revision reaches perfect agreement.


## Completed 26-case run

The user subsequently authorized completing all 26 eligible cases regardless of the six-case gate. The saved run was resumed for the remaining 20 with the identical prompt fingerprint, model, temperature, evidence, case order and reference labels. No retries, exclusions based on correctness, or further prompt changes were made.

- Agreement: **13/26 (50.0%)**; Cohen's kappa: **0.00**.
- 95% Wilson interval for agreement: 32.1% to 67.9%.
- All 26 outputs valid; zero failures and zero abstentions. Source offsets and exact evidence text verified for every selected span.
- References: 16 supporting, 10 non-supporting. True positives: 8; true negatives: 5; false positives: 5; false negatives: 8.
- The original six contributed 4 correct; the remaining 20 contributed 9 correct.
- All 14 previously ambiguous cases remain outside this eligible benchmark. Held-out cases remain untouched.

The project goals (at least 80% agreement and kappa 0.6) remain unmet. This rule should not be promoted as a calibrated judge. Kappa zero means no agreement beyond that expected from these marginal label frequencies; it does not mean zero answers were correct. These are development results after repeated tuning, not an independent validation.

### Case results

| Question | PMID | Reference support | Judge support | Agreed |
|---|---|---|---|---|
| 126 | 33484483 | False | True | False |
| 142 | 24042856 | True | True | True |
| 150 | 24336970 | True | True | True |
| 146 | 34132818 | False | True | False |
| 152 | 15183079 | True | True | True |
| 137 | 22673594 | False | False | True |
| 140 | 29869038 | False | True | False |
| 126 | 17911163 | True | True | True |
| 139 | 23329707 | True | True | True |
| 146 | 34191936 | True | False | False |
| 144 | 20148501 | False | False | True |
| 125 | 16986050 | True | True | True |
| 127 | 15553101 | True | True | True |
| 148 | 18481559 | False | True | False |
| 137 | 32641437 | True | False | False |
| 126 | 17314397 | False | False | True |
| 129 | 15660353 | True | False | False |
| 126 | 15329821 | True | True | True |
| 125 | 17609936 | False | False | True |
| 137 | 33163300 | True | False | False |
| 150 | 27429818 | False | False | True |
| 128 | 32374168 | True | False | False |
| 150 | 20397860 | True | False | False |
| 138 | 15236629 | False | True | False |
| 127 | 16782218 | True | False | False |
| 126 | 18558649 | True | False | False |
