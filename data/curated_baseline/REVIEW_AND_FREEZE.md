# Review and freeze of the 50 MTSamples source reports

**Frozen on October 26, 2026.** Version: `v3-medium-with-allergy-exceptions-frozen-2026-10-26`.

All 50 original selected reports are retained, in the same order, with their text unchanged. The input selection is now fixed for repeatable baseline and ADK experiments. No replacement was necessary for basic source suitability: every report contains substantive clinical findings or a usable procedure/assessment/plan. Source ambiguity is retained and documented rather than repaired by guessing.

## Review scope and method

All 50 complete transcriptions were reviewed for source suitability, with individual annotations recording the case, facts to preserve, source caveats, and mistakes to watch for.

This review covers **source-input suitability**: meaningful content, apparent completeness for the report type, duplicates, selection coverage, and facts an explanation should preserve. The annotations provide reading priorities and exact source anchors. No generated answer or performance score was used to keep or reject a report.

A report can be suitable even when it ends at a consultation, pending test, planned operation, or handoff. We must explain the available note without inventing what happened afterward.

## Decision rules and result

- **Accept (31):** a usable source report; preserve its stated facts, timing, and uncertainty.
- **Accept with caveat (19):** a usable report with a specific conflict, unclear phrase, or numeric medication detail needing careful attribution. Keep the report, mark the uncertain detail, and do not invent a resolution. These reports remain in the 50-report denominator.
- **Replace (0):** would be required for an unusable fragment, duplicate, or a report with no meaningful content to explain. No report met that exclusion rule in this review.

`Accept` does not mean free of typos or medically validated. A caution about a literal medication value is not a finding that the dose is wrong.

The most consequential source conflicts include row **3606** (renal versus adrenal nodule), **85** (catheter replacement schedule), **3811** (unclear thyroid-treatment target), and **3290** (unexplained adjusted-calcium estimate). Medication wording in **3911** and **422** also needs careful source attribution. Preserve these details as uncertain; the review does not invent a corrected value or choose between conflicting source statements.

## What the checks found

- 50 unique source IDs, **20,512 whitespace words**, 15 source labels, and eight sampling structure groups.
- **48 medium reports, one short Allergy report (row 0), and one long Allergy report (row 4998).** These documented exceptions preserve the original three-report Allergy quota.
- Every selected transcription and word count matches the original data. All CSV/Excel cells match. Existing source/output hashes and candidate-audit selected IDs were verified.
- No blank transcription or explicit underscore/inaudible gap marker was found. Unicode apostrophes and the quarter-inch symbol in row 2365 are intact in the files.
- All **1,225 selected pairs** were checked for five-word-shingle Jaccard overlap. The largest overlap was **0.036212**, between rows 343 and 108, below the existing 0.85 near-duplicate threshold. This lexical check does not prove there is no conceptual overlap.
- Original specialty quotas, the 13/16/21 lower/middle/higher text-complexity split, structure coverage, and content-cue checks passed. Sampling categories are not clinical labels and do not measure medical severity.

## How to use this frozen set

1. Use the same `mtsamples_curated_50.csv` for both the baseline and ADK pipeline. Send the **transcription** as source input; do not put these review notes or expected behaviors in the generation prompt.
2. Save `source_row_id` and the frozen version with every result. Record model, prompt, retrieval snapshot/settings, failures, and revisions for each experiment.
3. Keep background MedlinePlus explanations separate from patient facts. A suspected diagnosis, pending test, consent risk, or future procedure must stay qualified.
4. For a source conflict, evaluate whether the answer preserves or acknowledges uncertainty rather than inventing a resolution. Do not silently drop difficult reports from published results.
5. Generate baseline and ADK outputs using the same inputs, then compare them with the project's agreed scoring rules.

## Files and verification

- [Frozen input CSV](mtsamples_curated_50.csv) and [Excel copy](mtsamples_curated_50.xlsx): unchanged inputs.
- [Selection manifest](selection_manifest.json): original sampling provenance plus frozen version/status.
- [Freeze manifest](freeze_manifest.json): hashes for fixed inputs/review files, source IDs, and each transcription; also records completed review status and verification results.
- [Structured review annotations](source_review_annotations.jsonl): the same report notes below, in machine-readable form.
- [Candidate audit](candidate_audit.csv): original selection/cleaning audit.

From the repository root:

```powershell
.\.venv\Scripts\python.exe -m evaluation.validate_frozen_set --source data/mtsamples.csv
```

A successful check reports 50 reports, matching frozen hashes, and exact correspondence to the original source. It does not call Gemini. Without `--source` it checks the frozen snapshot and review hashes but does not reopen the original full corpus.

The sampler refuses to overwrite a folder containing `freeze_manifest.json`. To reproduce the proposed selection independently, choose another output directory:

```powershell
.\.venv\Scripts\python.exe EDAs/mtsamples_sampling.py --profile medium --source data/mtsamples.csv --output data/mtsamples_reproduction
```

The generator produces the original proposed selection, not these authored review notes. Compare IDs and full transcription strings; regenerated Excel files may have different ZIP timestamps. A later selection/text correction needs a new version and recorded reason. Do not edit this frozen snapshot because a model performs poorly on a case.

## Quick index

Numbers 1-50 below are positions in the CSV. **Source row ID** is the stable zero-based data-row position in the original file; it is not an Excel line number.

| # | Source row ID | Report | Decision |
| --- | --- | --- | --- |
| 1 | 0 | [Allergic Rhinitis](#report-1-source-row-0) | accept |
| 2 | 4997 | [Asthma in a 5-year-old](#report-2-source-row-4997) | accept with caveat |
| 3 | 4998 | [Allergy Evaluation Consult](#report-3-source-row-4998) | accept |
| 4 | 4626 | [Transesophageal Echocardiography Probe](#report-4-source-row-4626) | accept |
| 5 | 4720 | [Non-Q-wave Myocardial Infarction](#report-5-source-row-4720) | accept |
| 6 | 4787 | [Heart Catheterization - 2](#report-6-source-row-4787) | accept |
| 7 | 4976 | [Abnormal Echocardiogram](#report-7-source-row-4976) | accept with caveat |
| 8 | 4457 | [Dietary Consultation - 1](#report-8-source-row-4457) | accept |
| 9 | 4345 | [H&P - Infant with fever](#report-9-source-row-4345) | accept |
| 10 | 4218 | [OB/GYN - H&P](#report-10-source-row-4218) | accept |
| 11 | 3938 | [Discharge Summary - COPD](#report-11-source-row-3938) | accept |
| 12 | 3885 | [Speech Therapy - Discharge Summary - 1](#report-12-source-row-3885) | accept with caveat |
| 13 | 3925 | [Discharge Summary - Urology & Nephrology](#report-13-source-row-3925) | accept |
| 14 | 3911 | [Lap Chole - Discharge Summary](#report-14-source-row-3911) | accept with caveat |
| 15 | 3846 | [Fall & Laceration](#report-15-source-row-3846) | accept |
| 16 | 3826 | [Mastoiditis - Discharge Summary](#report-16-source-row-3826) | accept |
| 17 | 3860 | [Consult/ER Report - OB/GYN](#report-17-source-row-3860) | accept with caveat |
| 18 | 3847 | [Fiberoptic Bronchoscopy with Lavage](#report-18-source-row-3847) | accept |
| 19 | 3808 | [Acute Cystitis & Diabetes Type II](#report-19-source-row-3808) | accept with caveat |
| 20 | 3805 | [Completion Thyroidectomy](#report-20-source-row-3805) | accept |
| 21 | 3811 | [Acquired Hypothyroidism Followup](#report-21-source-row-3811) | accept with caveat |
| 22 | 3608 | [CT Abdomen & Pelvis](#report-22-source-row-3608) | accept with caveat |
| 23 | 3685 | [Admission History & Physical - Nausea](#report-23-source-row-3685) | accept with caveat |
| 24 | 3606 | [CT Abdomen & Pelvis - 3](#report-24-source-row-3606) | accept with caveat |
| 25 | 3341 | [Gen Med Consult - 41](#report-25-source-row-3341) | accept |
| 26 | 3319 | [Gen Med H&P - 2](#report-26-source-row-3319) | accept |
| 27 | 3381 | [Gen Med Consult - 13](#report-27-source-row-3381) | accept |
| 28 | 3290 | [H&P - Gen Med - 1](#report-28-source-row-3290) | accept with caveat |
| 29 | 3186 | [Biopsy - Cervical Lymph Node](#report-29-source-row-3186) | accept |
| 30 | 3127 | [Polycythemia Vera Followup](#report-30-source-row-3127) | accept |
| 31 | 3159 | [Hematology Consult](#report-31-source-row-3159) | accept |
| 32 | 2964 | [Carotid Ultrasound](#report-32-source-row-2964) | accept |
| 33 | 2936 | [Craniotomy - Frontotemporal - 1](#report-33-source-row-2936) | accept with caveat |
| 34 | 2756 | [Wilson's Disease - Letter](#report-34-source-row-2756) | accept |
| 35 | 2946 | [Consult - Migraine](#report-35-source-row-2946) | accept with caveat |
| 36 | 2359 | [Ankle Sprain - H&P](#report-36-source-row-2359) | accept |
| 37 | 2365 | [Achilles Ruptured Tendon](#report-37-source-row-2365) | accept |
| 38 | 2059 | [Rotator cuff syndrome - H&P](#report-38-source-row-2059) | accept |
| 39 | 1571 | [MRI Knee - 4](#report-39-source-row-1571) | accept |
| 40 | 1516 | [Transesophageal Echocardiogram - 3](#report-40-source-row-1516) | accept with caveat |
| 41 | 1663 | [CT-Guided Biopsy - Kidney](#report-41-source-row-1663) | accept |
| 42 | 1394 | [Fundoplication & Gastrostomy Followup](#report-42-source-row-1394) | accept |
| 43 | 1384 | [Gen Med Progress Note - 7](#report-43-source-row-1384) | accept |
| 44 | 1396 | [Gen Med Progress Note - 11](#report-44-source-row-1396) | accept |
| 45 | 343 | [Shockwave Lithotripsy](#report-45-source-row-343) | accept with caveat |
| 46 | 1190 | [AV Fistula - 4](#report-46-source-row-1190) | accept with caveat |
| 47 | 422 | [Plantar Fasciotomy](#report-47-source-row-422) | accept with caveat |
| 48 | 85 | [Neurogenic Bladder - Consult](#report-48-source-row-85) | accept with caveat |
| 49 | 131 | [Flank Pain - Consult - 1](#report-49-source-row-131) | accept with caveat |
| 50 | 108 | [I&D - Penoscrotal Abscess](#report-50-source-row-108) | accept |

## Per-report reading notes

Each section explains what the report says, what an explanation should retain, and where a model could overstate something. No recorded source caveat means no specific caveat was identified in this review.

<a id="report-1-source-row-0"></a>

### 1. Allergic Rhinitis - source row 0

**Allergy / Immunology | 204 words | accept**

An allergy visit for persistent nasal symptoms, with asthma described as not flaring.

- **Preserve:** Keep the switch from Allegra to Zyrtec, loratadine as another option, Nasonex two sprays in each nostril for three weeks, and no known medicine allergies.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not turn environmental allergies into a drug allergy or claim an asthma attack. This is the documented 204-word short Allergy exception.
- **Exact source anchor:** `She has no known medicine allergies.`

<a id="report-2-source-row-4997"></a>

### 2. Asthma in a 5-year-old - source row 4997

**Allergy / Immunology | 390 words | accept with caveat**

A child with worsening wheezing and breathing distress is treated in the ER and accepted for admission.

- **Preserve:** Keep the working diagnosis of respiratory distress/asthma, oxygen and breathing treatments, low room-air oxygen measurement, and admission rather than discharge.
- **Source caveat:** The peak-flow sentence calls morning values both normal and reduced; the narrative switches from he to she and includes an unclear earlier-clinic statement about asthma.
- **Watch for:** Do not invent a consistent peak-flow timeline, confirm pneumonia from the differential, or treat the earlier clinic visit as the final hospital disposition.
- **Exact source anchor:** `working diagnosis of respiratory distress and asthma.`

<a id="report-3-source-row-4998"></a>

### 3. Allergy Evaluation Consult - source row 4998

**Allergy / Immunology | 638 words | accept**

An allergy consultation after swelling thought possibly related to Keflex, in a patient with dialysis-dependent renal failure.

- **Preserve:** Keep the uncertain cause, the recommendation to avoid cephalosporins, pending allergy-testing results, and the documented EpiPen/emergency follow-up plan.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not describe Keflex as proven by an allergy test, invent the test results, or present historical medication advice as a new recommendation. This is the 638-word long Allergy exception.
- **Exact source anchor:** `Acute allergic reaction, etiology uncertain, however, suspicious for Keflex.`

<a id="report-4-source-row-4626"></a>

### 4. Transesophageal Echocardiography Probe - source row 4626

**Cardiovascular / Pulmonary | 341 words | accept**

Successful echocardiography-probe insertion and unsuccessful vascular-line attempts before infant heart surgery.

- **Preserve:** Separate successful probe placement from failed line placement. Keep the small hematoma and temporary circulation concern, which improved by the end.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not say all procedures succeeded, claim no bleeding at any point, or infer the outcome of the later heart operation.
- **Exact source anchor:** `At the end of the procedure, the circulation of the leg was intact.`

<a id="report-5-source-row-4720"></a>

### 5. Non-Q-wave Myocardial Infarction - source row 4720

**Cardiovascular / Pulmonary | 458 words | accept**

A cardiac consultation records non-Q-wave myocardial infarction, an episode of atrial fibrillation, and diabetes/renal comorbidity.

- **Preserve:** Preserve conversion to sinus rhythm, rising troponin values if mentioned, planned catheterization with possible intervention, and dialysis history.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not convert planned catheterization or possible intervention into a completed procedure or invent chest pain that the note does not establish.
- **Exact source anchor:** `The patient is currently in sinus rhythm.`

<a id="report-6-source-row-4787"></a>

### 6. Heart Catheterization - 2 - source row 4787

**Cardiovascular / Pulmonary | 477 words | accept**

Right-heart catheterization for heart failure leads to planned ICU medication titration.

- **Preserve:** Keep the low-perfusion interpretation, plan for Primacor, reason dobutamine cannot continue, and stated Lasix/amiodarone changes.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not invent successful home discharge, combine all listed drugs as continued therapy, or treat measurements as a recovery claim.
- **Exact source anchor:** `we will transfer the patient to the Intensive Care Unit for titration of the Primacor therapy.`

<a id="report-7-source-row-4976"></a>

### 7. Abnormal Echocardiogram - source row 4976

**Cardiovascular / Pulmonary | 482 words | accept with caveat**

A cardiac consultation during a GI admission describes valve leakage and shortness of breath, with medical treatment chosen.

- **Preserve:** Keep severe mitral/tricuspid regurgitation, normal left ventricular function, and the decision not to undergo the proposed transesophageal study.
- **Source caveat:** Hypertension is described as a history in one section and questionable in another. Retain that uncertainty if summarizing this detail.
- **Watch for:** Do not invent a valve operation, label the declined test as completed, or use normal pumping function to erase valve findings.
- **Exact source anchor:** `the patient does not wish to proceed with a transesophageal echocardiogram.`

<a id="report-8-source-row-4457"></a>

### 8. Dietary Consultation - 1 - source row 4457

**Consult - History and Phy. | 295 words | accept**

A dietary follow-up records modest weight loss, food-record keeping, and snacking difficulties.

- **Preserve:** Keep the 1.5-pound loss over a month, planned afternoon snack around 2:30-3 p.m., continued activity/records, and one-month follow-up.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not diagnose measured hypoglycemia from a discussion of symptoms or present weight-loss counseling as an already achieved future result.
- **Exact source anchor:** `Will plan to follow the patient in one month for ongoing support.`

<a id="report-9-source-row-4345"></a>

### 9. H&P - Infant with fever - source row 4345

**Consult - History and Phy. | 418 words | accept**

A febrile infant is evaluated for infection, with a likely viral illness listed rather than a proven cause.

- **Preserve:** Keep the sepsis workup, IV fluids, and antibiotics until spinal-fluid/blood cultures are negative for 48 hours.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not report meningitis, sepsis, or negative cultures as confirmed. Avoid repeating judgmental family descriptions as explanations of the illness.
- **Exact source anchor:** `the child is being treated in a rule out sepsis protocol.`

<a id="report-10-source-row-4218"></a>

### 10. OB/GYN - H&P - source row 4218

**Consult - History and Phy. | 490 words | accept**

An initial prenatal examination includes positive pregnancy tests, early gestational information, nutrition counseling, and follow-up.

- **Preserve:** Keep early-pregnancy timing as recorded, bee/wasp and pet-dander allergies, the prenatal prescription, and four-week return plan.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not say fetal movement was abnormally absent, turn counseling into a diagnosed complication, or treat this historical record as current pregnancy advice.
- **Exact source anchor:** `fetal activity is not yet detected (due to early stage of pregnancy).`

<a id="report-11-source-row-3938"></a>

### 11. Discharge Summary - COPD - source row 3938

**Discharge Summary | 379 words | accept**

A discharge summary describes improving COPD exacerbation plus an abnormal cardiac stress study and follow-up needs.

- **Preserve:** Keep the reversible defect suggestive of ischemia, cardiology follow-up in a week, primary-care follow-up tomorrow, anemia follow-up, and complete prednisone taper if reproduced.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not describe a negative cardiac workup, omit urgent return instructions, or flatten the multi-step prednisone taper into one ongoing daily dose.
- **Exact source anchor:** `Reversible defect suggestive of ischemia, ejection fraction of 55%.`

<a id="report-12-source-row-3885"></a>

### 12. Speech Therapy - Discharge Summary - 1 - source row 3885

**Discharge Summary | 471 words | accept with caveat**

Speech-therapy discharge records improved comprehension and swallowing but continuing expressive-language limitations.

- **Preserve:** Keep initial versus later aphasia scores, oral intake with the G-tube still present, advice to discuss removal, and discharge for a progress plateau.
- **Source caveat:** The note reports achievement of a yes/no accuracy goal while also describing ongoing difficulty with verbal and head-gesture responses; response modes are not fully reconciled.
- **Watch for:** Do not claim complete language recovery, guaranteed yes/no reliability in every mode, or that the feeding tube was already removed.
- **Exact source anchor:** `however, her G-tube is still present.`

<a id="report-13-source-row-3925"></a>

### 13. Discharge Summary - Urology & Nephrology - source row 3925

**Discharge Summary | 493 words | accept**

A child with one kidney and persistent obstruction receives a nephrostomy and treatment for a Pseudomonas urinary infection.

- **Preserve:** Keep failed internal-tube replacement, successful percutaneous drainage, creatinine improvement, ciprofloxacin at discharge, and planned urology/surgical follow-up.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not turn a possible future reconstructive operation into a completed repair or equate a draining nephrostomy with permanent resolution.
- **Exact source anchor:** `followup in Urology in 1 to 2 weeks`

<a id="report-14-source-row-3911"></a>

### 14. Lap Chole - Discharge Summary - source row 3911

**Discharge Summary | 505 words | accept with caveat**

A postoperative discharge describes gallbladder removal in a patient receiving dialysis, with a long medication list.

- **Preserve:** Keep completed laparoscopic cholecystectomy, dialysis history, the instruction to stop Premarin, and surgeon follow-up in 3-5 days.
- **Source caveat:** The source lists Synthroid 0.5 mg and uses awkward tablet/strength wording for Renagel. These are source details, not medication instructions validated by this review.
- **Watch for:** Do not silently correct/convert doses or resolve tablet-strength ambiguity by guessing. Keep uncertain medication details attributed to the source.
- **Exact source anchor:** `Synthroid 0.5 mg 1 tablet p.o. daily`

<a id="report-15-source-row-3846"></a>

### 15. Fall & Laceration - source row 3846

**Emergency Room Reports | 302 words | accept**

An ER note records a fall, facial cuts repaired with sutures, alcohol-related findings, and a handoff for further care.

- **Preserve:** Keep denial of loss of consciousness, no fracture on the cited cervical-spine films, repaired lacerations, and the continuing-care handoff.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not invent discharge, normal head imaging, or a concussion diagnosis. A note ending at handoff is not necessarily truncated.
- **Exact source anchor:** `his care will be turned over to Dr. G for further evaluation and care.`

<a id="report-16-source-row-3826"></a>

### 16. Mastoiditis - Discharge Summary - source row 3826

**Emergency Room Reports | 318 words | accept**

A discharge summary distinguishes initially suspected mastoiditis from the final assessment of acute right middle-ear infection.

- **Preserve:** Keep that mastoiditis was ruled out, symptoms improved, discharge antibiotics were prescribed, and ENT/primary-care follow-up was requested.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not use the sample title or initial CT concern as a confirmed mastoiditis diagnosis.
- **Exact source anchor:** `Suspected mastoiditis ruled out.`

<a id="report-17-source-row-3860"></a>

### 17. Consult/ER Report - OB/GYN - source row 3860

**Emergency Room Reports | 418 words | accept with caveat**

An obstetric ER consultation after a reported suicide attempt discusses pregnancy of unknown gestation and planned dating tests.

- **Preserve:** Keep unknown gestation, the patient's belief that she passed tissue as a report rather than a confirmed loss, medication-allergy reactions, and planned HCG/ultrasound.
- **Source caveat:** The assessment refers to substances taken, but exposure quantities and full overdose history are absent. The note cannot support reconstructing those details.
- **Watch for:** Do not invent ingestion amounts, confirm miscarriage or fetal health, or turn the historical fetal-risk discussion into a present-day safety guarantee.
- **Exact source anchor:** `at unknown gestation who presents after suicide attempt.`

<a id="report-18-source-row-3847"></a>

### 18. Fiberoptic Bronchoscopy with Lavage - source row 3847

**Emergency Room Reports | 440 words | accept**

A bronchoscopy note describes clearing obstructing airway clots after trauma while ventilation continues.

- **Preserve:** Keep left-sided obstruction, clot removal, continued ventilator support, stable procedure observations, and pending postprocedure chest X-ray.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not report the pending X-ray result, permanent lung recovery, or removal from ventilation. Preprocedure respiratory failure is not a new procedural complication.
- **Exact source anchor:** `Postprocedure chest x-ray is pending at this time.`

<a id="report-19-source-row-3808"></a>

### 19. Acute Cystitis & Diabetes Type II - source row 3808

**Endocrinology | 299 words | accept with caveat**

An outpatient note assesses uncontrolled type II diabetes and acute cystitis and lists prescriptions and further workup.

- **Preserve:** Keep the explicit final assessment, listed medication strengths/frequency without inventing duration, and planned endocrinology consultation/CBC.
- **Source caveat:** The generic past history says no significant history despite diabetes in the HPI; the GU checklist denies bladder disorder despite the acute-cystitis assessment.
- **Watch for:** Do not state there is no diabetes/bladder problem, invent a culture result, or turn 30 tablets into an explicitly documented course duration.
- **Exact source anchor:** `Diabetes type II uncontrolled.  Acute cystitis.`

<a id="report-20-source-row-3805"></a>

### 20. Completion Thyroidectomy - source row 3805

**Endocrinology | 423 words | accept**

Completion thyroid surgery and right paratracheal-node removal follow a prior specimen showing papillary thyroid carcinoma.

- **Preserve:** Keep prior left-sided surgery separate from the completion operation, preserve nerve/parathyroid protection, and note nodes were sent as a specimen.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not call discussed surgical risks actual complications or diagnose lymph-node metastasis without pathology.
- **Exact source anchor:** `sent as a separate specimen labeled right paratracheal lymph nodes.`

<a id="report-21-source-row-3811"></a>

### 21. Acquired Hypothyroidism Followup - source row 3811

**Endocrinology | 486 words | accept with caveat**

Endocrine follow-up after thyroidectomy plans repeat laboratory tests and ongoing surveillance.

- **Preserve:** Keep prior cancer/surgery history, repeat tests today, next-week call, six-month follow-up, and earlier labs versus pending repeat values.
- **Source caveat:** The list separately includes levothyroxine and Synthroid; target phrasing 'somewhere between 0.41 or less' is unclear and no new taper dose is supplied.
- **Watch for:** Do not manufacture a precise TSH range/new dose, count possible duplicate medication names as confirmed separate treatment, or say repeat tests returned.
- **Exact source anchor:** `get her TSH somewhere between 0.41 or less.`

<a id="report-22-source-row-3608"></a>

### 22. CT Abdomen & Pelvis - source row 3608

**Gastroenterology | 324 words | accept with caveat**

A follow-up abdominal/pelvic CT describes stable aortoiliac graft repair without a leak and advanced left-kidney atrophy.

- **Preserve:** Keep stability/no leak, different aneurysm measurements/levels, and left renal atrophy.
- **Source caveat:** The comparison date is 10/20/05 in the body and 10/20/04 in the impression. The source does not resolve the year.
- **Watch for:** Do not choose a comparison year as certain, merge the two aneurysm dimensions, or turn diverticulosis without diverticulitis into active diverticulitis.
- **Exact source anchor:** `stable compared to the study of 10/20/04.`

<a id="report-23-source-row-3685"></a>

### 23. Admission History & Physical - Nausea - source row 3685

**Gastroenterology | 379 words | accept with caveat**

An admission after gastric bypass assesses a bile-duct stone and possible gallbladder inflammation.

- **Preserve:** Keep the question mark on cholecystitis, planned ultrasound/antibiotics, possible operation, and stated difficulty of ERCP with altered anatomy.
- **Source caveat:** The HPI includes the garbled sentence 'He feels like he was on it but has not done so.' Its intended symptom cannot be established.
- **Watch for:** Do not invent vomiting from the garbled phrase, make cholecystitis certain, or report the planned operation as completed.
- **Exact source anchor:** `Choledocholithiasis, ? cholecystitis.`

<a id="report-24-source-row-3606"></a>

### 24. CT Abdomen & Pelvis - 3 - source row 3606

**Gastroenterology | 408 words | accept with caveat**

A noncontrast abdominal/pelvic CT reports a hernia and incompletely characterized lesions with follow-up recommendations.

- **Preserve:** Keep noncontrast limitations, possible rather than certain cirrhosis/cysts, lung-nodule follow-up in three months, and recommended further imaging.
- **Source caveat:** The body describes a 1.9-cm left renal nodule, while the impression calls an indeterminate left adrenal nodule. These locations cannot be silently reconciled.
- **Watch for:** Do not select renal versus adrenal as a definitive corrected site, invent a cancer diagnosis, or call an indeterminate lesion benign.
- **Exact source anchor:** `Indeterminate left adrenal nodule`

<a id="report-25-source-row-3341"></a>

### 25. Gen Med Consult - 41 - source row 3341

**General Medicine | 374 words | accept**

A visit records urinary/flank symptoms, abnormal urinalysis, pharyngitis, and pending cultures.

- **Preserve:** Keep Rocephin already given, the conditional next-dose/Omnicef plan, pending urine/throat cultures, and return instructions.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not say cultures are positive, identify an organism, or turn the conditional antibiotic plan into two simultaneous confirmed courses.
- **Exact source anchor:** `Culture and sensitivity is pending.`

<a id="report-26-source-row-3319"></a>

### 26. Gen Med H&P - 2 - source row 3319

**General Medicine | 379 words | accept**

An admission examination records pneumonia and a workup for possible Pneumocystis, tuberculosis, and HIV-related illness.

- **Preserve:** Keep established respiratory findings, suspected causes as unconfirmed, planned sputum/HIV/RPR tests, and documented empiric/supportive treatment.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not infer HIV/tuberculosis from demographics or sexual history, turn the workup into diagnoses, or repeat stigmatizing descriptions as causal explanations.
- **Exact source anchor:** `Check HIV and RPR.`

<a id="report-27-source-row-3381"></a>

### 27. Gen Med Consult - 13 - source row 3381

**General Medicine | 383 words | accept**

A chronic-care visit finds suboptimal blood-pressure control and plans lab, breast-imaging, and bone-density follow-up.

- **Preserve:** Keep blood-pressure control as suboptimal, chronic conditions, intolerance wording for Prevacid, and the three-to-six-month return plan.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not turn intolerance into a proven immune allergy, invent planned-test results, or confuse normal examination findings with absence of chronic disease.
- **Exact source anchor:** `Hypertension, suboptimal control.`

<a id="report-28-source-row-3290"></a>

### 28. H&P - Gen Med - 1 - source row 3290

**General Medicine | 524 words | accept with caveat**

A GI-illness admission describes dehydration, renal dysfunction, electrolyte concerns, limited history, and conditional further workup.

- **Preserve:** Keep unknown diabetes status and baseline kidney function, replacement/monitoring plans, and possible myeloma workup conditional on family discussion.
- **Source caveat:** Listed calcium 10.3 and albumin 3.8 do not transparently support the later adjusted calcium 'somewhere around 12'; no calculation is supplied. Demographic wording also differs across sections.
- **Watch for:** Do not calculate a new corrected value, treat the estimate as independently verified, invent family-history details, or diagnose diabetes/myeloma.
- **Exact source anchor:** `Her baseline is unknown.`

<a id="report-29-source-row-3186"></a>

### 29. Biopsy - Cervical Lymph Node - source row 3186

**Hematology - Oncology | 318 words | accept**

A right cervical lymph-node excision follows nondiagnostic earlier investigations.

- **Preserve:** Keep right-sided biopsy, specimen sent for pathology, no recorded operative complication, and next-day drain-removal follow-up.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not infer cancer from the source specialty or biopsy, or invent pathology results.
- **Exact source anchor:** `sent for pathologic examination.`

<a id="report-30-source-row-3127"></a>

### 30. Polycythemia Vera Followup - source row 3127

**Hematology - Oncology | 496 words | accept**

Follow-up for polycythemia vera with secondary myelofibrosis discusses treatment intolerance and a possible trial.

- **Preserve:** Keep stopped/intolerable prior therapies, aspirin prophylaxis, trial inquiry rather than enrollment, shin X-rays ordered, and three-week follow-up.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not report trial acceptance, a newly started JAK-2 inhibitor, a proven clot, or fracture from an X-ray only ordered.
- **Exact source anchor:** `see whether he will be a candidate for the LBH trial.`

<a id="report-31-source-row-3159"></a>

### 31. Hematology Consult - source row 3159

**Hematology - Oncology | 512 words | accept**

A hematology consultation covers pulmonary embolism, right-leg thrombosis, and acute renal failure.

- **Preserve:** Keep anticoagulation, pending hypercoagulability studies, and dialysis as planned/possibly temporary rather than completed.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not diagnose an inherited clotting disorder before results or turn absent calf pain into absence of the documented clot.
- **Exact source anchor:** `we will await hypercoagulable studies`

<a id="report-32-source-row-2964"></a>

### 32. Carotid Ultrasound - source row 2964

**Neurology | 348 words | accept**

A carotid ultrasound finds bilateral plaque, worse on the left, and recommends CTA.

- **Preserve:** Keep laterality and qualified finding of at least 50% left internal-carotid narrowing, with CTA to assess it further.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not round to exactly 50%, call the arteries normal, or invent CTA results/treatment.
- **Exact source anchor:** `at least 50% stenosis of the left internal carotid artery`

<a id="report-33-source-row-2936"></a>

### 33. Craniotomy - Frontotemporal - 1 - source row 2936

**Neurology | 404 words | accept with caveat**

An emergency left-sided craniotomy evacuates acute subdural blood in a patient with leukemia and low blood-cell counts.

- **Preserve:** Keep left-sided surgery, approximately 80% apparent removal, the drain, and transfer for further ICU management.
- **Source caveat:** The closing discussion says 'this actual skin looked good' after a postoperative scan is described; the intended word/result is unclear.
- **Watch for:** Do not silently replace skin with scan, report complete evacuation, or guarantee imaging excluded all new hemorrhage.
- **Exact source anchor:** `apparent removal of about 80% of the subdural`

<a id="report-34-source-row-2756"></a>

### 34. Wilson's Disease - Letter - source row 2756

**Neurology | 409 words | accept**

A referral requests atrial-fibrillation/anticoagulation advice in a patient with Wilson's disease.

- **Preserve:** Keep spontaneous return to sinus rhythm, current aspirin/metoprolol, and uncertainty about cirrhosis and long-term anticoagulation.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not confirm cirrhosis, say Coumadin was started, or turn a request for specialist advice into a settled decision.
- **Exact source anchor:** `his diagnosis of cirrhosis`

<a id="report-35-source-row-2946"></a>

### 35. Consult - Migraine - source row 2946

**Neurology | 490 words | accept with caveat**

A neurology consultation describes difficult-to-control migraine-like headaches, investigation, and medication trials.

- **Preserve:** Keep reported negative brain imaging, cervical-disc findings that do not explain the headache per the note, and vasculitis conditions as rule-outs.
- **Source caveat:** The differential contains 'temporal and arthritis'. It should not be expanded into a definite disease label by guessing.
- **Watch for:** Do not diagnose the rule-out list, invent workup results, or recast past medication intolerance as a current regimen.
- **Exact source anchor:** `Rule out sinusitis.`

<a id="report-36-source-row-2359"></a>

### 36. Ankle Sprain - H&P - source row 2359

**Orthopedic | 326 words | accept**

A right ankle sprain note includes a preliminary film interpretation and a later pain-treatment change.

- **Preserve:** Keep no fracture on the clinician's read while radiology interpretation is pending, the cast, and next-day pain call.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not claim final radiologist clearance, invent the unknown blood-pressure medicine dose, or describe a new fracture without evidence.
- **Exact source anchor:** `Radiologic interpretation is pending.`

<a id="report-37-source-row-2365"></a>

### 37. Achilles Ruptured Tendon - source row 2365

**Orthopedic | 469 words | accept**

A right Achilles-tendon rupture consultation discusses planned repair and staged rehabilitation.

- **Preserve:** Keep surgery as planned, postoperative nonweightbearing periods, estimated 6-9-month return to sport, and recorded travel-related medication planning.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not report completed surgery or apply postoperative restrictions to the preoperative phase. The quarter-inch lift symbol is intact Unicode; do not substitute another measurement.
- **Exact source anchor:** `Right Achilles tendon rupture.`

<a id="report-38-source-row-2059"></a>

### 38. Rotator cuff syndrome - H&P - source row 2059

**Orthopedic | 526 words | accept**

A right shoulder assessment describes rotator-cuff syndrome, limited movement, an injection, and possible later imaging.

- **Preserve:** Keep injection as performed, MRI/arthrogram as conditional if initial treatments fail, and activity restriction.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not diagnose a proven tear, say all discussed options were performed, or endorse the historical prescription as present-day treatment advice.
- **Exact source anchor:** `may be required to rule out a rotator cuff tear.`

<a id="report-39-source-row-1571"></a>

### 39. MRI Knee - 4 - source row 1571

**Radiology | 298 words | accept**

A left-knee MRI describes ligament injuries, complex fluid, and meniscal changes without a definite surface tear.

- **Preserve:** Keep high-grade partial ACL finding/qualified interpretation, partial lateral-collateral injury, intact PCL, and possible blood products.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not turn partial tears into complete tears, establish a meniscal tear, or turn possible blood products into a definite hemorrhage.
- **Exact source anchor:** `no definite evidence of a tear.`

<a id="report-40-source-row-1516"></a>

### 40. Transesophageal Echocardiogram - 3 - source row 1516

**Radiology | 384 words | accept with caveat**

A transesophageal echo assesses a mechanical aortic valve, reporting moderate narrowing and preserved ventricular function.

- **Preserve:** Keep mechanical aortic valve, 3.2 m/sec velocity and 1.2 cm2 area if included, no seen thrombus, and two-to-three-year reassessment.
- **Source caveat:** The preoperative line says atrial rather than aortic valve; mitral leakage is mild in one section and mild-to-moderate in another.
- **Watch for:** Do not invent a new valve replacement, silently reconcile inconsistent labels/severity, or turn no seen thrombus into a future guarantee.
- **Exact source anchor:** `Moderate stenosis of aortic valve replacement.`

<a id="report-41-source-row-1663"></a>

### 41. CT-Guided Biopsy - Kidney - source row 1663

**Radiology | 426 words | accept**

A CT-guided right-kidney mass biopsy causes bleeding and a small hematoma, with bleeding stopped during the procedure.

- **Preserve:** Keep actual bleeding/hematoma, Gelfoam control, specimens sent to the lab, planned observation, and follow-up for results.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not call the procedure complication-free, diagnose cancer from an indeterminate mass, or claim pathology/final discharge was confirmed.
- **Exact source anchor:** `active bleeding through the biopsy needle stopped by tract embolization with Gelfoam pledgets.`

<a id="report-42-source-row-1394"></a>

### 42. Fundoplication & Gastrostomy Followup - source row 1394

**SOAP / Chart / Progress Notes | 370 words | accept**

Infant fundoplication/gastrostomy follow-up finds good healing while airway treatment remains under review.

- **Preserve:** Keep partial oral feeding with the rest by G-tube, button reinsertion teaching, and possible future decannulation/airway surgery.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not say the feeding tube was permanently removed, all feeds are oral, or the tracheostomy was already removed.
- **Exact source anchor:** `the rest is given by G-tube.`

<a id="report-43-source-row-1384"></a>

### 43. Gen Med Progress Note - 7 - source row 1384

**SOAP / Chart / Progress Notes | 419 words | accept**

A pediatric visit assesses viral gastroenteritis with improving vomiting and dietary/follow-up instructions.

- **Preserve:** Keep no vomiting on the visit day, ongoing diarrhea, preserved exam findings, and the clinician's plan as historical source content.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not prove food poisoning from a shared meal, identify an organism, or turn a rash without petechiae into a bleeding diagnosis.
- **Exact source anchor:** `He has not had any emesis today.`

<a id="report-44-source-row-1396"></a>

### 44. Gen Med Progress Note - 11 - source row 1396

**SOAP / Chart / Progress Notes | 514 words | accept**

Diabetes/hypertension follow-up also addresses shoulder pain and overdue breast imaging.

- **Preserve:** Keep missed second metformin doses as reported behavior, the old A1c date, planned repeat labs/mammogram, and three-month follow-up.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not report the older A1c as today's result, turn missed doses into a prescribed reduction, or diagnose malignancy from requested imaging.
- **Exact source anchor:** `she has been skipping her second dose during the day.`

<a id="report-45-source-row-343"></a>

### 45. Shockwave Lithotripsy - source row 343

**Surgery | 296 words | accept with caveat**

A right kidney-stone procedure uses shockwaves and removes two stents, with later imaging planned.

- **Preserve:** Keep 2,500 shocks, two removed stents, stable immediate recovery, and KUB planned in two to three months.
- **Source caveat:** The initial energy-level wording is 'O2', ambiguous in this equipment-setting context.
- **Watch for:** Do not interpret O2 as oxygen therapy, claim all fragments passed, or turn discussed MI/DVT/PE risks into actual complications.
- **Exact source anchor:** `total of 2500 shocks were applied.`

<a id="report-46-source-row-1190"></a>

### 46. AV Fistula - 4 - source row 1190

**Surgery | 398 words | accept with caveat**

A first-stage right-arm arteriovenous fistula is created for dialysis access amid existing venous problems.

- **Preserve:** Keep right-arm laterality, first-stage status, left occlusion versus right stenosis, no heparin given, and no recorded operative complications.
- **Source caveat:** The note twice says 'A grade 2 was felt' without identifying what was graded. This review cannot supply the missing meaning.
- **Watch for:** Do not invent a specific thrill grade, claim immediate access readiness, or call the second stage completed.
- **Exact source anchor:** `We did not give heparin.`

<a id="report-47-source-row-422"></a>

### 47. Plantar Fasciotomy - source row 422

**Surgery | 489 words | accept with caveat**

A left-foot partial plantar fasciotomy follows failed conservative care, with postoperative restrictions and medications.

- **Preserve:** Keep left-sided partial release, nonweightbearing with crutches, follow-up, and administered anesthetic versus discharge medicines.
- **Source caveat:** The note records an additional 80 cc of 1% lidocaine. The numeric source text is preserved without validating or correcting the dose.
- **Watch for:** Do not silently replace the volume, turn local-anesthetic administration into a take-home prescription, or treat historical dosing as independently approved advice.
- **Exact source anchor:** `an additional 80 cc of 1% lidocaine`

<a id="report-48-source-row-85"></a>

### 48. Neurogenic Bladder - Consult - source row 85

**Urology | 323 words | accept with caveat**

A neurogenic-bladder consultation reviews self-catheterization/recurrent infection and plans nighttime prophylaxis.

- **Preserve:** Keep current absence of symptoms, transplant/steroid history, planned Keflex prophylaxis, and follow-up.
- **Source caveat:** Catheter replacement is weekly in history/plan but three times a week in the impression; catheterizing three times daily is a separate frequency.
- **Watch for:** Do not merge catheter-use frequency with replacement frequency or present one replacement schedule as unambiguously established.
- **Exact source anchor:** `changing catheter weekly`

<a id="report-49-source-row-131"></a>

### 49. Flank Pain - Consult - 1 - source row 131

**Urology | 346 words | accept with caveat**

A consultation for a large left ureteral stone plans laser treatment the following day and discusses possible additional procedures.

- **Preserve:** Keep reported approximate 1.3-cm size, improving nausea/vomiting, planned KUB/culture, possible stent, and uncertain one-session success.
- **Source caveat:** The HPI includes a generic denial of 'burning or pain' despite the explicit flank-pain complaint. The denial's scope is unclear.
- **Watch for:** Do not erase the main pain complaint, say treatment already occurred, or promise 100% success.
- **Exact source anchor:** `the success of the surgery may be or may not be 100%`

<a id="report-50-source-row-108"></a>

### 50. I&D - Penoscrotal Abscess - source row 108

**Urology | 453 words | accept**

An operation drains a penoscrotal abscess and biopsies an abnormal mass, leaving a catheter and packing.

- **Preserve:** Keep performed drainage/biopsy/dilation, pathology uncertainty, retained Foley, and possible later tissue-removal surgery as conditional.
- **Source caveat:** No specific conflict or usability caveat recorded.
- **Watch for:** Do not diagnose squamous-cell carcinoma before pathology or treat possible Fournier's gangrene/penectomy risks as confirmed outcomes.
- **Exact source anchor:** `biopsies were sent for pathology analysis.`

## What is completed and what comes next

The **source review and input freeze are completed**. The same 50 reports are ready for repeatable baseline and ADK runs with documented caveats.

Next, generate baseline and ADK explanations with traceable IDs and compare their results using the same scoring rules. Use the report notes to understand source conflicts, important facts, and potential unsupported additions.
