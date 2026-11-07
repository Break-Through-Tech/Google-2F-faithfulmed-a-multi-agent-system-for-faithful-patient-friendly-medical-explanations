# Source-only checklists for the five pilot reports

Version: **pilot-source-facts-2026-11-07-v1**. Prepared November 7, 2026.

These are the important source facts to look for in either system's answer. They were prepared from the frozen original reports, without reading generated answers during this task. No API calls were made. The source text and frozen set were not changed.

**Timing limitation:** report 4998 had already been run and discussed before this inventory existed. Its checklist is therefore retrospective, not a blinded pre-generation reference. The other four inventories were prepared before their pilot generation in this work.

Use the same IDs and facts for baseline and ADK. Routine normal exams and repetitive measurements are intentionally not an exhaustive checklist; valid extra source facts are allowed. A fact that is absent is an omission; an included but changed fact is a distortion. A combined schedule or linked fact requires all its stated parts for complete coverage. If only part is covered, record the missing portion explicitly rather than awarding full coverage.

For source conflicts, preserve the discrepancy. A safe explanation may say the report is inconsistent; it should not silently choose a location or diagnosis. For 3606, the renal and adrenal entries are two linked anchors for one discrepancy, not proof of two separate nodules. Do not count the same conflict twice when reporting affected outputs.

See [support/conflict policy](SUPPORT_CONFLICT_POLICY.md). These are operational checklists, not independently adjudicated clinical gold labels.

## Files and reuse

- Editable, versioned definitions: [pilot_key_facts_v1.json](pilot_key_facts_v1.json).
- Ready-to-use inventories and hashes: `data/source_key_facts/pilot_source_facts_2026-11-07_v1/`.
- Each `source_row_<id>.json` includes the unchanged full source, stable fact IDs, exact quotes, source digest, fact digest, and provenance.
- `manifest.json` records file hashes and fact counts.
- All 53 anchors passed the existing evaluator's quote/schema validation. This checks exact anchoring, not semantic correctness or clinical completeness.

Rebuild in a fresh directory without API calls:

```powershell
.\.venv\Scripts\python.exe -m evaluation.prepare_pilot_checklists --output-dir data/source_key_facts/pilot_source_facts_reproduction
```

Pass the prepared directory to the paired runner's `--key-facts-dir` when exporting saved results for scoring. Export itself is offline; running the live scorer is a separate API-consuming step. Keep failed generations and unreleased drafts distinct from final answers. Changing this inventory requires a new version and rescoring both systems.

## 4998:  Allergy Evaluation Consult

12 key facts.

### R4998-K01

Perioral swelling occurred; the cause was uncertain.

> the patient had an acute event of perioral swelling, etiology uncertain, occurring on 05/03/2008

### R4998-K02

Keflex was suspected, not established as the cause.

> Acute allergic reaction, etiology uncertain, however, suspicious for Keflex.

### R4998-K03

Renal failure requires dialysis.

> Renal failure requiring dialysis.

### R4998-K04

The patient has hypertension.

> history of hypertension.

### R4998-K05

Heparin causes thrombocytopenia in this patient.

> Heparin causing thrombocytopenia.

### R4998-K06

No further problems were reported after discharge and treatment.

> No further problems have been noted upon his discharge and treatment, which included corticosteroid therapy and antihistamine therapy and monitoring.

### R4998-K07

Food and environmental allergy testing was performed; results and further recommendations are still to follow.

> RAST allergy testing for both food and environmental allergies was performed, and we will get the results back to the patient with further recommendations to follow.

### R4998-K08

Avoiding a specific food or inhalant would depend on high sensitivity in the pending testing.

> If there is any specific food or inhalant allergen that is found to be quite high on the sensitivity scale, we would probably recommend the patient to avoid the offending agent

### R4998-K09

The clinician recommended stopping further cephalosporin use because of the suspected reaction.

> At this point, I would recommend the patient stopping any further use of cephalosporin antibiotics, which may be the cause of his allergic reaction, and I would consider this an allergy.

### R4998-K10

Atenolol complicates anaphylaxis treatment but was considered medically necessary; do not invent a stop instruction.

> Being on atenolol, the patient has a more difficult time treating acute anaphylaxis, but I do think this is medically necessary at this time

### R4998-K11

An EpiPen was prescribed for an acute or impending allergic reaction.

> An EpiPen was also prescribed in the event of acute angioedema or allergic reaction or sensation of impending allergic reaction

### R4998-K12

Go directly to the emergency room after EpiPen administration.

> he is aware he needs to proceed directly to the emergency room for further evaluation and treatment recommendations after administration of an EpiPen.


## 3938:  Discharge Summary - COPD

17 key facts.

### R3938-K01

The COPD exacerbation was improving with steroids and bronchodilators.

> Chronic obstructive pulmonary disease exacerbation improving, on steroids and bronchodilators.

### R3938-K02

CT angiography was negative for pulmonary embolism.

> CT angiography, negative for pulmonary arterial embolism.

### R3938-K03

The nuclear scan was abnormal with a reversible defect suggestive of ischemia; EF was 55%.

> Nuclear myocardial perfusion scan, abnormal.  Reversible defect suggestive of ischemia, ejection fraction of 55%.

### R3938-K04

Coronary disease was present, and Cardiology recommended discharge with clinic follow-up despite the abnormal scan.

> Coronary artery disease, abnormal nuclear scan, discussed with Cardiology Dr. X, who recommended to discharge the patient and follow up in the clinic.

### R3938-K05

Type 2 diabetes is a discharge diagnosis.

> Diabetes mellitus type 2.

### R3938-K06

Anemia remained stable; admission hemoglobin was 8.8.

> His hemoglobin on admission was 8.8, and has remained stable.

### R3938-K07

Low potassium was replaced.

> Hypokalemia, replaced.

### R3938-K08

Bronchitis is a discharge diagnosis.

> Bronchitis.

### R3938-K09

Recorded allergies are lisinopril and penicillin.

> ALLERGIES: , LISINOPRIL AND PENICILLIN.

### R3938-K10

Preserve every step of the oral daily prednisone taper, including the final two-day step.

> Prednisone tapering dose 40 mg p.o. daily for three days, then 30 mg p.o. daily for three days, then 20 mg p.o. daily for three days, then 10 mg p.o. daily for three days, and 5 mg p.o. daily for two days.

### R3938-K11

Levaquin is 750 mg by mouth daily for five more days.

> Levaquin 750 mg p.o. daily for 5 more days.

### R3938-K12

Protonix is 40 mg by mouth daily.

> Protonix 40 mg p.o. daily.

### R3938-K13

Continue other current home medications.

> The patient can continue other current home medications at home.

### R3938-K14

Cardiology follow-up is in one week.

> Recommend to follow up with Cardiology Dr. X's office in a week.

### R3938-K15

Hematology follow-up is for anemia workup, with no interval stated.

> The patient is recommended to see Hematology Dr. Y in the office for workup of anemia.

### R3938-K16

Primary care follow-up is tomorrow.

> Follow up with primary care physician's office tomorrow.

### R3938-K17

Return to the emergency room for worsening breathlessness, chest pain, fever, or acute symptoms.

> If increasing shortness of breath, chest pain, fever, any acute symptoms to return to emergency room.


## 3808:  Acute Cystitis & Diabetes Type II

7 key facts.

### R3808-K01

The presenting symptom is abdominal pain.

> The patient is a 45-year-old male complaining of abdominal pain.

### R3808-K02

The assessment lists uncontrolled type 2 diabetes and acute cystitis.

> ASSESSMENT: , Diabetes type II uncontrolled.  Acute cystitis.

### R3808-K03

The history documents longstanding treated diabetes despite the generic no-significant-history line.

> The patient also has a long-standing history of diabetes which is treated with Micronase daily.,PAST MEDICAL HISTORY: , There is no significant past medical history noted today.

### R3808-K04

The GU checklist denies bladder disorder despite the later cystitis assessment; preserve the discrepancy rather than declaring no urinary condition.

> GU:  Patient has history of Urinary tract disorder, but does not have Bladder disorder and Kidney disorder.

### R3808-K05

Micronase is prescribed as 2.5 mg orally each morning, quantity 30; quantity does not establish treatment duration.

> Micronase 2.5 mg Tab PO QAM #30

### R3808-K06

Bactrim is listed as 400/80 orally twice daily, quantity 30; do not invent a course length or unstated dose unit.

> Bactrim 400/80 Tab PO BID #30

### R3808-K07

The plan is an endocrinology consultation and a complete CBC.

> Endocrinology Consult, complete CBC.


## 3606:  CT Abdomen & Pelvis - 3

13 key facts.

### R3606-K01

Noncontrast technique limits assessment of the solid abdominal organs.

> Noncontrast technique limits evaluation of the solid abdominal organs.

### R3606-K02

The abdominal wall hernia contains fat with stranding suggestive of incarcerated fat, not a confirmed bowel incarceration.

> Anterior abdominal wall hernia with mesenteric fat-containing stranding, suggestive of incarcerated fat.

### R3606-K03

The lung-base nodular density is 1.6 cm on the left.

> There is a 1.6 cm nodular density at the left posterior sulcus.

### R3606-K04

Follow-up of the left lower-lobe nodule is recommended in three months.

> Nodule in the left lower lobe, recommend follow up in 3 months.

### R3606-K05

The body calls an indeterminate 1.9 cm nodule left renal; retain this location as a source conflict with the impression's left adrenal wording.

> There is a left renal nodule seen, which measures 1.9 cm with a Hounsfield unit density of approximately 29, which is indeterminate.

### R3606-K06

The impression calls the indeterminate nodule left adrenal and suggests dedicated adrenal CT or MRI; do not silently resolve the renal/adrenal conflict.

> Indeterminate left adrenal nodule, could be further assessed with dedicated adrenal protocol CT or MRI.

### R3606-K07

The liver is enlarged with changes suggestive of cirrhosis, not a confirmed diagnosis.

> Hepatomegaly with changes suggestive of cirrhosis.

### R3606-K08

The spleen is enlarged.

> There is also splenomegaly observed.

### R3606-K09

Splenic lesions are incompletely characterized and may be cysts.

> Low-attenuation lesions in the spleen may represent cyst, that are incompletely characterized on this examination.

### R3606-K10

An 8-mm left-kidney fat-density lesion is compatible in appearance with angiomyolipoma.

> There is an 8-mm fat density lesion in the anterior inner polar region of the left kidney, compatible in appearance with angiomyolipoma.

### R3606-K11

A 1-cm right-kidney lesion is likely a cyst but is incompletely characterized.

> There is a 1-cm low-attenuation lesion in the upper pole of the right kidney, likely representing a cyst, but incompletely characterized on this examination.

### R3606-K12

The right-adnexal lesion may represent an ovary or a dermoid cyst; neither is certain.

> Fat density soft tissue lesion in the region of the right adnexa, this contains calcifications and may represent an ovary or possibly dermoid cyst.

### R3606-K13

Right-hip degenerative changes suggest possible avascular necrosis.

> There are extensive degenerative changes of the right hip noted with changes suggestive of avascular necrosis.


## 2964:  Carotid Ultrasound

4 key facts.

### R2964-K01

There is plaque on both sides, greater on the left.

> The study demonstrates bilateral hard plaque at the bifurcation, left greater than right.

### R2964-K02

The right internal carotid has plaque without evidence of greater than 50% narrowing; do not call it plaque-free.

> The right internal carotid artery at the bifurcation demonstrates plaque formation, but no evidence of greater than 50% stenosis.

### R2964-K03

The impression reports at least 50% left internal carotid narrowing, not an exact 50% measurement.

> There is at least 50% stenosis of the left internal carotid artery at its bifurcation

### R2964-K04

A follow-up CTA is recommended; it has not already been performed in this report.

> a followup CTA is recommended for further assessment.
