# FaithfulMed presentation UI

A local Gradio page for the existing ADK pipeline. Paste a report or select a
frozen MTSamples example, then choose **Simplify report**. The page shows stage
progress, an explanation or clearly labeled review draft, source passages,
extracted facts, readability, and verification/repair details.

## Run on Rafi's computer

From the repository root in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m faithfulmed_ui.app
```

Open **http://127.0.0.1:7860** and leave the terminal running. Stop with Ctrl+C.
If the port is busy, use `--port 7861` and open that port instead.

## Setup on another computer

Use the existing Python 3.11+ virtual environment, or create one with
`python -m venv .venv`. From the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r faithfulmed_ui/requirements.txt
.\.venv\Scripts\python.exe -m nltk.downloader cmudict
.\.venv\Scripts\python.exe -m faithfulmed_ui.app
```

Live mode uses the same root `.env`, generation-model setting, and Gemini Chroma
index as [ADK Web](../faithfulmed_demo/README.md). See the
[index download instructions](../data_pipeline/GEMINI_MEDLINEPLUS.md). The key
stays in the local Python process and is never an input field in the page.
Restart the server after changing `.env`.

The example selector reads `data/curated_baseline/mtsamples_curated_50.csv`.
It verifies the source IDs against the freeze manifest and text hashes against
the review annotations. The CSV is local data; Git does not distribute it.
Without it, the synthetic example and pasted reports still work. The UI never
changes the frozen reports. Source caveats appear below the example selector.

## Presenting the demo

1. Select **Scripted repair walkthrough** for a repeatable, no-API example. It
   uses the fixed chest-pain report and demonstrates removal of an intentionally
   unsupported claim and a subsequent Verifier check.
2. Select **Live Gemini**, choose a report, and click **Simplify report** to run
   the real pipeline. Each click makes a fresh, isolated ADK session.
3. Follow the seven steps. **Sources & facts** shows the evidence; **Checks &
   repairs** shows the initial findings, remaining findings, and number of edits.
4. Explain the outcome: **Explanation ready** means this run's checks finished
   without unresolved findings. **Draft needs review** or **Draft needs simpler
   wording** preserves the draft and the reason. A stopped run has no final answer.

The scripted modes always use the fixed synthetic note and disable custom input.
They do not silently replace failed live calls. Live mode uses the focused demo
query only for the unchanged synthetic note; other reports use the full report
as the retrieval query after Carlin's runner alignment was merged in PR #28.
Both baseline and ADK now default to top-k 3, and the Simplifier uses temperature 0.
The UI inherits those shared settings rather than defining a separate pipeline.

Reading grade uses the existing grade-8 check. A completed run or a readable
answer does not establish clinical accuracy: the Verifier is still uncalibrated.
Trying a frozen report in this UI is exploratory, not a saved benchmark run.

In live mode, the final stage can try at most two readability rewrites after clinical
checks are clear. Each candidate goes through the Verifier again before acceptance.
**Checks & repairs** shows before/after grades and whether each rewrite was accepted;
the raw trace retains the candidate and recheck findings. Unresolved clinical findings
block rewriting, and failed or still-difficult drafts are not released as final answers.
Restart the UI server to load this updated workflow.

## Implementation and verification

- `app.py`: Gradio inputs, streaming output updates, and local launcher.
- `pipeline.py`: calls `faithfulmed_demo.agent.build_agent()` through ADK Runner;
  each request has a fresh agent and memory-only session that is removed afterward.
- `presentation.py`: displays existing state fields without changing scoring.
- `examples.py`: loads optional frozen examples and source caveats.
- `style.css`: local styles; no externally hosted fonts or assets.

The page queues one run at a time to limit overlapping Gemini requests. It
disables report controls during execution, clears prior results on each run,
and has a ten-minute timeout. A timed-out request may still finish an already
dispatched service call; its output is not released as a new final answer.
The server binds to localhost, does not create a public Gradio share link, and
does not save reports/results to disk. Credentials and Git files are blocked
from Gradio's file-serving routes. Public hosting/authentication is future work.

Run the offline checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_ui.py -v
```

These cover actual offline ADK execution, bounded repair/recheck, isolated
requests, failure/review display, and missing-data behavior. They do not make
Gemini calls. Gradio's [streaming outputs](https://www.gradio.app/guides/streaming-outputs)
and [Blocks API](https://www.gradio.app/docs/gradio/blocks) describe the interface
mechanisms used here.
