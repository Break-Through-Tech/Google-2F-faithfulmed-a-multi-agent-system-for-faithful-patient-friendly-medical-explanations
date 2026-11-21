# ADR-005: Define citation support separately from report faithfulness

## Status

Proposed.

## Context

MedAESQA contains human judgments about answer accuracy and the relationship between answer sentences and cited documents. These are different questions. A sentence can contain several claims, and one cited paper may support only part of it. Requiring that paper to establish every claim can change the task being compared with the evidence-support labels.

The live report Verifier has a broader responsibility: identify unsupported patient claims, contradictions, and important omissions in a complete explanation.

## Decision

Evaluate one cited document against an answer sentence in its question context, using the supplied title and abstract. Apply contradiction priority: direct contradiction of a factual claim takes precedence over support for another claim. Absence of evidence is not contradiction.

Otherwise, count citation support when the document establishes at least one complete, substantive, independently checkable claim. Shared topic words or a study aim without findings are insufficient. Preserve necessary qualifiers, populations, quantities, uncertainty, comparisons, timing, and treatment conditions. Record the supported assertion and its source quotation.

Keep whole-sentence coverage and complete-report judgments separate from this citation decision. The live report Verifier must still check every patient claim and important omission; one supported claim cannot approve an entire explanation.

Compare citation decisions with MedAESQA's existing evidence-support labels and report agreement, Cohen's kappa, case counts, failures, and evaluation scope. Do not present citation agreement as whole-system medical accuracy. A new study using human labels for live report outputs is an optional validation extension, not an added requirement of the overview's MedAESQA calibration item.

## Why

The MedAESQA paper distinguishes evidence relationships from answer accuracy. BioACE's citation-evaluation discussion provides a useful basis for assessing independently checkable claims with contradiction priority. Its prose and appendix differ on partial-support scope, so this is an explicit project policy to test, rather than a claim that the literature supplies one universal rule.

## Alternatives considered

- **Require support for every claim from each cited document:** measures complete sentence coverage and can penalize citations supporting one independent claim.
- **Accept any topical overlap:** too weak to establish a substantive claim.
- **Use the citation rule to approve whole reports:** could overlook unsupported patient details and omissions.

## Consequences

A supporting citation label does not establish support for every detail in a sentence. Explanations and reports must state what the score measures. The citation evaluator and live report Verifier share evidence-preservation principles while retaining different output contracts and responsibilities.

## References

- [MedAESQA paper](https://d-nb.info/1374626414/34)
- [BioACE citation evaluation](https://pmc.ncbi.nlm.nih.gov/articles/PMC13119346/)
- [Citation evaluator and evaluation record](../../evaluation/CALIBRATION.md)
- [Live report Verifier](../../faithfulmed_demo/roles/verifier.py)
