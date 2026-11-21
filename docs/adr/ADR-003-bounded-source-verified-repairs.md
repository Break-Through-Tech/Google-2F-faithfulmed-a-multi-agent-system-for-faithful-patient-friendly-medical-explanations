# ADR-003: Bounded source-verified repairs

## Status

Proposed.

## Context

The Verifier returns unsupported claims, contradictions, and omissions. Giving another model permission to rewrite the entire explanation could change correct passages or introduce new claims. Zurabi's Refiner already provides a strict edit contract; the ADK workflow needs to preserve that contract while handling findings it cannot repair automatically.

## Decision

Use the Python Refiner for targeted clinical repairs. Each finding must identify one exact, unique draft span. Permit deletion or replacement with an exact quote from the original report. Reject overlapping edits and invalid replacements before applying them. Do not release an empty explanation.

Use an adapter to translate the live Verifier's findings into the existing Refiner contract. Send omissions, ambiguous spans, and corrections requiring new wording to review instead of attempting an automatic insertion or unrestricted rewrite.

Allow at most two repair rounds. Run the Verifier again after every applied repair. Keep the revised draft, each recheck, and any repair blocker in shared state. Unresolved findings or a blocked repair prevent final-answer release.

## Why

Small, inspectable edits preserve correct content and keep the repair behavior predictable. A bounded loop controls model calls and prevents repeated revisions from running indefinitely. Rechecking ensures an edit is not accepted solely because Python could apply it.

## Alternatives considered

- **Ask Gemini to rewrite the whole explanation:** more flexible, but can change facts outside the flagged passage.
- **Apply edits without rechecking:** faster, but successful text replacement does not establish that the result is faithful.
- **Keep repairing until all findings disappear:** has unpredictable cost and may never converge.

## Consequences

Some legitimate corrections require review because exact source wording is too restrictive. Source quotes may also be difficult to read; readability is handled separately. A clean recheck is a workflow decision, not a guarantee of clinical correctness.

## Implementation

- [Refiner adapter](../../faithfulmed_demo/refiner_adapter.py)
- [Refiner](../../faithfulmed_demo/roles/refiner.py)
- [ADK orchestration](../../faithfulmed_demo/agent.py)
