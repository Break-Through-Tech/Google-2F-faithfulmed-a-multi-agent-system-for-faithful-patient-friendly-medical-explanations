# Run the FaithfulMed ADK Web demo

This package builds on Carlin's ADK scaffold and connects seven visible steps:
**Intake → Extractor → QuoteCheck → Simplifier → Verifier → Refiner → Readability**.
It is an initial development demo, not a calibrated clinical system or a benchmark result.
Carlin's original runnable scaffold and setup guide are preserved as
[`scaffold_agent.py`](scaffold_agent.py) and [`SCAFFOLD_README.md`](SCAFFOLD_README.md).
The active `agent.py` adds live roles to that flow; the scaffold files record her
original contribution and can be inspected separately.

## Start on Rafi's computer

From the repository root in VS Code's PowerShell terminal:

```powershell
.\.venv\Scripts\adk.exe web --host 127.0.0.1 --port 8000 .
```

Leave that terminal running. Open **http://127.0.0.1:8000**, select
**faithfulmed_demo**, and enter one of these messages:

| Message | What happens |
| --- | --- |
| `/offline-error` | A scripted synthetic chest-pain example includes the deliberately false claim “You have pneumonia.” The fixture Verifier flags it; the Refiner removes only that sentence and rechecks it. No Gemini calls or vector search. |
| `/offline` | The same scripted example without the false claim. The Refiner leaves the draft unchanged. |
| `/demo` | The existing synthetic chest-pain note runs through the real Extractor, Gemini/Chroma retrieval, Gemini Simplifier and Verifier, targeted repairs if needed, and local readability scoring. |
| Paste a synthetic note | The live path uses that note. Each new message starts a fresh note and clears the previous run's state. |

Start with `/offline-error` to learn the UI, then `/demo` to see the live path.
The chat events identify each stage. Inspect event/state details to see
`source_report`, `atoms`, `retrieved_context`, `draft`, `verdict`,
`revised_draft`, and `final_answer`. `final_verdict`, `refinement_history`,
`readability`, `stage_modes`, and `run_status` provide additional trace information.
The original `verdict` is retained so you can compare it with the recheck.

Stop the server with **Ctrl+C** in its terminal. No website, cloud deployment,
or public hosting account is needed. ADK Web is a local development interface.
If port 8000 is busy, use `--port 8001` and open that port instead.

## First setup on another computer

Use Python 3.11 or later and a virtual environment. Install the tested dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r faithfulmed_demo/requirements.txt
.\.venv\Scripts\python.exe -m nltk.downloader cmudict
```

Offline mode needs no API key or database. Live mode also needs:

1. `GEMINI_API_KEY=...` in the ignored repository-root `.env`. The demo maps it to
   `GOOGLE_API_KEY` in memory for ADK. Do not paste keys into the chat UI.
2. The completed local database described in [the Gemini index setup](../data_pipeline/GEMINI_MEDLINEPLUS.md).
   Download the existing snapshot; do not rebuild document embeddings for this demo.
3. Access and quota for the configured generation model and query-embedding model.
   The generation default follows the existing baseline: `gemini-3.8-flash`.
   To choose a different accessible generation model, set `FAITHFULMED_MODEL` in
   `.env` and restart ADK Web. This does not change the embedding model.

Live errors stop the run and appear in the stage trace. The demo never silently
substitutes scripted output for a failed model call. Run `/offline-error` explicitly
if you want the no-API walkthrough instead.

## What each stage does

- **Intake:** records the source note after resolving `/demo` to the fixed synthetic note.
- **Extractor:** uses Vaibhavi's ADK agent. Scripted mode uses fixed atoms for the supplied example only.
- **QuoteCheck:** applies the source-quote validation from Carlin's scaffold.
  A failed quote stops the workflow before drafting.
- **Simplifier:** uses Ruhma's function with the original note, extracted facts, and
  up to three real MedlinePlus chunks. Scripted mode uses one checked-in cited passage.
- **Verifier:** compares the draft with the original note, atoms, and background.
  Its structured findings distinguish unsupported claims, contradictions, and omissions.
  The live judgment is not calibrated. The offline check recognizes only the intentional
  demonstration error; it cannot judge arbitrary medical text.
- **Refiner:** uses Zurabi's `run_refiner` through an adapter. Only an exact
  source-quote replacement or deletion of one unambiguous draft span is applied.
  Omissions, paraphrased replacements, and ambiguous spans are marked for review.
  Every applied repair is rechecked; at most two rounds are allowed.
- **Readability:** uses Alicia's `run_readability` wrapper around her scorer.
  A passing, resolved draft becomes `final_answer`. A failing grade gets a
  suggestion; an unresolved Verifier finding leaves `final_answer` empty and
  shows the draft for review. This stage does not rewrite medical text.

`complete` means the demo finished without unresolved findings from its own check;
it is not a clinical faithfulness certificate. Readability can still fail separately.
The 50-report evaluation, human calibration, and model comparison remain later work.

## Reproduce a run outside the browser

These commands use the same root agent and save JSON traces under ignored `data/`:

```powershell
.\.venv\Scripts\python.exe -m faithfulmed_demo.smoke --message /offline-error --output data/adk_demo_results/offline.json
.\.venv\Scripts\python.exe -m faithfulmed_demo.smoke --message /demo --output data/adk_demo_results/live.json
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_adk_demo.py -v
```

To test the already-running Web server's streaming endpoint and save its trace:

```powershell
.\.venv\Scripts\python.exe -m faithfulmed_demo.web_smoke --sse --message /offline-error
```

See [the October 21 run record](RUN_RECORD.md) for measured results and limitations.

## Original ownership of this work

Rafi implemented the integration and missing demo pieces in this working change,
using the existing teammate modules below. This table preserves the milestone ownership;
it does not attribute the new work to teammates who did not write it.

| Milestone owner | Responsibility covered by this demo |
| --- | --- |
| Carlin | Original seven-step ADK scaffold, Intake, QuoteCheck, shared-state flow, credential setup, and setup guide. These are preserved and built upon here. |
| Rafi | Shared contract, source-note preservation, Verifier example and implementation, live retrieval connection, and demo checks. |
| Vaibhavi | Existing Extractor reused; integration adds quote validation to the workflow. |
| Ruhma | Existing Simplifier reused; added model configuration, output checks, original-note context, and real retrieval handoff. |
| Zurabi | His merged strict Refiner is called by the new adapter; the integration adds bounded repair/recheck behavior. His baseline remains separate. |
| Alicia | Her merged `run_readability` wrapper and existing scorer are called by the final stage. |

Official references: [ADK Python/Web setup](https://adk.dev/get-started/python/),
[sequential workflows](https://adk.dev/agents/workflow-agents/sequential-agents/),
[custom agents and state events](https://adk.dev/agents/custom-agents/).
