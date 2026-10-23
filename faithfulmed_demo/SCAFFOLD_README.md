# FaithfulMed ADK demo
### Note that the Windows instructions are not tested yet!

How to run the FaithfulMed pipeline in your browser with Google's Agent
Development Kit (ADK). Each step has commands for Windows (PowerShell) and Mac
(Terminal). You don't need to edit any code.

## 1. What this is

The demo takes a patient note and passes it through seven steps in order:
Intake → Extractor → QuoteCheck → Simplifier → Verifier → Refiner →
Readability. Each step reads what the steps before it saved and adds its own
result. Today, three steps do real work:

- **Intake** saves your chat message as the note.
- **Extractor** pulls the clinical facts out of the note with a live Gemini call
  when you have an API key.
- **QuoteCheck** confirms that each fact's quote really appears in the note.

Simplifier, Verifier, Refiner and Readability are still **placeholders**. They
return fixed example text, start their messages with `[DEMO PLACEHOLDER: ...]`
and never call Gemini.

## 2. Get the code

These git commands are the same on Windows and Mac. If you haven't cloned the
repo yet:

```powershell
git clone https://github.com/Break-Through-Tech/Google-2F-faithfulmed-a-multi-agent-system-for-faithful-patient-friendly-medical-explanations.git
cd Google-2F-faithfulmed-a-multi-agent-system-for-faithful-patient-friendly-medical-explanations
```

Then switch to the demo branch:

```powershell
git fetch origin
git checkout carlin/adk-orchestration
git pull
```

## 3. Set up Python

You need Python 3.11 or newer, because ADK requires it. Check with
`python --version` on Windows or `python3 --version` on Mac.

From the repo root:

**Windows:**

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

**Mac:**

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

This installs ADK, the Gemini library and everything the demo uses. You don't
need to activate the virtual environment, because every command here calls
`.venv` directly.

## 4. Add your own key (only if you haven't already!)

Each teammate uses their own free key. Don't share keys.

1. Get a key from Google AI Studio: https://aistudio.google.com/apikey
2. In the repo root, create a file named `.env` and open it:

   **Windows:**

   ```powershell
   notepad .env
   ```

   **Mac** (Finder hides files whose names start with a dot, so use Terminal):

   ```bash
   touch .env
   open -e .env
   ```

3. Add this one line, using your key, then save:

   ```
   GEMINI_API_KEY=your-key-here
   ```

The demo copies `GEMINI_API_KEY` to `GOOGLE_API_KEY` for ADK and never prints
it. `.env` is already in `.gitignore`. **Never commit it.**

No key? The demo still runs. The Extractor just becomes a placeholder too, and
its message says `live call skipped: no API key`.

## 5. Run it

From the repo root (the folder that contains `faithfulmed_demo`):

**Windows:**

```powershell
.\.venv\Scripts\adk.exe web .
```

**Mac:**

```bash
.venv/bin/adk web .
```

Open the address it prints, usually http://127.0.0.1:8000. Pick
**faithfulmed_demo** from the agent dropdown in the top left.

Press `Ctrl+C` in the terminal to stop the server.

## 6. Try it

Paste this note into the chat box and send it. It's a made-up example from
`baseline/examples/synthetic_chest_pain.json`.

```
A patient came to the hospital with chest pain. Serial troponin tests did not show a heart attack. A nuclear stress test was done, but its result is still pending. Liver enzyme levels were elevated, and the cause is uncertain. The patient also has acid reflux. The patient will see a cardiologist in two weeks and a primary care doctor in two to four weeks. Discharge medications will depend on the stress-test result.
```

## 7. What you should see

One message per step, in this order:

| Step | Message |
| --- | --- |
| Intake | `Read the chat message. Wrote source_report (418 characters).` |
| Extractor | A JSON list of facts, each with `text`, `type`, `assertion` and `source_quote`. With no key, you'll see the `live call skipped` placeholder instead. |
| QuoteCheck | `All N quotes found in the source.` N is usually about 10 with a key, or 2 without one. |
| Simplifier | `Read atoms. Wrote retrieved_context, draft.` |
| Verifier | `Read source_report, atoms, draft. Wrote verdict.` |
| Refiner | `Read draft, verdict. Wrote revised_draft.` |
| Readability | `Read revised_draft. Wrote final_answer.`, followed by the final answer |

Intake's message also starts with `[DEMO PLACEHOLDER: Intake]`, even though it
really saves your note. With a key, you may also see an `ExtractorGate` step
next to the Extractor. That gate skips the Extractor if there is no note.

The **State** tab should list `source_report`, `atoms`, `retrieved_context`,
`draft`, `verdict`, `revised_draft` and `final_answer`.

Only `source_report` and `atoms` come from your note. The draft, verdict and
final answer are **fixed placeholder text**, so they stay the same whatever you
paste.

## 8. Troubleshooting

**faithfulmed_demo isn't in the dropdown.** You started `adk web` from the
wrong folder. Stop it, `cd` to the repo root (the folder that contains
`faithfulmed_demo`) and run it again.

**Messages say "Missing state field(s)".** The chat message was empty, so
nothing was saved for the later steps. Send the note again.

**QuoteCheck says "Quote check failed".** One of the Extractor's quotes isn't
word for word in the note. The rest of the run still finishes. Send the
message again. If it keeps failing, share the failing quote with the team.

**A Gemini error or a quota limit (for example `429 RESOURCE_EXHAUSTED`).**
The free tier has usage limits. Wait a few minutes and try again. To keep
working without Gemini, rename `.env` to `.env.off` and restart `adk web`. The
key is only checked when the server starts. If you also set `GOOGLE_API_KEY`
in your Windows environment variables or your Mac shell profile (such as
`~/.zshrc`), the demo uses that key instead of `.env`.

## 9. What's next (mostly for Carlin)

- A Verifier ↔ Refiner loop that repeats at most twice, in place of a single
  pass.
- A fallback for when Gemini fails or hits its limit.
- Real Simplifier, Verifier, Refiner and Readability agents in place of the
  placeholders. The Simplifier first needs to be turned into an ADK agent like
  `roles/extractor.py`.
