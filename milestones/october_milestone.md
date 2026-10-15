# October Milestone 2: an ADK demo first, then real agent contributions

**Working team plan, updated October 15, 2026.** This plan changes the earlier `milestone2Planning.pdf` order. The first deadline is a **local ADK Web demo on Sunday night, October 18**. Each teammate must make a concrete, reviewable contribution **by Tuesday night, October 20 (before October 21)**. The names below follow our existing role assignments; confirm any changes together. Have a teammate review each PR before merging.

## What October as a whole is supposed to accomplish

These are the [project overview's](../Challenge-Project-Overview.md) October goals. The Sunday walkthrough is the first visible slice of this work, not proof that the whole table is finished.

| October work | Expected result by the end of the month |
| --- | --- |
| **Connect the five agents with Google ADK** | A runnable path from a clinical note through Extractor, Simplifier, Verifier, Refiner, and Readability to a final explanation. ADK Web should show the steps during development. |
| **Extract facts** | Extractor returns source-linked clinical facts (“atoms”) with useful types; it preserves negation, numbers, and uncertainty. |
| **Write a grounded explanation** | Simplifier uses those facts plus MedlinePlus passages to explain terms plainly without treating general health information as facts about this patient. The complete MiniLM/Chroma index can support retrieval while Gemini embeddings remain incomplete. |
| **Check and repair faithfulness** | Verifier flags unsupported additions, contradictions, and important omissions against the source note. Refiner changes only flagged content, and a bounded Verifier/Refiner loop stops after at most two rounds. Recheck any final readability rewrite. |
| **Measure quality** | Use Alicia's readability metrics and calibrate the Verifier against MedAESQA human accuracy/evidence labels; the overview targets at least 80% agreement and Cohen's kappa of at least 0.6. Source-note omissions need a separate human check. |
| **Make an initial comparison** | Eventually compare the multi-agent path with the single-Gemini baseline on the same reviewed examples, then attempt Gemini, Gemma, and one external-model comparison. Record missing runs and limits honestly. This is later October work, not part of the Sunday demo. |

**What already exists:** a design sketch in `notebooks/adk_pipeline.py`, two synthetic input examples in `baseline/examples/`, a runnable single-Gemini baseline, retrieval code and a complete MiniLM MedlinePlus index, Rafi's rubric foundation, and Alicia's reusable readability scorer. **What does not yet exist:** an ADK Web-loadable FaithfulMed package or five finished agent modules. The 50-report evaluation set is not reviewed/frozen, and Gemini embeddings are partial.

## Plan through October 20 only

### What the Sunday, October 18 demo must show

1. From the repo root, ADK Web starts and offers a `faithfulmed_demo` agent. ADK's required entry point is an agent package with `__init__.py`, `agent.py`, and a `root_agent` variable; a separate `.py` file per role is useful for team ownership but is **not required** to start the demo.
2. We enter one existing **synthetic, de-identified** clinical note. The UI shows five named stages in order and a final plain-language answer. Each stage either uses a small live implementation or is visibly labeled as a demo placeholder; no one mistakes a fixed response for Gemini output.
3. At least one Gemini text-generation step runs if the current key and quota allow. If quota blocks it, a labeled deterministic ADK run still demonstrates the orchestration, and the status note says the live call remains blocked.
4. We can point to the source note, extracted facts, the MedlinePlus context used (a short cited fixture is acceptable), the draft, Verifier finding, Refiner decision, and final text. This shows **data moving between steps**, not merely five agents with disconnected names.
5. Another teammate can follow the instructions and repeat the run. Save the exact example, command, observed result, and which stages were live or placeholders. A demo run is **not** a clinical-quality or evaluation result.

For this walkthrough, use one short MedlinePlus passage and URL as a fixture, or use the existing MiniLM collection if it is already available on the demo computer. Do not wait for full Gemini embeddings, extra MedlinePlus handoff work, or the 50-report review.

### Day-by-day handoff

| Day | Work and handoff | Completion check |
| --- | --- | --- |
| **Thu Oct 15** | **Rafi + Carlin** agree on a tiny state contract and pick a synthetic note. Carlin creates `faithfulmed_demo/` with `root_agent` and confirms ADK Web discovers it. | ADK loads the package; names of the fields and the sample note are written down. |
| **Fri Oct 16** | **Carlin** wires a first `SequentialAgent` pass. Start with two connected steps, then add simple versions/placeholders for the remaining named roles. **Rafi** supplies a Verifier example and checks that the original note reaches it. | A run passes values from one step to the next without missing-state or import errors. |
| **Sat Oct 17** | **Carlin + Rafi** do an end-to-end local rehearsal. Try the current Gemini generation model with one small call; add the cited MedlinePlus fixture and a labeled fixed-output fallback. Write concise startup instructions. | One full synthetic run finishes; the team can tell exactly which steps were live. |
| **Sun Oct 18** | **Rafi runs the ADK Web walkthrough himself** using the written steps; **Carlin** is available to fix demo-blocking errors. Rafi submits the note and explains the state handoffs and Verifier finding. | Rafi can start ADK Web, select the agent, run the synthetic note, and see the five named steps and final answer. Record the trace/result and open blockers. |
| **Mon Oct 19** | Owners deliver small real implementations for their roles; Carlin replaces demo placeholders one at a time. See individual action plans below. | Each owner has a reviewable file/change and a synthetic example or check. The demo still starts after each replacement. |
| **Tue Oct 20** | Finish remaining slices, run a shared smoke check, review PRs, and document what was integrated versus still pending. | All six people have a concrete contribution before Oct 21; no unreviewed PR is merged. |

The demo can run from a local branch before all PRs merge. Team review remains required **before merging**, as agreed with the coach.

### Shared contract: what moves between agents

| Field | Plain meaning | Producer -> consumer |
| --- | --- | --- |
| `source_report` | The original synthetic note, kept unchanged. | User -> Extractor and Verifier |
| `atoms` | Short, source-linked patient facts. | Extractor -> Simplifier and Verifier |
| `retrieved_context` | MedlinePlus text and URL used as general background. | Retrieval/fixture -> Simplifier |
| `draft` | First patient-friendly explanation. | Simplifier -> Verifier |
| `verdict` | Supported/unsupported/omitted findings with reasons. | Verifier -> Refiner |
| `revised_draft` | Targeted correction, or unchanged draft if no correction is needed. | Refiner -> Readability and later Verifier recheck |
| `final_answer` | Text shown to the user, with a clear demo status. | Readability -> UI |

Carlin can use ADK `output_key` and shared session state for this first pass. Keep each step's output small and predictable. On Sunday, one ordered pass is enough; add the bounded Verifier/Refiner loop after it works.

## Action plans for each teammate through October 20

These are **small first contributions**, not full-agent completion deadlines. For clean parallel work, the recommended later layout is `faithfulmed_demo/agent.py` for orchestration plus `faithfulmed_demo/roles/extractor.py`, `simplifier.py`, `verifier.py`, `refiner.py`, and `readability.py` for owner code. These role files are an organization choice, not an ADK requirement. Each must export an ADK-compatible agent or helper that `agent.py` can use.

### Carlin — ADK orchestration (needed before Sunday)

- **Thu–Sun action:** Create `faithfulmed_demo/__init__.py` and `agent.py` with `root_agent`. Wire five named steps in order, initially using small instructions or explicitly labeled placeholder agents. Make the output of one available to the next. Use the existing `notebooks/adk_pipeline.py` for the intended shape, but validate APIs/model names against the installed ADK version.
- **Setup action:** The ignored root `.env` currently has `GEMINI_API_KEY`; ADK's Gemini setup expects `GOOGLE_API_KEY`. Load the existing value and map it **in memory** without displaying or committing it. Test a current text-generation model with one small synthetic call.
- **Mon–Tue action:** Import each owner's first module, replace placeholders as they arrive, and keep the Sunday smoke test runnable.
- **Handoff/check:** Rafi can follow Carlin's instructions without editing code, run ADK Web, submit the sample note, and see all named stages plus the final response.

### Rafi — contract, demo test, Verifier (needed before Sunday)

- **Thu–Sun action:** Define the seven shared fields above with Carlin; choose a synthetic input and write one intentionally unsupported draft claim to show what a Verifier finding looks like. Check that the Verifier has both the original source note and the draft. Help rehearse the Web run.
- **Mon–Tue action:** Put a small Verifier implementation or prompt in `roles/verifier.py` that returns a source-tied reason for a supported claim, unsupported addition, or omission. Reuse the categories in `EDAs/MedAESQA/verifier_rubric.py` where appropriate, but do not claim that deterministic rubric file already judges arbitrary generated text.
- **Handoff/check:** One faithful and one unsupported synthetic claim yield different, understandable verdicts that the Refiner can read.

### Vaibhavi — Extractor (Monday/Tuesday contribution; not a Sunday blocker)

- **Action:** Add `roles/extractor.py` with a small ADK agent or helper that turns a synthetic note into a few typed `atoms`. Include a short pointer to the original wording for each atom. Preserve at least one negation and any number or dosage used in the example.
- **Handoff:** Carlin substitutes this for the demo Extractor placeholder. Ruhma and Rafi then receive its `atoms`.
- **Check by Oct 20:** Show the input and resulting atoms for one synthetic note; test that “no allergy” does not become “has allergy.” Existing `extractor/rag.py` is retrieval/vector-store code, not this clinical-fact agent.

### Ruhma — Simplifier and grounding (Monday/Tuesday contribution; not a Sunday blocker)

- **Action:** Add `roles/simplifier.py` with a small draft-writing agent/helper that receives `atoms` and `retrieved_context`. For the first slice, use one cited MedlinePlus passage or call the already built MiniLM retrieval adapter. Explain terms plainly and separate general MedlinePlus facts from patient facts.
- **Handoff:** Return `draft` to Rafi's Verifier. Carlin replaces the Sunday placeholder when the input/output works.
- **Check by Oct 20:** Show one draft and its context URL; point out which statements came from the patient note versus background definitions. No new large EDA or Gemini embedding run is needed for this slice.

### Zurabi — Refiner (Monday/Tuesday contribution; not a Sunday blocker)

- **Action:** Add `roles/refiner.py` to read `draft` and `verdict`, change only a flagged sentence, and leave the rest alone. If nothing is flagged, return the draft unchanged. Write down how the later Verifier/Refiner loop will stop after at most two rounds.
- **Handoff:** Return `revised_draft` for Alicia's stage and for a future Verifier recheck. The first Sunday demo can use a simple placeholder decision.
- **Check by Oct 20:** On a synthetic example, one unsupported sentence is corrected without unrelated rewrites; a clean verdict causes no change. His existing baseline remains a separate, useful comparison path.

### Alicia — Readability (Monday/Tuesday contribution; not a Sunday blocker)

- **Action:** Add `roles/readability.py` or a small wrapper that accepts `revised_draft` and calls the existing `evaluation/readability.py` scorer. Return a grade-level result, pass/fail status, and the final text or a clear suggestion. If an LLM rewrites for clarity later, flag that text for a final faithfulness recheck.
- **Handoff:** Supply `final_answer` plus the score/status to Carlin's workflow and demo output.
- **Check by Oct 20:** Run the same synthetic explanation through the reusable scorer and show what passed or needs simplification.

## How to launch once Carlin's package exists

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\adk.exe web .
```

Open the local URL ADK prints (normally `http://127.0.0.1:8000`), select `faithfulmed_demo`, and submit the agreed synthetic note. This is the intended Sunday command; it cannot select our demo until that package is created. Keep the server local. [Google's ADK Python quickstart](https://adk.dev/get-started/python/) describes `root_agent`, API-key setup, and running `adk web` from the agent folder's parent directory.

## What waits until after this October 20 plan

- Review/freeze the proposed 50-report set and run the fair same-input baseline comparison.
- Further MedlinePlus handoff polishing and finishing the separate Gemini embedding index.
- Replace all placeholders with robust agents, use real retrieval consistently, add the bounded two-round loop and final faithfulness check, calibrate the Verifier against MedAESQA human labels, and evaluate on reviewed examples.
- Attempt the larger Gemini/Gemma/external-model comparison only after the main path and evaluation rules are stable.

After the October 18 walkthrough, update the board with the *actual* live stages, placeholders, and failures. After the October 20 contribution check, assign dates for the remaining October work. The Sunday demo proves the workflow can run; it does not prove the medical explanations are accurate.
