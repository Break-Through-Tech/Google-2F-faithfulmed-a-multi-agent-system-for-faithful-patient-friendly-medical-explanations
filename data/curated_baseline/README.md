# MTSamples: active 50-report medium-focused subset

Status: **v3-medium-with-allergy-exceptions-proposed; awaiting team review and freeze**. This is the single active curated set, following Samaneh's recommendation to use medium-length reports for the first baseline. It replaces the mixed-length CSV and Excel at the same paths. The earlier analysis and selected IDs remain reproducible in `EDAs/mtsamples_eda.ipynb`; the original exports remain in Git history (commit `5d415c7`). No generated explanations or gold annotations are included.

## Source and cleaning

Source: `data/mtsamples.csv`; **4,999 rows**; SHA-256 `a92cb78569f460606661ee7da50c92305b60d0fac2be4b06c8d2de0f234612d4`.
The unchanged cleaning rules remove empty/very short text, obvious truncation and template fragments, normalized duplicates, and near-duplicates. Near-duplicate detection uses five-word shingle Jaccard >= 0.85 with length ratio >= 0.8. The original transcription text is preserved exactly.

| Cleaning exclusion | Reports |
| --- | --- |
| normalized duplicate transcription | 2436 |
| ends with an empty heading/field (apparent truncation) | 134 |
| explicit template or standalone opening fragment | 96 |
| fewer than 40 whitespace words (too little text for this subset) | 76 |
| missing transcription | 33 |
| ends mid-phrase (apparent truncation) | 5 |
| near-duplicate transcription | 1 |

**2,218 cleaned reports remain; 740 are medium-length.** Medium means more than **294** and at most **528 whitespace words**, using the middle third of the complete cleaned pool. These cutoffs are not recomputed within specialties or within the final 50. The active set has 48 medium reports and two documented Allergy/Immunology length exceptions.

## How these 50 were chosen

1. Start with the same quality-screened, deduplicated pool used for the original EDA, and keep medium reports. Exclude explicit transcription gaps (two or more underscores, or bracketed inaudible/unintelligible markers): 61 medium reports are excluded and 679 remain. This conservative extra screen avoids incomplete passages without filling in missing text; it can also exclude harmless redactions. The original mixed-length cleaning and analysis are unchanged.
2. Restore the original three-report Allergy/Immunology quota with two fixed, complete, gap-free source reports outside the medium range: **source row 0, Allergic Rhinitis (204 words, short)**, and **source row 4998, Allergy Evaluation Consult (638 words, long)**. They are direct allergy cases and add one shorter and one longer format to the 390-word medium asthma report. The other specialty quotas return to the original targets, including three each for Orthopedic and Surgery. All other 48 selected reports must be medium-length. This deliberate exception means the set is medium-focused, not strictly medium-only.
3. Process scarce specialties first (available reports divided by quota). Choose reports greedily to add less-represented content cues, report structures, and text-complexity groups. The diversity score is `4/(1+complexity_count) + 3/(1+structure_count) + sum(1/(1+content_cue_count))`. Seed 42 breaks ties with ranks assigned in source-row order.
4. Keep the original cleaned-pool complexity cutoffs so comparisons with the earlier sample are consistent. Text complexity and regex cues are sampling aids; they are not clinical labels and can match negated statements.
5. Validate 50 unique IDs, exact source-text preservation, the 48/1/1 length split and specialty quotas, at least 10 reports per complexity group, at least six structures, and at least three matches for every content cue. Check all 1,225 selected pairs for near-duplicates, without the length-ratio gate.

This is a reproducible diversity selection, not a claim of the clinically "best" 50. The quality filters cannot catch every incomplete or inaccurate source report; team review is still required. Selection does not use any generated output or evaluation score.

| specialty | previous_target | medium_available_after_gap_screen | documented_length_exceptions | selected_target |
| --- | --- | --- | --- | --- |
| General Medicine | 4 | 37 | 0 | 4 |
| Cardiovascular / Pulmonary | 4 | 67 | 0 | 4 |
| Neurology | 4 | 75 | 0 | 4 |
| Gastroenterology | 3 | 53 | 0 | 3 |
| Orthopedic | 3 | 70 | 0 | 3 |
| Urology | 3 | 39 | 0 | 3 |
| Allergy / Immunology | 3 | 1 | 2 | 3 |
| Endocrinology | 3 | 5 | 0 | 3 |
| Hematology - Oncology | 3 | 22 | 0 | 3 |
| Emergency Room Reports | 4 | 31 | 0 | 4 |
| Discharge Summary | 4 | 36 | 0 | 4 |
| Surgery | 3 | 109 | 0 | 3 |
| Consult - History and Phy. | 3 | 42 | 0 | 3 |
| Radiology | 3 | 27 | 0 | 3 |
| SOAP / Chart / Progress Notes | 3 | 39 | 0 | 3 |

## Selected-set coverage

- **48 medium-length reports, one short Allergy exception, and one long Allergy exception**, spanning 15 source labels (specialties and report formats).
- Word counts: minimum **204**, median **408.5**, mean **410.24**, maximum **638**.

| Structure | Reports |
| --- | --- |
| other narrative/sectioned | 8 |
| consultation | 8 |
| procedure/operative | 8 |
| history and physical | 7 |
| SOAP-style | 5 |
| discharge summary | 5 |
| diagnostic report | 5 |
| follow-up/progress | 4 |

| Text complexity | Reports |
| --- | --- |
| lower | 13 |
| middle | 16 |
| higher | 21 |

Content cue counts overlap:

| Content cue | Reports |
| --- | --- |
| allergies | 24 |
| assessment/plan | 25 |
| diagnoses | 47 |
| follow-up | 23 |
| imaging | 30 |
| laboratory values | 18 |
| medications | 33 |
| past history | 33 |
| procedures | 23 |
| surgery | 28 |
| symptoms | 37 |
| treatment plans | 39 |
| vital signs | 28 |

## Files and reproduction

- `mtsamples_curated_50.csv` and `.xlsx`: the same active medium-focused set, in two convenient formats.
- `candidate_audit.csv`: each original row's cleaning decision and selection status. Eligible but unselected reports are distinguished from quality exclusions and out-of-range reports.
- `selection_manifest.json`: source and output hashes, selected IDs, cutoffs, quotas, code hashes, and library versions.

Run from the repository root:

```text
python EDAs/mtsamples_sampling.py --profile medium --source data/mtsamples.csv
```

The default profile is now `medium` (48 medium reports plus two documented length exceptions). The original mixed-length functions remain unchanged; to reproduce their exports separately use `--profile mixed --output <another-directory>`. The notebook displays both analyses but compares the active exports only with the new medium-focused set. CSV/Excel full-text round trips are checked. These existing output files are already tracked by Git; ignoring `data/` does not hide changes to them. Only one active export set is kept here.

Review complete reports before freezing this version. Results on this set mainly describe medium-length notes from these source categories, with two explicit Allergy exceptions; they do not establish general performance on short/long reports or clinical reliability.
