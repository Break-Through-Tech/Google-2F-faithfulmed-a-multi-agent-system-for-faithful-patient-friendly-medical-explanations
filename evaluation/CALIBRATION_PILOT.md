# First MedAESQA development pilot — October 27, 2026

Six fixed development cases were sent to `gemini-3.8-flash` after authorization. All six returned valid predictions, with no API failures. The prompt, reference labels, and selected cases were not changed after seeing the results.

| Measure | Result |
| --- | --- |
| Development cases scored | 6 of 40 |
| Reference labels | 3 supporting, 3 neutral/non-supporting |
| Predictions | All 6 not supported |
| Matching reference labels | 3 of 6 |
| Agreement | **50%** |
| Cohen's kappa | **0.00** |
| Agreement Wilson 95% interval | Approximately 18.8%–81.2% |
| False negatives / false positives | 3 / 0 |
| Remaining development cases | 34 |
| Held-out cases scored | **0 of 40** |

The ≥80% agreement and kappa ≥0.6 targets were not met in this pilot. A constant “not supported” prediction matches half of this balanced sample, explaining the zero kappa. This is a small evidence-pair pilot, not a measurement of accuracy on the 50 clinical reports or the entire ADK workflow.

## Case results

| Position | Question ID | Reference relation | Predicted support | Match |
| --- | --- | --- | --- | --- |
| 1 | 144 | supporting | False | No |
| 2 | 128 | neutral | False | Yes |
| 3 | 139 | supporting | False | No |
| 4 | 126 | neutral | False | Yes |
| 5 | 142 | supporting | False | No |
| 6 | 146 | neutral | False | Yes |

Full case IDs, source sentences/excerpts, model reasons, prompt hash, and attempt records are saved locally in `data/calibration_results/medaesqa_support_v1.json` and `data/calibration_results/development_v1.json`. The selected IDs are also recorded in [the selection manifest](calibration_selection_manifest.json).

## What the disagreements show

- **Question 144:** the answer lists specific lifestyle measures. The excerpt discusses treatment of reversible factors and blood pressure more broadly. The judge rejected support for the specific list.
- **Question 139:** the answer lists particular pregnancy complications. The excerpt describes high-risk pregnancies and the study's purpose, without those specific findings. The judge regarded this as insufficient.
- **Question 142:** the answer describes medicines causing hypertension or interfering with treatment. The excerpt says an NSAID has an effect on systolic blood pressure but does not state the direction of that effect. The judge rejected the stronger conclusion.

These are disagreements with existing reference labels; they do not establish that either the judge or the references are necessarily correct in every case. They suggest a possible mismatch between strict excerpt-only support and the scope of the dataset's citation assessments, as well as sensitivity to partial support in multi-part sentences. Six cases cannot distinguish these explanations reliably.

## Next development step

Check the annotation definition and available evidence context for these cases before changing the prompt or spending calls on the remaining cases. Keep neutral evidence distinct from broad topical overlap. Do not change reference labels, discard cases because the judge disagrees, or allow external knowledge merely to raise the score.

Any revised prompt needs a new recorded version and prediction output path. Use development cases for that work, then hold the chosen settings fixed for held-out evaluation. The four advisor-example checks already passed, but this pilot shows that passing those examples does not establish MedAESQA agreement.

## Follow-up investigation

The [evidence-scope investigation](CALIBRATION_INVESTIGATION.md) is now completed. The original prompt and labels were retained while the same six pairs received full cited titles/abstracts. Agreement became **66.7% (4/6), kappa 0.33**. Reference inconsistencies remain, and no cases were dropped. The original results above are preserved; the diagnostic is not a held-out result.
