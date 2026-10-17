# ADR-001: Single-Gemini retrieval baseline

## Status

Accepted by Rafi on 2026-10-16 for the current baseline design. Zurabi remains the baseline implementation owner. This acceptance does not freeze the evaluation set or scoring rules for a benchmark.

## Date

2026-10-02 (original proposal); revised into ADR format 2026-10-09; accepted by Rafi 2026-10-16.

## Decision owner

Zurabi Kochiashvili, baseline and Refiner owner. The revised format preserves the decision in Zurabi's original `ADR-002-september-single-model-baseline.md`.

## Context

The team needs a reproducible comparison point before testing the October multi-agent system. Issue #5 calls for a retrieval-grounded single-Gemini baseline on the curated source reports. The MedlinePlus index and Rafi's Chroma-compatible retrieval interface are separate handoffs, so the baseline must be testable before a shared real collection or API credentials are available. A baseline result also needs enough provenance to distinguish retrieval failures, model failures, and generated explanations during later evaluation.

## Decision

Use the framework-neutral `baseline.run_baseline` function with an injected Chroma-compatible collection and Gemini generator. For each clinical input, retrieve context once and make at most one Gemini generation call. Pass the clinical text and retrieved chunks to the generator as serialized data; preserve retrieved chunk IDs, text, metadata, and distances in the result. Record stable example, model, and prompt identifiers.

If retrieval returns no nonblank passage text, return `status="no_context"` without generating. This checks whether text is present, not whether the passage is medically relevant. Reject blocked, incomplete, or empty model output; let retrieval and service errors propagate for the caller to record separately. Do not add an agent loop, automatic prompt repair, or a second refinement call to this baseline.

Use an explicit Gemini model setting and deterministic control flow. The current generator requests temperature 0 and one candidate, while acknowledging that hosted responses may still vary. Query embeddings must be compatible with the stored vectors. This ADR does not choose the ingestion embedding model or replace the retrieval owner's collection contract.

## Why

One retrieval step and one generation step make the baseline simpler to reproduce and compare with the later multi-agent pipeline. Injected dependencies allow offline tests without credentials or a downloaded index. Recording exact context and configuration helps reviewers trace an answer back to what the model actually saw. A distinct `no_context` outcome prevents an ungrounded answer from being mistaken for a retrieval-grounded baseline result.

## Alternatives considered

- **Start with the October ADK multi-agent pipeline:** This would combine several agents before there is a single-model comparison point and make failures harder to attribute.
- **Generate even when retrieval finds no usable chunks:** This would produce an ungrounded answer under the same label as a grounded baseline result.
- **Hide model or retrieval defaults inside the baseline:** Silent model or embedding changes would undermine comparisons across runs. The baseline therefore records its settings and receives its collection from the caller.

## Consequences

The baseline can run an offline plumbing test and use the real MedlinePlus collection without changing its public function. It produces a technical completion status, not a clinical faithfulness verdict; Verifier and readability evaluation remain separate. Temperature 0 does not guarantee identical Gemini responses. Large context or service limits may still cause failures, which must be reported rather than silently converted to successful outputs. The `no_context` behavior is accepted for this baseline; how those cases count in final benchmark scores still needs agreement.

## Follow-up

1. **Done:** Connect the baseline to the complete 6,883-chunk Gemini MedlinePlus collection. Stored passages and search queries use `gemini-embedding-2`; the verified index ZIP and checksum are in the team Drive.
2. **Done as a smoke check:** Run two synthetic, de-identified notes through Gemini retrieval and one Gemini answer-generation call each. Their saved JSON records retrieved passages and source links. These runs do not measure clinical faithfulness or retrieval quality.
3. **Next:** Have teammates download and verify the shared index, and review retrieval results across different topics and languages before relying on them for the benchmark.
4. **Next:** Review and freeze the proposed 50-report set. Record its version alongside the index snapshot, Gemini generation model, prompt version, SDK version, retrieval settings, and how `no_context` and failed runs will count in evaluation.
5. **Next:** Run the frozen reports through this baseline and the later agent pipeline, then compare their outputs using the same faithfulness and readability measures.

See the [baseline task specification](../../baseline/README.md) for the current input/output contract and handoff example.
