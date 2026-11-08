"""Gradio presentation layer; launch with python -m faithfulmed_ui.app."""

import argparse
from pathlib import Path

import gradio as gr

from faithfulmed_demo.config import ROOT
from faithfulmed_demo.fixtures import SOURCE
from .examples import BUILTIN, load_examples
from .pipeline import LIVE, MODES, Snapshot, stream_run
from .presentation import (answer_markdown, checks_markdown, facts_rows, metrics_html,
                           progress_html, sources_html, status_html, trace_state)

CSS = Path(__file__).with_name("style.css").read_text(encoding="utf-8")


def presentation_theme():
    """Keep this light presentation readable when Gradio detects dark mode."""
    theme = gr.themes.Soft(primary_hue="emerald", neutral_hue="slate",
                           font=["Segoe UI", "Arial", "sans-serif"])
    tokens = theme.to_dict()["theme"]
    # Match the whole component palette, including inputs, menus, tables and
    # JSON details, rather than fixing only the currently visible text.
    return theme.set(**{name: tokens[name[:-5]] for name in tokens
                        if name.endswith("_dark") and name[:-5] in tokens})


def build_ui():
    examples, availability = load_examples()
    idle = Snapshot(active="")
    with gr.Blocks(title="FaithfulMed · Medical reports, made clearer", analytics_enabled=False) as app:
        gr.HTML('''<header class="masthead"><a class="brand" href="#">FaithfulMed</a></header>
            <section class="intro"><p class="eyebrow">UNDERSTAND YOUR MEDICAL REPORT</p>
            <h1>Clearer words.<br><span>The same important facts.</span></h1>
            <p>Turn a medical report into a plain-language explanation, with source references and visible checks.</p></section>''')
        with gr.Row(equal_height=False, elem_id="workspace"):
            with gr.Column(scale=5, min_width=320, elem_id="input-panel"):
                gr.Markdown("## 1. Choose a report\nPaste a sample report, or explore one of the examples below.")
                mode = gr.Radio(choices=list(MODES), value=LIVE, label="Run mode", elem_id="run-mode")
                mode_note = gr.Markdown("Uses Gemini and your local MedlinePlus index. Use public or synthetic reports for this demo.", elem_classes="muted")
                example = gr.Dropdown(choices=list(examples), value=BUILTIN, label="Load an example", filterable=True)
                example_note = gr.Markdown(examples[BUILTIN]["note"], elem_classes="muted")
                report = gr.Textbox(value=SOURCE, label="Medical report", lines=13, max_lines=20,
                                    placeholder="Paste the report here…", elem_id="report-input")
                run_button = gr.Button("Simplify report →", variant="primary", size="lg", elem_id="run-button")
                gr.Markdown(availability, elem_classes="muted")
            with gr.Column(scale=7, min_width=320, elem_id="results-panel"):
                gr.Markdown("## 2. Read the explanation\nFollow the checks, then explore the result and its supporting evidence.")
                status = gr.HTML('<div class="result-status idle"><span class="status-dot"></span><div><strong>Ready when you are</strong><p>Choose a report and select Simplify report.</p></div></div>')
                progress = gr.HTML(progress_html(idle))
                metrics = gr.HTML(metrics_html(idle))
                with gr.Tabs():
                    with gr.Tab("Explanation"):
                        answer = gr.Markdown("Your explanation will appear here when the checks finish.",
                                             elem_id="explanation", buttons=["copy"], sanitize_html=True)
                    with gr.Tab("Sources & facts"):
                        sources = gr.HTML(sources_html({}))
                        gr.Markdown("### Facts from the original report")
                        facts = gr.Dataframe(headers=["Fact", "Assertion", "Exact source quote"],
                                             datatype=["str", "str", "str"], value=[], interactive=False, wrap=True)
                    with gr.Tab("Checks & repairs"):
                        checks = gr.Markdown(checks_markdown({}), sanitize_html=True)
                        with gr.Accordion("Inspect the saved workflow fields", open=False):
                            trace = gr.JSON(value={}, label="Current run")
                gr.Markdown("Research prototype. Automated checks are still being calibrated; this demo does not establish clinical accuracy.", elem_classes="result-footnote")
        gr.HTML('<footer class="page-footer"><span>FaithfulMed · Google 2F / Break Through Tech</span><span>From source report to a clearer explanation.</span></footer>')

        view_components = [status, progress, metrics, answer, sources, facts, checks, trace]

        def reset_outputs():
            return ('<div class="result-status idle"><span class="status-dot"></span><div><strong>Ready when you are</strong><p>Run the pipeline to check the selected report.</p></div></div>',
                    progress_html(idle), metrics_html(idle), "Your explanation will appear here when the checks finish.",
                    sources_html({}), [], checks_markdown({}), {})

        def select_example(choice):
            item = examples.get(choice)
            if item is None:
                return (gr.skip(), "Paste your own sample report.", *reset_outputs())
            return (item["text"], item["note"], *reset_outputs())

        example.change(select_example, [example], [report, example_note, *view_components], queue=False, api_visibility="private")

        def select_mode(value):
            live = value == LIVE
            note = ("Uses Gemini and your local MedlinePlus index. Use public or synthetic reports for this demo." if live else
                    "Scripted example only: fixed chest-pain text, no Gemini calls or database search. The repair walkthrough deliberately adds and removes a false claim.")
            return (gr.Dropdown(value=BUILTIN, interactive=live), gr.Textbox(value=SOURCE, interactive=live),
                    examples[BUILTIN]["note"], note, *reset_outputs())

        mode.change(select_mode, [mode], [example, report, example_note, mode_note, *view_components], queue=False, api_visibility="private")

        def report_edited(text):
            for item in examples.values():
                if item["text"] == text:
                    return (item["note"], *reset_outputs())
            return ("Custom report. The pipeline will use the text currently in this box.", *reset_outputs())

        report.input(report_edited, [report], [example_note, *view_components], queue=False, api_visibility="private")

        async def run_report(text, selected_mode):
            async for view in stream_run(text, selected_mode):
                unlocked = view.finished
                live = selected_mode == LIVE
                yield (status_html(view), progress_html(view), metrics_html(view), answer_markdown(view),
                       sources_html(view.state), facts_rows(view.state), checks_markdown(view.state), trace_state(view.state),
                       gr.Button(interactive=unlocked, value="Run again →" if unlocked else "Processing report…"),
                       gr.Radio(interactive=unlocked), gr.Dropdown(interactive=unlocked and live),
                       gr.Textbox(interactive=unlocked and live))

        run_button.click(run_report, [report, mode],
                         [*view_components, run_button, mode, example, report],
                         concurrency_limit=1, concurrency_id="faithfulmed", trigger_mode="once",
                         show_progress="minimal", api_name="simplify", api_visibility="private")
    return app.queue(max_size=8, default_concurrency_limit=1)


def main():
    parser = argparse.ArgumentParser(description="Run the local FaithfulMed presentation UI.")
    parser.add_argument("--port", type=int, default=7860)
    args = parser.parse_args()
    build_ui().launch(server_name="127.0.0.1", server_port=args.port, share=False, show_error=False,
                      theme=presentation_theme(),
                      css=CSS, footer_links=[], run_history=False,
                      blocked_paths=[str(ROOT / ".env"), str(ROOT / ".git")])


if __name__ == "__main__":
    main()
