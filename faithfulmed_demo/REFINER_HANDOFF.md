# Zurabi's Refiner contribution

This implements the small Refiner slice in the October 15 team plan: change
flagged text only, preserve a clean draft exactly, and return `revised_draft`.
The baseline remains a separate comparison path. This is a deterministic
helper, not a Gemini run, a clinical verifier, or a complete five-agent demo.

## Run the synthetic example and checks

From the repository root, with Python 3.10 or later:

```sh
python -m faithfulmed_demo.refiner_demo
python -m unittest discover -s tests -p 'test_refiner.py' -v
```

No additional packages, API key, network, or MedlinePlus index are needed.
The example uses a synthetic pending stress-test result, consistent with
`baseline/examples/synthetic_chest_pain.json`. It replaces only the unsupported
sentence `Your stress test result was normal.` with the source's pending-result
sentence. The surrounding sentences and newlines stay identical. A second,
clean verdict preserves the corrected input exactly. Both verdicts are supplied
fixtures; these checks do not measure Verifier accuracy or medical quality.

Observed on October 21, 2026: all 14 offline tests passed, and both preservation
checks in the demo returned `true`. The actual demo output is saved in
`examples/refiner_smoke.json`. No live Gemini call or ADK Web run was performed
for this helper contribution.

## Integration for Carlin, Rafi, and Alicia

```python
from faithfulmed_demo.roles.refiner import refine_state

# state contains the shared draft, verdict, and unchanged source_report.
delta = refine_state(state)
# delta is {"revised_draft": "..."}.
```

Carlin's ADK wrapper should publish `delta` as an event's `state_delta`, then
pass `revised_draft` to Alicia and the next Verifier check. The helper does not
mutate session state or instantiate a model. It is intentionally usable without
ADK installed. Do not overwrite the original `source_report`. No orchestration
entry point is added here: the team-owned `agent.py` must wire this helper in.

Rafi's adapter must return the following proposed verdict shape as a mapping
or a JSON object string. This is a new explicit handoff contract, not a claim
that the current notebook scaffold already emits it:

```json
{
  "faithful": false,
  "findings": [{
    "category": "unsupported",
    "start": 0,
    "end": 21,
    "original": "The result is normal.",
    "replacement": "The result is pending.",
    "source_quote": "The result is pending.",
    "reason": "The original note says the result is pending."
  }]
}
```

For this example, `draft` is `The result is normal.` and `source_report`
contains `The result is pending.`. `start` is inclusive and `end` exclusive;
offsets count Python Unicode characters, not bytes or JavaScript UTF-16 units.
The Verifier should select the whole flagged sentence, excluding surrounding
whitespace. Exact spans avoid splitting abbreviations and decimal doses.

- `faithful: true` with `findings: []` returns the input byte-for-byte when
  encoded with the same encoding. No whitespace normalization takes place.
- `unsupported` and `contradictory` findings can replace an exact draft span
  with an exact nonempty quote from `source_report`. This conservative first
  implementation does not paraphrase corrections.
- An empty `replacement` and empty `source_quote` delete only the selected
  span. Whitespace outside that span remains, even if deletion leaves an empty
  line. The Verifier must decide whether deletion would create an omission.
- All edits use offsets into the same original draft. They are validated
  together and applied from right to left, so an earlier edit cannot shift a
  later target. Duplicate or overlapping spans are rejected.
- Invalid JSON, unexpected fields, missing evidence, inconsistent verdicts,
  stale spans, and unsupported categories raise `ValueError`. The orchestrator
  must show a blocked correction, not mark the unchanged text as verified.

Exact quote matching checks provenance only. A quote can still be irrelevant
or lose context when moved. The Verifier remains responsible for relevance,
negation, uncertainty, numbers, and clinical faithfulness. Inputs are treated
as text data; the helper does not execute their contents.

Omissions are explicitly unsupported in this first slice. An omission finding
must stop automatic correction for review; it must not be silently dropped or
converted to a clean verdict. The scaffold's `unsupported_claims` / `omissions`
shape requires an explicit adapter. Future omission insertion and paraphrasing
need their own evidence contract and tests.

## Later bounded Verifier/Refiner loop

The orchestrator owns the counter. Use this sequence when integrating a real
Verifier; this PR documents the loop rather than claiming it is implemented:

1. Keep `source_report` fixed. Set `current = draft` and `rounds = 0`.
2. Verify `current` against the original source and obtain a fresh verdict.
3. If clean, pass `current` as `revised_draft` to Readability and stop refining.
4. If the verdict is unusable, has omissions this helper cannot repair, or
   `rounds == 2`, stop with an explicit unresolved/needs-review status.
5. Refine `current` using that verdict. Increment `rounds`, then go to step 2.

This permits at most two Refiner calls and three Verifier calls (initial plus
one after each correction). Always verify the second correction before deciding
whether it passed. Never reuse stale offsets or equate reaching the cap with
success. A later readability rewrite also needs a final faithfulness check;
it must not restart the correction counter. Pending human review and full
pipeline integration remain team work.
