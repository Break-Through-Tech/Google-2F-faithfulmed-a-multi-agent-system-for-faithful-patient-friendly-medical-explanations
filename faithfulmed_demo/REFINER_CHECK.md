# Refiner behavior checks

I ran these checks on November 4, 2026 against main commit `4a51216`, using
Python 3.11.11 and the versions in `faithfulmed_demo/requirements.txt`. They
cover my four Refiner checks from the October 27 team plan.

I used the seven-stage ADK workflow with the existing adapter, Refiner helper,
repair loop, and readability scorer. The drafts and Verifier responses are
scripted examples, so this checks how the workflow handles edits and review
status. It doesn't measure Verifier accuracy or results on the frozen 50
reports. The checks don't call Gemini or run vector search.

## Run the checks

From the repository root (macOS/Linux; Windows users can substitute
`.venv\Scripts\python.exe` for `.venv/bin/python`):

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r faithfulmed_demo/requirements.txt
.venv/bin/python -m nltk.downloader cmudict
.venv/bin/python -m faithfulmed_demo.refiner_check --output faithfulmed_demo/examples/refiner_check_results.json
.venv/bin/python -m unittest discover -s tests -p 'test_refiner.py' -v
.venv/bin/python -m unittest discover -s tests -p 'test_adk_demo.py' -v
```

The first install and CMU dictionary download require network access. The
checks run locally after setup; no API key or MedlinePlus database is needed.
If the default NLTK directory is not writable, download with
`-d /your/writable/nltk_data` and set `NLTK_DATA` to that directory before running
the commands. The check command exits nonzero on a failed expectation and writes
the JSON only after all cases pass. Run without `--output` for a read-only check.

## Results

All rows are produced by the `refiner_check` command above. The case IDs identify
the corresponding records in [the saved JSON](examples/refiner_check_results.json).

| Behavior | Case and concrete example | Observed result |
| --- | --- | --- |
| Clean verdict preserves text | `clean`: existing synthetic chest-pain draft plus two newlines and two trailing spaces; empty issues list | **PASS** — original and revised strings identical, including whitespace; zero adapter calls/repairs; one Verifier call; released answer unchanged; `complete`. |
| Delete one exact unsupported span, then recheck | `deletion`: append `You have pneumonia.` to the chest-pain draft, then flag that unique span | **PASS** — only that sentence deleted; preceding space preserved; one repair, two Verifier calls; second call receives the revised text; clean final verdict and `complete`. |
| Apply a permitted exact-source replacement | `replacement`: append `Your stress test result was normal.` and replace it with `A nuclear stress test was done, but its result is still pending.` from the original source | **PASS** — exact source quote inserted; surrounding draft/newlines preserved; one repair, two Verifier calls; clean final verdict and `complete`. |
| Block omission/ambiguous edits for review | `omission`: request insertion of the pending-test fact; `ambiguous`: flag `You have pneumonia.` when it occurs twice | **PASS** — both blocked before any repair; draft unchanged; explicit blocker saved; one Verifier call each; `needs_review` and empty `final_answer` despite readability being scored. |

## Two-round cap and trace checks

I also checked what happens at the two-round limit. These examples flag one
span at a time so both runs need two repairs. The placeholder text is just
there to test the loop.

- `cap_unresolved`: initial draft contains `Unsupported first.`,
  `Unsupported second.`, and `Unsupported third.`. The first two spans are
  deleted in separate rounds. After the second repair, the Verifier flags the
  third. **PASS:** exactly two adapter calls/repairs and three Verifier calls;
  third finding retained in `final_verdict`; remaining draft retained for review;
  `needs_review`; `final_answer` empty. Reaching the cap does not release text.
- `cap_clean`: two spans require two separate repairs, and the final recheck is
  clean. **PASS:** exactly two adapter calls/repairs and three Verifier calls;
  `complete`; answer equals the final revised draft. The second repair is
  rechecked before release.

Every case checks that `source_report`, original `draft`, and initial `verdict`
remain available. Every history entry records its round, revised draft, and
recheck verdict; the runner checks these against the exact text and verdict
observed by the scripted Verifier. The JSON includes those records, adapter
attempt counts, final status/answer, blockers, readability scores, dependency
versions, and all seven stage names. It contains synthetic inputs only.

The check command returned:

```text
PASS clean: 0 repairs, 1 verifier calls, complete
PASS deletion: 1 repairs, 2 verifier calls, complete
PASS replacement: 1 repairs, 2 verifier calls, complete
PASS omission: 0 repairs, 1 verifier calls, needs_review
PASS ambiguous: 0 repairs, 1 verifier calls, needs_review
PASS cap_unresolved: 2 repairs, 3 verifier calls, needs_review
PASS cap_clean: 2 repairs, 3 verifier calls, complete
All 7 checks passed.
```

The existing helper suite passed **14 tests**, and the ADK adapter and workflow
suite passed **11 tests**. I didn't find a Refiner bug in these cases, so I left
the repair rules and orchestration as they were.
