# Support and reference-conflict policy

Version: **support-conflict-2026-11-07-v1**. Prepared before additional service calls. This is a protocol and data audit, not a new calibrated judge or a replacement for saved results.

## What supported means

For clinical-output scoring, split independently checkable propositions. A supported patient claim must follow from the original report, preserving negation, uncertainty, numbers, units, laterality, timing, and conditional plans. An exact quote is an anchor, not proof that the interpretation is correct. General medical knowledge cannot fill a gap in patient evidence. Explicit general background may use the saved retrieved passages.

A sentence listing A, B, and C is not fully supported when evidence establishes only A. Record the supported and unsupported propositions separately. Do not mark the whole sentence supported just because its topic matches. Missing evidence is insufficient support, not necessarily a contradiction. Conflicting source statements must remain explicitly conflicting; do not silently choose one.

For MedAESQA, distinguish **citation/assertion support** from **complete sentence coverage**. Existing citation labels do not automatically provide a gold label for every proposition in a multi-claim sentence. A paper supporting one cited assertion may legitimately have a supporting citation label while leaving other assertions unaddressed. We must not change those labels into strict whole-sentence labels without separate annotation.

The next development prompt should return proposition-level coverage (supported, contradicted, or not established), exact evidence anchors, and a complete-coverage flag. Citation-reference agreement and complete-coverage diagnostics must be reported separately. The existing `supports_sentence` prompt/schema has NOT been changed by this policy. Its historical scores retain their original meaning.

## Evidence and identity

- Use the cited PubMed title and full abstract for document-reference comparisons. No silent fallback to a short highlighted snippet. Missing context means pending, not unsupported.
- Cache the PMID, title, abstract, retrieval date, and content hash. Current PubMed is not a verified recreation of the original dataset snapshot; disclose that limitation.
- Group references by question ID, numeric PMID, and assertion with numeric citation markers removed, case folded, and whitespace collapsed. Preserve punctuation, negation, decimals, units, and words.
- Also flag punctuation-insensitive neighboring groups for inspection; do not merge them automatically. This avoids merging different measurements merely because punctuation was removed.
- Collapse exact repeated document/assertion groups to one benchmark unit. Preserve every source record identifier and original relation in the audit.

## Conflict handling fixed before predictions

Map supporting to true and neutral, contradicting, and not relevant to false for a binary citation-support comparison. Inspect all matching records, including records without snippets: missing snippets do not erase document-level references. Invalid citations and unknown relations are separate validity/data problems.

If a group contains both true and false references, quarantine it from any newly constructed single-label benchmark. No majority vote, preferred answer-model label, or model-agreement tie-breaker. Retain it in a separate ambiguity set with all original labels. Groups mixing only false relations can retain false for binary agreement, but their relation disagreement remains visible. Groups containing invalid/unknown relations require resolution before benchmark inclusion.

This is prospective eligibility, not permission to improve the old six-case score by dropping errors. Keep the original 3/6 and 4/6 results intact. Report all selected cases, conflicts, duplicates, missing context, attempted cases, failures, and scored denominators. Any later reference correction needs a recorded rationale, original and revised labels, a new suite version, and rescoring of both methods under that version.

## Development and held-out boundary

Audit metadata/duplicate labels in both existing splits mechanically, using the same rules. Do not inspect held-out sentences semantically, create held-out predictions, or tune prompts on them. Preserve question-level separation. The audit does not select a replacement cohort or declare eligible cases semantically unambiguous.

Review partial coverage and assertion boundaries on development cases first. Freeze task definition, prompt/schema, evidence snapshots, eligibility rules, cohort IDs, and model/settings before held-out calls. If held-out examples are used to tune the method, retire them from independent testing. A new cohort must be versioned; do not silently resume v1 with a changed task.

Agreement >=80% and Cohen's kappa >=0.6 remain goals, not guaranteed results. Report confusion counts, class balance, raw denominators, and uncertainty. An undefined kappa is not zero or a pass. Citation-support agreement alone does not validate omissions, source conflicts, or the full live Verifier.

## Source-only pilot checklists

Use original frozen report text only. Include consequential findings, uncertainty, allergies, medication instructions, and follow-up; omit repetitive routine normal examinations. Preserve source conflicts instead of resolving them using outside knowledge. A medication taper is one linked schedule: partial or altered coverage must not earn full credit.

Every fact has a stable ID and a verbatim contiguous source anchor. Keep the same checklist for both systems, version and hash it, and rescore both if it changes. Missing facts and present-but-distorted facts are different. Extra valid facts in an answer are not penalized just because they are absent from this key-fact inventory.

The November 7 inventories were prepared from sources without opening generated answers during this task. Report 4998 had already been generated and discussed earlier, so this is not a prospectively blinded inventory for that historical pair. The other four reports have no pilot outputs recorded in this work. These inventories are operational evaluation checklists, not independently adjudicated clinical gold labels.

## Next gate before API calls

1. Use the [audit](SUPPORT_CONFLICT_AUDIT.md) to identify context gaps and ambiguous references.
2. Implement and locally test the proposition-coverage development prompt/schema; keep it separate from citation-label agreement.
3. Assemble a versioned development cohort with cached title/abstract evidence and explicit reference scope. Context retrieval may be needed; no such requests were made for this audit.
4. Run a bounded development check, inspect errors, then freeze settings before independent held-out evaluation.

The five report inventories can be used independently of finishing calibration, but all resulting judge scores remain provisional until validation supports their use.
