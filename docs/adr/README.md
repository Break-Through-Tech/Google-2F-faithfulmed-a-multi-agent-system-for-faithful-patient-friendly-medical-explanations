# Architecture Decision Records

An Architecture Decision Record (ADR) captures a meaningful technical or architectural decision, along with the context and tradeoffs that led to it. ADRs help the whole team understand why the system is shaped the way it is.

## When to write an ADR

Write an ADR when a decision affects multiple teammates, a shared interface, the overall system, or future architectural direction. Examples include:

- Choosing a vector database or retrieval strategy
- Defining agent communication or orchestration design
- Establishing the Verifier output schema
- Selecting an evaluation strategy
- Selecting or comparing models

When in doubt, write the decision down and ask for team review.

## When not to write one

Do not create an ADR for a small personal implementation detail, a local refactor with no shared impact, or a temporary experiment that does not influence the project direction. Record those details in the relevant code review or working notes instead.

## Naming and status

Use the format `ADR-001-short-title.md`, incrementing the number for each new ADR. Use lowercase hyphenated titles.

Recommended statuses are:

- **Proposed**: under discussion and not yet adopted
- **Accepted**: approved and currently in effect
- **Superseded**: replaced by a later ADR; link to the replacement

Copy `templates/adr-template.md` when creating a new ADR. `ADR-001-example.md` is a sample format only, not an actual project decision.
