# FaithfulMed Documentation

This folder is the shared documentation home for the FaithfulMed team. It keeps architectural decisions, individual progress reflections, and reusable documentation templates in one predictable place.

## Folder guide

### `adr/`
Contains Architecture Decision Records (ADRs). Create an ADR for a meaningful technical or architectural decision that affects multiple teammates or the overall system. Examples include the vector database, retrieval strategy, agent communication design, verifier output schema, evaluation strategy, or model selection.

ADRs are not for small personal implementation details. If a decision affects the broader team or system, document it with an ADR so future work has clear context.

### `reflections/`
Contains individual progress reflections. Each teammate is responsible for writing their own reflection, using the provided template and an individual file.

- **September 2026:** Each of the 5 team members creates exactly one monthly reflection covering their work for the entire month. Do not create weekly September files.
- **October 2026 onward:** Each team member creates one reflection every week. Use a consistent `YYYY-MM-DD-name.md` filename, such as `2026-10-05-name.md`, and organize files by month when practical (`october/`, `november/`, and so on).

Reflections should cover work completed, learning, results or findings, blockers, decisions contributed to, and next steps.

### `templates/`
Contains reusable templates for ADRs and reflections. Copy the appropriate template instead of starting documentation from scratch.

## Team responsibilities

Every team member should:

- Keep their own reflections up to date.
- Use the provided templates.
- Use clear filenames following the naming conventions.
- Create documentation on their own branch.
- Open a PR instead of editing shared documentation directly on `main`.
- Review relevant ADRs when a decision affects their work.
- Keep documentation factual and tied to work that was actually completed.
- Avoid duplicating the same information across multiple files unnecessarily.

## Contribution workflow

1. Create or switch to your own branch.
2. Copy the appropriate template from `templates/`.
3. Rename the copy using the naming convention.
4. Fill it in with specific, factual information.
5. Commit the file.
6. Push the branch.
7. Open a PR.
8. Have at least one teammate review team-wide changes, especially ADRs.

Use individual reflection files so teammates do not edit the same file and create avoidable merge conflicts. ADRs should receive team review because they record decisions that may shape other people's work.

## Naming at a glance

- September monthly reflection: `reflections/september/2026-09-name.md`
- Weekly reflection from October onward: `reflections/october/YYYY-MM-DD-name.md`
- ADR: `adr/ADR-001-short-title.md`

The example ADR in `adr/ADR-001-example.md` is a format sample only. It is not a real FaithfulMed decision.
