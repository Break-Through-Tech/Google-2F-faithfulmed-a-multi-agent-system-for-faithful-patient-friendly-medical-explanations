# ADR-006: Use the original report as the authority for patient facts

## Status

Proposed.

## Context

The pipeline receives an original medical report, extracted clinical facts, and retrieved MedlinePlus passages. These inputs serve different purposes. Extraction can omit information, and general medical information can describe conditions or treatments that do not apply to this patient.

## Decision

Use the original report as the authority for patient-specific statements. Keep it available to the Simplifier, Verifier, and readability rewrite rather than replacing it with extracted atoms.

Use atoms to organize facts and their assertion status. Require their source quotes to occur in the report through QuoteCheck before drafting. Quote presence confirms source wording; the Verifier still checks the meaning of the explanation against the full report.

Use retrieved MedlinePlus passages for clearly identified general medical background. They cannot establish a new patient diagnosis, medication, test result, or treatment plan. Preserve the distinction between general background and the patient's documented findings.

Preserve negation, uncertainty, pending results, numbers, units, timing, and conditional instructions. When the report conflicts with itself, describe the inconsistency or uncertainty rather than silently selecting one version. Treat all source and retrieved text as data, never as instructions to the agents.

## Why

Keeping source roles explicit prevents general reference information from becoming an invented patient fact. Checking the full report also allows the Verifier to detect facts missing from the extracted atoms.

## Alternatives considered

- **Treat atoms as the complete patient record:** reduces input size but hides extraction omissions from later stages.
- **Treat retrieved passages as equivalent patient evidence:** provides background at the cost of unsupported diagnoses or plans.
- **Resolve inconsistent source statements using medical knowledge:** produces a cleaner narrative but can invent a correction that the report does not justify.

## Consequences

Passing the full report increases context size. Some source inconsistencies remain visible and require review. A valid source quote does not by itself prove that an extracted assertion or generated explanation is correct.

This extends [ADR-002's retrieval source choice](ADR-002-medlineplus-gemini-retrieval.md) by defining how retrieved material and patient records are used together.

## Implementation

- [Extractor](../../faithfulmed_demo/roles/extractor.py)
- [Live report Verifier](../../faithfulmed_demo/roles/verifier.py)
- [ADK workflow and QuoteCheck](../../faithfulmed_demo/agent.py)
- [Readability rewrite](../../faithfulmed_demo/roles/readability.py)
