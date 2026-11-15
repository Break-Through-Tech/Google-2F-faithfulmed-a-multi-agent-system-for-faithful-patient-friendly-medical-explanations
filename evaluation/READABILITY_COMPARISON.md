# Five-report readability comparison

This is the readability-only comparison for the five-report pilot. It uses the
saved, matched-context run `five_report_readability_2026-11-08_v2` and the shared
`evaluation.readability.evaluate_readability` scorer with `max_grade=8` and no
word-count limit. Baseline answers and ADK retained text were scored as saved;
the ADK 3606 text is a held-for-review draft, not a released answer.

The supplied run artifacts are local under
`data/comparison_results/five_report_readability_2026-11-08_v2/` and are
gitignored. No raw run artifacts are included in this report.

## Summary

| System / denominator | Scored | Readability passes | Pass rate | Mean FK grade | Mean SMOG grade | Mean words | Mean jargon density | Refusals | Failed / held for review |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Baseline: all attempted reports | 4/5 | 3 | 75% (3/4 scored) | 7.56 | 10.55 | 460.25 | 0.0179 | 0/4 | Report 3606 failed generation; not scored |
| ADK: all attempted reports | 5/5 | 4 | 80% (4/5 scored) | 7.02 | 10.28 | 434.40 | 0.0183 | 0/5 | Report 3606 is `needs_review`; its draft was scored but not released |

The directly comparable pairs are reports 4998, 3938, 3808, and 2964. On that
same four-report subset, the baseline passed 3/4 (75%) and ADK passed 4/4
(100%). Mean baseline metrics were FK 7.56, SMOG 10.55, 460.25 words, and
0.0179 jargon density; mean ADK metrics were FK 6.54, SMOG 9.92, 415 words,
and 0.0219 jargon density. Both systems had 0 detected refusals in these four
pairs.

The denominator is the number of successfully generated, non-empty texts
scored. A failed generation is not scored as a readability failure. The
separate five-attempt figures keep that failure visible. The ADK 3606 draft
has a readability score, but is not a released explanation; therefore, the
four released ADK answers are 4/4 readability passes, while one additional
attempt remains held for review.

## Per-report metrics

Jargon density is the shared scorer's count of recognized medical terms divided
by word count. SMOG is unavailable for texts with fewer than three sentences;
all texts here had a value.

| Report | System | Output status | FK grade | SMOG grade | Words | Jargon density | Refusal | Passes grade-8 target |
|---|---|---|---:|---:|---:|---:|---|---|
| 4998 | Baseline | Answer | 8.14 | 10.88 | 595 | 0.0151 | No | No |
| 4998 | ADK | Complete | 7.84 | 10.93 | 444 | 0.0113 | No | Yes |
| 3938 | Baseline | Answer | 7.86 | 10.63 | 463 | 0.0302 | No | Yes |
| 3938 | ADK | Complete | 5.26 | 8.96 | 476 | 0.0231 | No | Yes |
| 3808 | Baseline | Answer | 7.01 | 9.96 | 379 | 0.0264 | No | Yes |
| 3808 | ADK | Complete | 6.61 | 9.43 | 409 | 0.0440 | No | Yes |
| 3606 | Baseline | Generation failed | — | — | — | — | — | Not scored |
| 3606 | ADK | Needs review; draft not released | 8.92 | 11.72 | 512 | 0.0039 | No | No |
| 2964 | Baseline | Answer | 7.23 | 10.73 | 404 | 0.0000 | No | Yes |
| 2964 | ADK | Complete | 6.46 | 10.36 | 331 | 0.0091 | No | Yes |

## Examples and interpretation

- **Shorter follow-up wording (3938):** the baseline says, “Follow up at your
  primary care doctor's office”; ADK says, “See your primary care doctor.”
  Both preserve the next-day timing in the surrounding instruction.
- **Plain-language definition (2964):** the baseline says carotid arteries
  “supply your brain and head with blood”; ADK says they “send blood to your
  head and brain.” ADK's version scored lower for FK grade in this report.
- **Readability does not measure completeness (4998):** the baseline explains
  that continuing atenolol was medically necessary despite complicating
  treatment of a severe allergic reaction. The ADK text lists atenolol for
  blood pressure but omits that rationale. A lower reading grade cannot detect
  or correct that omission.

In this small pilot, ADK had a lower mean FK grade on the four comparable
reports and all four met the grade-8 target, compared with three of four
baseline answers. Jargon density was not consistently lower. These are
descriptive results from four matched examples, not evidence that ADK is
generally more readable or clinically more accurate. In particular, the
baseline failed to generate report 3606, and the ADK result for that report
remained held for review. The live Verifier's clinical accuracy was not
validated by these readability scores.
