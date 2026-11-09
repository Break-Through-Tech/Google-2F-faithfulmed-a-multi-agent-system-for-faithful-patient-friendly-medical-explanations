# Presentation UI checks — November 4, 2026

Tested locally on Windows with Gradio 6.28.0 and a headless Microsoft Edge browser.

| Check | Observed result |
| --- | --- |
| Frozen example loader | 50 MTSamples reports available plus the synthetic example; IDs and report hashes checked. |
| Browser example selection | Selecting MTSamples source row 0 loaded its actual report into the input box. |
| Scripted repair walkthrough | All seven stages finished; one targeted repair/recheck removed the intentionally unsupported pneumonia claim. |
| Changing modes | Previous results cleared; scripted input locked to the fixed report; live input became editable. |
| Empty input after a run | Clear validation message; previous answer did not remain displayed as the current result. |
| Live synthetic chest-pain run | All seven stages finished through the existing ADK Runner using Gemini and real Chroma retrieval. |
| Live output | 10 extracted facts; Flesch–Kincaid grade 6.84; no unresolved findings in this run; explanation displayed. |
| Browser console | No page JavaScript errors in the tested flow. |
| Small-screen layout | Checked at 390 px wide; columns stack and the page has no horizontal overflow. |
| Automated tests | Full 101-test suite passed, including 10 new UI/integration checks. Those 10 also passed after runner cleanup was added. |

The live result is one synthetic smoke check, not a calibration or benchmark
result. Generated wording and scores may vary on subsequent calls. MTSamples
selection was checked in the browser; this check did not submit the 50 reports
to Gemini. Review/failure presentation is additionally covered by offline tests.

Local screenshots are under ignored `data/ui_checks/`. The UI does not itself
save medical reports or results to disk. Playwright was installed in the local
virtual environment for browser checks; it is not a runtime dependency of the UI.

## November 7: synced with the team's merged changes

Local `main` and `gradio-demo-ui` were fast-forwarded to `1fbe3fe`, containing
Carlin's paired runner (PR #28) and Zurabi's Refiner checks (PR #27). The local
Gradio implementation and personal documents were preserved. The custom-report
query now follows the merged full-report rule, baseline top-k defaults to 3,
and the Simplifier uses temperature 0. The UI setup guide was updated accordingly.

- All **134 tests passed** with the merged code and local UI present.
- The browser's dark-mode scripted repair walkthrough completed all seven
  stages, removed the deliberate unsupported pneumonia sentence, and recorded
  one repair/recheck. No page JavaScript errors occurred.
- No new live Gemini call was made for this synchronization check.
- The separate November 7 live paired-runner diagnostic on source row 4998
  remains recorded under `data/comparison_results/carlin_pilot_2026-11-07/`:
  baseline returned an answer; ADK retained a draft at reading grade 10.28;
  retrieval matched. That diagnostic is not a rerun of the UI's November 4
  synthetic example or a completed benchmark.

The UI remains local and uncommitted. A screenshot of the synced scripted run
is saved under ignored `data/ui_checks/after_team_sync_2026-11-07.png`.
