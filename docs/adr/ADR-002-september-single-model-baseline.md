# ADR-002: September single-model baseline

Status: Proposed (for team review)

## Context

Issue #5 and the September roadmap require a retrieval-grounded single-Gemini
comparison point before October's ADK multi-agent system. Rafi already supplies
`retrieval.retrieve_context`; the shared populated index is still a dependency.

## Decision proposed

Use the framework-neutral `baseline.run_baseline` function with an injected
Chroma collection and generator. Retrieve once, serialize the clinical input and
retrieved chunks as data, then call Gemini once. Preserve chunk provenance and
stable example/model/prompt identifiers in evaluation records. Return
`no_context` without generation when no usable chunks are returned. Propagate
service errors and reject incomplete model output.

## Consequences

The baseline can be tested offline without API keys, index downloads, or ADK.
It can later be called from ADK without replacing the existing retrieval adapter.
It neither creates collections nor selects an embedding model: ingestion and
query embeddings must match. The extra explicit model setting prevents a silent
change of benchmark model. Temperature 0 reduces variability but does not ensure
identical hosted responses or clinical faithfulness. Team review must confirm the
no-context policy before freezing the evaluation protocol.

See [baseline task specification](../../baseline/README.md) for contracts,
limitations, and the handoff example. This proposal does not adopt a new
orchestration framework or modify the October scaffold.
