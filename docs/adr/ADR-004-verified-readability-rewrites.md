# ADR-004: Verify readability rewrites before acceptance

## Status

Proposed.

## Context

An explanation can preserve medical facts while exceeding the grade-8 reading target. Shorter wording can also remove a necessary qualifier, change a medication detail, or omit a follow-up instruction. Readability scoring alone cannot judge whether a rewrite preserves meaning.

## Decision

Keep Alicia's local readability scorer separate from Gemini's wording rewrite. Start readability rewriting only when the current draft has no unresolved Verifier findings or repair blocker. Allow at most two rewrite attempts in the live workflow.

Provide the rewrite step with the current draft, original report, extracted facts, retrieved background, and reading target. Require preservation of patient facts, numbers, units, negation, uncertainty, pending results, conditional plans, follow-up, source conflicts, and background source links.

Run the Verifier on every rewritten candidate before accepting it, then score its readability. Accept only a candidate that clears the Verifier and improves the reading grade. Stop when the target is reached, a candidate introduces findings, improvement stops, or the attempt limit is reached.

Retain the previous accepted draft when a candidate is rejected. Save candidate text, recheck findings, before/after grades, and acceptance in `readability_history`. Release a final answer only when the retained draft passes both the existing clinical checks and readability rules. Otherwise return a review draft and its blocker or suggestion.

## Why

The system should improve wording without lowering its standard for preserving facts. Keeping candidate history also explains why a lower grade from a rejected rewrite does not become the displayed score for the retained draft.

## Alternatives considered

- **Score without rewriting:** simple, but leaves otherwise useful drafts above the target.
- **Accept any rewrite below grade 8:** can reward removal or distortion of difficult facts.
- **Rewrite without an attempt limit:** creates unpredictable latency and cost.

## Consequences

Readability improvement adds generation and verification calls. A draft may remain above target or require review. Reading grade is a wording measure; passing it does not establish clinical accuracy. Scripted walkthroughs remain deterministic and do not call Gemini for rewrites.

## Implementation

- [Readability helper](../../faithfulmed_demo/roles/readability.py)
- [Shared scorer](../../evaluation/readability.py)
- [ADK orchestration](../../faithfulmed_demo/agent.py)
