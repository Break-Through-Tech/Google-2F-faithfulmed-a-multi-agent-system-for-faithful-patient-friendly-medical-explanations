# ADK Web demo run record — October 21, 2026

## Team integration check — October 23, 2026

This file also retains the October 21 results below as a historical record of
Rafi's earlier local demo. After merging the teammate PRs, the integration
branch keeps Carlin's Intake/QuoteCheck, Zurabi's strict Refiner, and Alicia's
readability wrapper. The active demo displays seven stages.

- The full local suite passed: **51 tests**, including the new adapter checks
  and Zurabi's own Refiner tests.
- `/offline-error` completed through the seven-stage workflow and the local
  ADK Web streaming endpoint. Its false pneumonia sentence was removed and
  the changed draft was checked again. The Web run returned `complete` with
  FK grade 2.16.
- An omission and a non-quoted replacement now require review; they do not
  produce a released `final_answer`.
- A new live `/demo` attempt reached the Extractor but stopped with
  `ClientConnectorError` before generation. The execution environment could
  not complete that remote Gemini call, so this integrated revision has **not
  yet been confirmed by a new live end-to-end run**. The older live results
  below belong to the earlier checkpoint and must not be represented as a
  result of the combined code.

Implementation and local checks performed by Rafi with Codex assistance.
These are synthetic smoke checks, not clinical evaluation results.

## Environment and input

- Windows, Python 3.12, ADK 2.9.2; dependency versions are in `requirements.txt` here.
- Server: `adk web --host 127.0.0.1 --port 8000 .`, launched from the repository root.
- Agent selected by the server: `faithfulmed_demo` (root name `FaithfulMed`).
- Live generation model: `gemini-3.8-flash`.
- Retrieval: local `faithfulmed_medlineplus_gemini_embedding_2_768_v1` Chroma collection,
  using matching Gemini query embeddings and top-k 3.
- Input: the unchanged `clinical_text` from
  [`synthetic_chest_pain.json`](../baseline/examples/synthetic_chest_pain.json).

## Observed results

| Check | Observed result |
| --- | --- |
| Web UI and discovery | HTTP 200; `/list-apps` includes `faithfulmed_demo`. |
| Scripted `/offline-error` through Web | All five stage authors present; the intentionally invented pneumonia sentence was flagged and removed in one repair; original draft and initial verdict retained. Grade 2.16 on the corrected fixture. |
| Live `/demo` through Web `/run_sse` | Completed all five stages; 11 source-linked atoms, 3 retrieved passages, live Gemini draft and judgment, no repair requested in this run. Final FK grade 6.58; grade-8 check passed. |
| Separate live Verifier probes | Supported fixture draft returned no findings; pneumonia addition was flagged; changing “tests did not show a heart attack” into “you did not have a heart attack” was flagged. |
| Automated tests | `python -m unittest discover -s tests -v`: 34 passed, including 8 new demo checks. |

The live Extractor also emits events as `ClinicalExtractor` inside the top-level
Extractor stage. This extra author is the reused child agent, not a sixth pipeline stage.

The first exploratory live run overstated the negative test result and the Verifier
missed it. Both prompts were revised to preserve evidence strength. The subsequent
streamed run preserved the source wording, and the explicit overstated-claim probe
was detected. This demonstrates why a successful run must not be treated as proof
of clinical accuracy or Verifier calibration.

## Saved local evidence

Generated records are ignored by Git:

- `data/adk_demo_results/web_offline.json`: scripted Web run and full state.
- `data/adk_demo_results/web_live.json`: final live streaming run and full state.
- `data/adk_demo_results/verifier_cases.json`: three live judgment probes.
- `data/adk_demo_results/web.stdout.log` and `web.stderr.log`: local server logs.

Use the commands in [README.md](README.md) to repeat the walkthrough. The automated
tests cover stage order, source preservation, exact edits, no-op refinement, clearing
state between turns, stopping on invalid/empty extraction, and the two-repair cap.

## Remaining work

- Have Rafi personally open the UI and repeat the walkthrough, then have a teammate
  reproduce it. The checks above exercised the actual HTTP/SSE server; they do not
  claim a human has already completed that walkthrough.
- Review these new modules with their original owners before merging.
- Calibrate the Verifier, assess omissions and retrieval quality, and evaluate on
  reviewed examples. One live retrieval result was Spanish; language filtering and
  multilingual quality are not established by this demo.
- A readability failure is reported without rewriting. If a rewrite stage is added,
  its changed answer must be checked again for faithfulness.
- The installed ADK still supports `SequentialAgent` but emits a deprecation warning.
  This demo pins the tested version; migration to its newer Workflow API is separate work.
