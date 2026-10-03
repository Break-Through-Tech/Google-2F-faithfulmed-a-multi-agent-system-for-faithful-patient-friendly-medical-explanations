# MTSamples: selected 50-report source evaluation subset

MTSamples is a collection of medical transcription sample reports. Each selected row's `transcription` is the source document for FaithfulMed's future simplification evaluation. This is a **selected evaluation subset**, not a cleaned replacement for the full dataset and not a claim of clinical correctness.

Status: **v1-proposed; selected, unannotated source reports awaiting team review and freeze**. These 50 reports are intended to become the team's shared/frozen baseline/evaluation set. No model outputs, clinical annotations, or gold simplified answers have been generated. Review and version this same set before reporting headline metrics. MedAESQA remains the separate Verifier calibration dataset.

## Source and sampling EDA

- Source file: `data/mtsamples.csv`; 4,999 rows and 6 columns.
- Columns: `Unnamed: 0`, `description`, `medical_specialty`, `sample_name`, `transcription`, `keywords`.
- SHA-256: `a92cb78569f460606661ee7da50c92305b60d0fac2be4b06c8d2de0f234612d4`.
- Source identifiers: `source_row_id` is the zero-based data-row position excluding the header. `source_dataset_id` preserves the CSV's `Unnamed: 0` identifier (or the source row position if absent).
- 40 original specialty labels; counts below include repeated reports under different labels.
- Exact duplicate full rows: 0; duplicate rows excluding the index: 0.
- Repeated nonempty transcription rows beyond the first: 2,609 exact; 2,611 after case/punctuation/whitespace normalization. Missing notes are excluded from duplicate counts.

| Column | missing_count | missing_percent |
| --- | --- | --- |
| Unnamed: 0 | 0 | 0.00% |
| description | 6 | 0.12% |
| medical_specialty | 0 | 0.00% |
| sample_name | 0 | 0.00% |
| transcription | 33 | 0.66% |
| keywords | 1149 | 22.98% |

Word counts use whitespace splitting. Statistics below exclude blank transcriptions; blank rows have zero words in the EDA.

| Statistic | Words |
| --- | --- |
| count | 4966.0 |
| mean | 465.45 |
| std | 316.39 |
| min | 1.0 |
| 25% | 241.0 |
| 50% | 398.0 |
| 75% | 615.0 |
| max | 3029.0 |

| Original specialty | Reports |
| --- | --- |
| Surgery | 1103 |
| Consult - History and Phy. | 516 |
| Cardiovascular / Pulmonary | 372 |
| Orthopedic | 355 |
| Radiology | 273 |
| General Medicine | 259 |
| Gastroenterology | 230 |
| Neurology | 223 |
| SOAP / Chart / Progress Notes | 166 |
| Obstetrics / Gynecology | 160 |
| Urology | 158 |
| Discharge Summary | 108 |
| ENT - Otolaryngology | 98 |
| Neurosurgery | 94 |
| Hematology - Oncology | 90 |
| Ophthalmology | 83 |
| Nephrology | 81 |
| Emergency Room Reports | 75 |
| Pediatrics - Neonatal | 70 |
| Pain Management | 62 |
| Psychiatry / Psychology | 53 |
| Office Notes | 51 |
| Podiatry | 47 |
| Dermatology | 29 |
| Dentistry | 27 |
| Cosmetic / Plastic Surgery | 27 |
| Letters | 23 |
| Physical Medicine - Rehab | 21 |
| Sleep Medicine | 20 |
| Endocrinology | 19 |
| Bariatrics | 18 |
| IME-QME-Work Comp etc. | 16 |
| Chiropractic | 14 |
| Rheumatology | 10 |
| Diets and Nutritions | 10 |
| Speech - Language | 9 |
| Lab Medicine - Pathology | 8 |
| Autopsy | 8 |
| Allergy / Immunology | 7 |
| Hospice - Palliative Care | 6 |

## Cleaning the candidate pool

The original file and original transcription strings were not modified. Filtering and normalization occur in memory only. Exclusions are sequential and mutually exclusive:

| Exclusion reason | Reports |
| --- | --- |
| normalized duplicate transcription | 2436 |
| ends with an empty heading/field (apparent truncation) | 134 |
| explicit template or standalone opening fragment | 96 |
| fewer than 40 whitespace words (too little text for this subset) | 76 |
| missing transcription | 33 |
| ends mid-phrase (apparent truncation) | 5 |
| near-duplicate transcription | 1 |

The 40-word minimum excludes heading-only stubs and very short fragments observed during inspection. It is a conservative suitability rule for this subset, not a judgment that all shorter reports lack clinical value. Additional checks require 15 distinct alphabetic tokens, at least 50% alphabetic non-whitespace characters, no replacement/control characters, and no trailing empty heading/field (a final colon, optionally followed by commas/semicolons/whitespace). Reports ending mid-phrase with `with/and/the/of/to/a/an/or/for/in/on/as/by/at` are excluded, as are titles explicitly containing `template` or ending in `opening`. These rules were informed by inspected truncated and template records; they are conservative text-quality heuristics, not exhaustive judgments of completeness. No missing metadata is invented; missing description or keywords alone does not exclude a meaningful note. Absence of a regex content cue does not exclude a report: some meaningful diagnostic findings use different vocabulary. Heading-only/metadata fragments observed in the shortest rows fail the minimum-text checks.

Duplicate normalization case-folds and extracts word tokens. For each normalized duplicate group, prefer a label among the 15 target specialties, then the least frequent specialty in the usable pre-deduplication pool, then the lowest source row ID. This preserves actual source labels and avoids letting multi-listed notes all inherit a broad specialty. Near duplicates use sets of consecutive five-word shingles: Jaccard overlap >= 0.85 with token-length ratio >= 0.8. Connected components are collapsed using the same representative rule; 1 qualifying pairs were found. This conservative screen may remove minor clinical variants and cannot detect every semantic duplicate.

Remaining candidate pool: **2,218 reports**. `candidate_audit.csv` records every source row's exclusion reason and final representative ID. An empty exclusion reason means retained in the candidate pool, not necessarily selected in the final 50. Representative IDs on quality-excluded rows are self-references only.

## Selection method

This is a purposive diversity set, not a prevalence-weighted population sample. Fifteen actual source specialty labels cover general care, organ systems, acute care, surgery, and different report formats. General Medicine, Cardiovascular / Pulmonary, Neurology, Emergency Room Reports, and Discharge Summary receive 4 reports each; the other 10 receive 3. Thus no specialty exceeds 8% of the subset. Source labels include both clinical disciplines and report types, so they are not a formal specialty ontology.

1. Compute length tertiles on the complete cleaned, deduplicated candidate pool: short <= **294** words; medium > **294** and <= **528**; long > **528**. Global quotas are 17 short, 17 medium, and 16 long.
2. Solve deterministic integer specialty/length quotas, requiring at least one of each available length group per specialty. Process specialties with fewer candidates first; choose the most even feasible allocation, with lexicographic tie-breaking.
3. Process specialty/length cells in ascending candidates-per-required-slot order, then specialty and length label. Greedily choose each report to increase diversity: score = 4/(1 + selected count in its complexity group) + 3/(1 + selected count of its structure) + sum of 1/(1 + selected count of each content cue). Break exact score ties using NumPy's seeded random ranks, assigned in ascending source-row order. **RANDOM_SEED = 42**.
4. Complexity is a textual proxy: average candidate-pool percentile ranks of distinct alphabetic words of at least 9 letters, numeric-token count, uppercase section-heading count, and number of distinct content cues. Split that score into candidate-pool tertiles (lower/middle/higher). It is not medical severity or a clinical diagnosis. Structure uses a documented ordered set of title/heading checks in the sampler. Content indicators are case-insensitive regex presence cues in transcription text; they can match negated statements and are not verified clinical facts or gold annotations.
5. Preserve original text and source IDs; sort output by specialty, word count, and source row ID. Short reasons describe sampling features only. Validate size, provenance, exact/near-duplicate absence, quotas, at least 10 reports in each complexity group, at least 6 structures, and at least 3 reports matching every content cue. All 1,225 selected pairs are independently checked against the shingle threshold without the length-ratio gate.

## Final subset

| Selected specialty | Reports |
| --- | --- |
| Allergy / Immunology | 3 |
| Cardiovascular / Pulmonary | 4 |
| Consult - History and Phy. | 3 |
| Discharge Summary | 4 |
| Emergency Room Reports | 4 |
| Endocrinology | 3 |
| Gastroenterology | 3 |
| General Medicine | 4 |
| Hematology - Oncology | 3 |
| Neurology | 4 |
| Orthopedic | 3 |
| Radiology | 3 |
| SOAP / Chart / Progress Notes | 3 |
| Surgery | 3 |
| Urology | 3 |

| Length group | Reports |
| --- | --- |
| short | 17 |
| medium | 17 |
| long | 16 |

- Selected: **50**; mean words: **543.68**; median: **422**.
- Shortest: **144** words (source row 4874); longest: **2460** words (source row 2796).

| Structure indicator | Reports |
| --- | --- |
| procedure/operative | 9 |
| consultation | 8 |
| other narrative/sectioned | 7 |
| SOAP-style | 6 |
| diagnostic report | 6 |
| follow-up/progress | 5 |
| history and physical | 5 |
| discharge summary | 4 |

| Text complexity | Reports |
| --- | --- |
| lower | 13 |
| middle | 17 |
| higher | 20 |

Content counts overlap because one note can match multiple cues:

| Content cue | Reports |
| --- | --- |
| allergies | 21 |
| assessment/plan | 27 |
| diagnoses | 49 |
| follow-up | 31 |
| imaging | 32 |
| laboratory values | 21 |
| medications | 36 |
| past history | 34 |
| procedures | 30 |
| surgery | 31 |
| symptoms | 40 |
| treatment plans | 41 |
| vital signs | 26 |

## Reproduce and review

From the repository root, with dependencies in `requirements.txt` installed:

```powershell
python EDAs/mtsamples_sampling.py --source data/mtsamples.csv
# Existing Windows virtual environment:
.\.venv\Scripts\python.exe EDAs/mtsamples_sampling.py --source data/mtsamples.csv
```

The sampler also accepts `.xlsx`/`.xlsm` input using pandas/openpyxl. It fails explicitly if another source cannot meet these quotas. For this version, verify the source hash above and use the library versions recorded in `selection_manifest.json`. Running the command overwrites generated subset artifacts; archive a reviewed/frozen version before deliberately changing source data or selection rules. CSV content, selected IDs, and metadata are deterministic; Excel archive timestamps may differ between runs.

Open `EDAs/mtsamples_eda.ipynb` and run all cells for the sampling EDA, plots, in-memory selection, and checks. The notebook does not overwrite exports. The reusable cleaning/selection implementation is `EDAs/mtsamples_sampling.py`. Its SHA-256 and selected row IDs are in the manifest.

Files: `mtsamples_curated_50.xlsx` (formatted sheet; expand row height/formula bar to read long notes), matching `mtsamples_curated_50.csv`, this README, `candidate_audit.csv`, and `selection_manifest.json`. The script verifies full CSV and Excel round-trips, including every transcription. Current repository rules ignore `data/curated_baseline/`; these local artifacts are not automatically tracked or published by Git.

Limitations: quota balancing intentionally changes specialty frequencies; only 15 of the 40 source labels are represented. Regex cues and text complexity are approximate sampling aids. This automated, reproducible selection is a proposal for team curation, not completed human annotation or clinical validation. Before freezing, the team should review whole reports for source suitability, structural classifications, residual duplicates, and intended coverage. No model generation or annotation is part of this task.
